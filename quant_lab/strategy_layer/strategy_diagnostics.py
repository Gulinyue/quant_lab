"""Diagnostics builders for strategy-layer outputs."""

from __future__ import annotations

from typing import Any

import pandas as pd


def build_strategy_diagnostics(
    score_frame: pd.DataFrame,
    rebalance_flags: dict[pd.Timestamp, bool],
    selected_factors: list[str],
    dropped_factors: dict[str, str],
    strategy_config: dict[str, Any],
    target_positions: pd.DataFrame,
) -> pd.DataFrame:
    """Build a long diagnostics table describing factor usage and daily run quality."""
    if score_frame.empty:
        return pd.DataFrame(
            columns=[
                "trade_date",
                "factor_name",
                "factor_used",
                "factor_drop_reason",
                "candidate_count",
                "selected_count",
                "active_factor_count",
                "dropped_factor_count",
                "weighting_method",
                "rebalance_flag",
                "score_non_null_ratio",
                "score_std",
                "message",
            ]
        )

    rows: list[dict[str, Any]] = []
    all_factors = list(dict.fromkeys(selected_factors + list(dropped_factors.keys())))
    min_selected_assets = int(strategy_config["constraints"]["min_selected_assets"])
    weighting_method = strategy_config["strategy"]["weighting"]

    for trade_date, group in score_frame.groupby("trade_date"):
        candidate_count = int(group["asset"].nunique())
        selected_group = target_positions.xs(trade_date, level="trade_date") if trade_date in target_positions.index.get_level_values("trade_date") else pd.DataFrame(columns=target_positions.columns)
        selected_count = int((selected_group["target_weight"] > 0).sum()) if not selected_group.empty else 0
        score_non_null_ratio = float(group["score"].notna().mean()) if len(group) else 0.0
        score_std = float(group["score"].std(ddof=0)) if group["score"].notna().any() else 0.0
        messages: list[str] = []
        if selected_count < min_selected_assets:
            messages.append("selected_count_below_min")
        if score_non_null_ratio == 0.0:
            messages.append("score_all_nan")
        elif score_std == 0.0:
            messages.append("score_no_dispersion")
        if rebalance_flags.get(pd.Timestamp(trade_date), False):
            messages.append("rebalance_day")

        for factor_name in all_factors:
            factor_used = factor_name in selected_factors
            rows.append(
                {
                    "trade_date": trade_date,
                    "factor_name": factor_name,
                    "factor_used": factor_used,
                    "factor_drop_reason": "" if factor_used else dropped_factors.get(factor_name, ""),
                    "candidate_count": candidate_count,
                    "selected_count": selected_count,
                    "active_factor_count": len(selected_factors),
                    "dropped_factor_count": len(dropped_factors),
                    "weighting_method": weighting_method,
                    "rebalance_flag": bool(rebalance_flags.get(pd.Timestamp(trade_date), False)),
                    "score_non_null_ratio": score_non_null_ratio,
                    "score_std": score_std,
                    "message": ";".join(messages),
                }
            )
    return pd.DataFrame(rows)
