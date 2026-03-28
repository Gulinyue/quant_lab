"""Minimal ranking strategy implementation."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from quant_lab.strategy_layer.base import Strategy, StrategyRunResult
from quant_lab.strategy_layer.constraints import apply_weight_constraints, compute_rebalance_flags
from quant_lab.strategy_layer.factor_selector import select_eligible_factors
from quant_lab.strategy_layer.strategy_diagnostics import build_strategy_diagnostics


class RankingStrategy(Strategy):
    """Linear weighted ranking strategy with equal-weight long-only output."""

    def __init__(self, strategy_config: dict[str, Any]) -> None:
        self.strategy_config = strategy_config

    def run(
        self,
        factor_panel: pd.DataFrame,
        metadata: pd.DataFrame,
        screening: pd.DataFrame | None = None,
    ) -> StrategyRunResult:
        """Generate standard target positions and diagnostics."""
        selection = select_eligible_factors(factor_panel, metadata, screening, self.strategy_config)
        if not selection.selected_factors:
            raise ValueError(f"No eligible factors after filtering: {selection.dropped_factors}")

        score_frame = build_composite_score(
            factor_panel=factor_panel,
            selected_factors=selection.selected_factors,
            factor_weights=selection.weights,
            score_transform=self.strategy_config["factors"]["score_transform"],
        )
        target_positions = generate_target_positions(score_frame, self.strategy_config)
        trade_dates = score_frame["trade_date"].drop_duplicates().sort_values()
        rebalance_flags = compute_rebalance_flags(trade_dates, self.strategy_config["strategy"]["rebalance"])
        diagnostics = build_strategy_diagnostics(
            score_frame=score_frame,
            rebalance_flags=rebalance_flags,
            selected_factors=selection.selected_factors,
            dropped_factors=selection.dropped_factors,
            strategy_config=self.strategy_config,
            target_positions=target_positions,
        )
        return StrategyRunResult(
            target_positions=target_positions,
            diagnostics=diagnostics,
            selected_factors=selection.selected_factors,
            dropped_factors=selection.dropped_factors,
            config=self.strategy_config,
        )


def build_composite_score(
    factor_panel: pd.DataFrame,
    selected_factors: list[str],
    factor_weights: dict[str, float],
    score_transform: str = "none",
) -> pd.DataFrame:
    """Build cross-sectional composite score from selected factors."""
    frame = factor_panel[selected_factors].copy()
    if score_transform == "rank":
        frame = frame.groupby(level="trade_date", group_keys=False).rank(pct=True)
    elif score_transform == "zscore":
        frame = frame.groupby(level="trade_date", group_keys=False).transform(_safe_zscore)
    elif score_transform != "none":
        raise ValueError(f"Unsupported score_transform: {score_transform}")

    score_series = pd.Series(0.0, index=frame.index, name="score")
    used_factor_count = pd.Series(0, index=frame.index, dtype=int, name="factor_count_used")
    for factor_name in selected_factors:
        series = pd.to_numeric(frame[factor_name], errors="coerce").replace([np.inf, -np.inf], np.nan)
        weight = float(factor_weights[factor_name])
        score_series = score_series.add(series.fillna(0.0) * weight, fill_value=0.0)
        used_factor_count = used_factor_count.add(series.notna().astype(int), fill_value=0)

    score_frame = (
        pd.DataFrame({"score": score_series, "factor_count_used": used_factor_count})
        .reset_index()
        .sort_values(["trade_date", "asset"])
        .reset_index(drop=True)
    )
    score_frame["rank"] = score_frame.groupby("trade_date")["score"].rank(method="first", ascending=False)
    score_frame["signal"] = np.where(score_frame["score"].notna(), np.sign(score_frame["score"]).astype(float), np.nan)
    return score_frame


def generate_target_positions(score_frame: pd.DataFrame, strategy_config: dict[str, Any]) -> pd.DataFrame:
    """Generate target positions using top-N equal-weight long-only selection."""
    if score_frame.empty:
        raise ValueError("score_frame is empty; cannot generate target positions.")

    top_n = int(strategy_config["strategy"]["top_n"])
    rebalance = strategy_config["strategy"]["rebalance"]
    max_weight_per_asset = float(strategy_config["constraints"]["max_weight_per_asset"])
    rebalance_flags = compute_rebalance_flags(score_frame["trade_date"].drop_duplicates().sort_values(), rebalance)

    outputs: list[pd.DataFrame] = []
    last_selected_assets: list[str] = []
    for trade_date, group in score_frame.groupby("trade_date"):
        ranked = group.sort_values(["score", "asset"], ascending=[False, True]).copy()
        ranked["target_weight"] = 0.0
        ranked["selected_by_strategy"] = False

        if rebalance_flags.get(pd.Timestamp(trade_date), False):
            valid = ranked.dropna(subset=["score"])
            selected = valid.head(top_n).copy()
            last_selected_assets = selected["asset"].tolist()
        else:
            selected = ranked[ranked["asset"].isin(last_selected_assets)].copy()

        selected_count = len(selected)
        weight = apply_weight_constraints(selected_count, max_weight_per_asset)
        if selected_count > 0:
            ranked.loc[ranked["asset"].isin(selected["asset"]), "target_weight"] = weight
            ranked.loc[ranked["asset"].isin(selected["asset"]), "selected_by_strategy"] = True

        outputs.append(
            ranked[
                [
                    "trade_date",
                    "asset",
                    "score",
                    "target_weight",
                    "rank",
                    "signal",
                    "selected_by_strategy",
                    "factor_count_used",
                ]
            ]
        )

    target_positions = pd.concat(outputs, ignore_index=True).set_index(["trade_date", "asset"]).sort_index()
    return target_positions


def _safe_zscore(series: pd.Series) -> pd.Series:
    """Z-score helper for strategy-layer scoring."""
    valid = series.dropna()
    if valid.empty:
        return pd.Series(np.nan, index=series.index)
    std = valid.std(ddof=0)
    if pd.isna(std) or std == 0:
        return pd.Series(0.0, index=series.index)
    return (series - valid.mean()) / std
