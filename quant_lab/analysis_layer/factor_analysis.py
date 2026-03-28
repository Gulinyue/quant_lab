"""Single-factor research helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from quant_lab.common.io import write_json


@dataclass(slots=True)
class FactorResearchResult:
    """Container for single-factor research outputs."""

    factor_name: str
    summary: dict[str, Any]
    rank_ic_series: pd.DataFrame
    quantile_returns: pd.DataFrame
    yearly_summary: pd.DataFrame
    forward_returns: pd.Series


def calc_forward_return(market_panel: pd.DataFrame, horizon: int = 1) -> pd.Series:
    """Calculate forward returns from adjusted close prices."""
    if "close_adj" not in market_panel.columns:
        raise KeyError("market_panel must contain close_adj for forward return calculation.")
    if horizon <= 0:
        raise ValueError("horizon must be a positive integer.")

    price_wide = market_panel["close_adj"].unstack("asset").sort_index()
    forward_returns = price_wide.pct_change(periods=horizon).shift(-horizon)
    return forward_returns.stack().rename(f"forward_return_{horizon}d")


def calc_rank_ic_series(
    factor_series: pd.Series,
    forward_return: pd.Series,
    min_cross_section: int = 5,
) -> pd.DataFrame:
    """Calculate per-date cross-sectional RankIC."""
    joined = pd.concat([factor_series.rename("factor"), forward_return.rename("forward_return")], axis=1)
    joined = joined.replace([np.inf, -np.inf], np.nan).dropna()

    rows: list[dict[str, Any]] = []
    for trade_date, group in joined.groupby(level="trade_date"):
        sample_size = len(group)
        unique_factor = int(group["factor"].nunique(dropna=True))
        unique_return = int(group["forward_return"].nunique(dropna=True))
        status = "ok"
        rank_ic = np.nan
        if sample_size < min_cross_section:
            status = "insufficient_cross_section"
        elif unique_factor < 2:
            status = "constant_factor_slice"
        elif unique_return < 2:
            status = "constant_return_slice"
        else:
            rank_ic = group["factor"].rank().corr(group["forward_return"].rank())
            if pd.isna(rank_ic):
                status = "invalid_rank_ic"
        rows.append(
            {
                "trade_date": trade_date,
                "rank_ic": rank_ic,
                "sample_size": sample_size,
                "status": status,
            }
        )
    if not rows:
        return pd.DataFrame(columns=["trade_date", "rank_ic", "sample_size", "status"])
    return pd.DataFrame(rows).sort_values("trade_date").reset_index(drop=True)


def calc_quantile_returns(
    factor_series: pd.Series,
    forward_return: pd.Series,
    quantiles: int = 5,
    min_cross_section: int = 5,
) -> pd.DataFrame:
    """Calculate per-date quantile portfolio returns."""
    if quantiles < 2:
        raise ValueError("quantiles must be >= 2.")

    joined = pd.concat([factor_series.rename("factor"), forward_return.rename("forward_return")], axis=1)
    joined = joined.replace([np.inf, -np.inf], np.nan).dropna()

    rows: list[dict[str, Any]] = []
    for trade_date, group in joined.groupby(level="trade_date"):
        if len(group) < max(quantiles, min_cross_section):
            continue
        if group["factor"].nunique(dropna=True) < quantiles:
            continue
        ranked = group["factor"].rank(method="first")
        try:
            buckets = pd.qcut(ranked, q=quantiles, labels=False, duplicates="drop") + 1
        except ValueError:
            continue
        grouped = group.assign(quantile=buckets).groupby("quantile")["forward_return"].mean()
        row = {"trade_date": trade_date}
        for quantile in range(1, quantiles + 1):
            row[f"q{quantile}"] = float(grouped.get(quantile, np.nan))
        row["long_short"] = row.get(f"q{quantiles}", np.nan) - row.get("q1", np.nan)
        rows.append(row)
    if not rows:
        return pd.DataFrame(columns=["trade_date"] + [f"q{i}" for i in range(1, quantiles + 1)] + ["long_short"])
    return pd.DataFrame(rows).sort_values("trade_date").reset_index(drop=True)


def calc_factor_research_summary(
    factor_name: str,
    rank_ic_series: pd.DataFrame,
    quantile_returns: pd.DataFrame,
    horizon: int = 1,
    min_valid_dates: int = 20,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Build summary metrics and yearly breakdown for a researched factor."""
    valid_rank_ic = rank_ic_series["rank_ic"].dropna() if "rank_ic" in rank_ic_series else pd.Series(dtype=float)
    valid_dates = int(valid_rank_ic.shape[0])
    rank_ic_mean = float(valid_rank_ic.mean()) if valid_dates else np.nan
    rank_ic_std = float(valid_rank_ic.std(ddof=0)) if valid_dates else np.nan
    annualization = np.sqrt(252 / horizon)
    if valid_dates and pd.notna(rank_ic_std) and rank_ic_std > 0:
        icir = float(rank_ic_mean / rank_ic_std * annualization)
    else:
        icir = np.nan

    long_short_mean = (
        float(quantile_returns["long_short"].dropna().mean())
        if not quantile_returns.empty and "long_short" in quantile_returns
        else np.nan
    )

    if valid_dates == 0:
        research_status = "failed_all_nan"
        message = "No valid RankIC observations were produced."
    elif valid_dates < min_valid_dates:
        research_status = "insufficient_sample"
        message = f"Only {valid_dates} valid RankIC dates; below threshold {min_valid_dates}."
    elif pd.isna(rank_ic_mean) or abs(rank_ic_mean) < 0.02:
        research_status = "weak"
        message = "RankIC mean is close to zero."
    else:
        research_status = "valid"
        message = "Factor has enough valid observations for basic research."

    yearly_summary = pd.DataFrame(columns=["year", "rank_ic_mean", "rank_ic_count", "long_short_mean"])
    if not rank_ic_series.empty:
        rank_yearly = rank_ic_series.dropna(subset=["rank_ic"]).copy()
        if not rank_yearly.empty:
            rank_yearly["year"] = pd.to_datetime(rank_yearly["trade_date"]).dt.year
            yearly_summary = (
                rank_yearly.groupby("year")["rank_ic"]
                .agg(rank_ic_mean="mean", rank_ic_count="count")
                .reset_index()
            )
    if not quantile_returns.empty and "long_short" in quantile_returns:
        ls_yearly = quantile_returns.dropna(subset=["long_short"]).copy()
        if not ls_yearly.empty:
            ls_yearly["year"] = pd.to_datetime(ls_yearly["trade_date"]).dt.year
            yearly_ls = ls_yearly.groupby("year")["long_short"].mean().rename("long_short_mean").reset_index()
            yearly_summary = yearly_summary.merge(yearly_ls, on="year", how="outer") if not yearly_summary.empty else yearly_ls

    summary = {
        "factor_name": factor_name,
        "horizon": horizon,
        "rank_ic_mean": rank_ic_mean,
        "rank_ic_std": rank_ic_std,
        "icir": icir,
        "valid_rank_ic_dates": valid_dates,
        "quantile_dates": int(len(quantile_returns)),
        "long_short_mean": long_short_mean,
        "research_status": research_status,
        "message": message,
    }
    return summary, yearly_summary


def _save_rank_ic_plot(rank_ic_series: pd.DataFrame, path: Path, factor_name: str) -> None:
    """Save RankIC time-series plot."""
    if rank_ic_series.empty:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(pd.to_datetime(rank_ic_series["trade_date"]), rank_ic_series["rank_ic"], label="RankIC")
    ax.axhline(0.0, color="black", linewidth=0.8, linestyle="--")
    ax.set_title(f"{factor_name} RankIC")
    ax.set_xlabel("Trade Date")
    ax.set_ylabel("RankIC")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _save_quantile_plot(quantile_returns: pd.DataFrame, path: Path, factor_name: str) -> None:
    """Save cumulative quantile long-short chart."""
    if quantile_returns.empty:
        return
    plot_df = quantile_returns.copy()
    value_cols = [column for column in plot_df.columns if column.startswith("q") or column == "long_short"]
    if not value_cols:
        return
    plot_df[value_cols] = plot_df[value_cols].fillna(0.0)
    cumulative = (1.0 + plot_df[value_cols]).cumprod() - 1.0
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 4))
    cumulative.index = pd.to_datetime(plot_df["trade_date"])
    cumulative.plot(ax=ax)
    ax.set_title(f"{factor_name} Quantile Returns")
    ax.set_xlabel("Trade Date")
    ax.set_ylabel("Cumulative Return")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def run_single_factor_research(
    market_panel: pd.DataFrame,
    factor_panel: pd.DataFrame,
    factor_name: str,
    *,
    horizon: int = 1,
    quantiles: int = 5,
    output_dir: Path | None = None,
) -> FactorResearchResult:
    """Run the full single-factor research flow for one factor."""
    if factor_name not in factor_panel.columns:
        raise KeyError(f"Factor not found in factor_panel: {factor_name}")

    factor_series = factor_panel[factor_name].rename(factor_name)
    forward_returns = calc_forward_return(market_panel, horizon=horizon)
    rank_ic_series = calc_rank_ic_series(factor_series, forward_returns)
    quantile_returns = calc_quantile_returns(factor_series, forward_returns, quantiles=quantiles)
    summary, yearly_summary = calc_factor_research_summary(
        factor_name=factor_name,
        rank_ic_series=rank_ic_series,
        quantile_returns=quantile_returns,
        horizon=horizon,
    )
    result = FactorResearchResult(
        factor_name=factor_name,
        summary=summary,
        rank_ic_series=rank_ic_series,
        quantile_returns=quantile_returns,
        yearly_summary=yearly_summary,
        forward_returns=forward_returns,
    )

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        rank_ic_series.to_csv(output_dir / "rank_ic.csv", index=False, encoding="utf-8")
        quantile_returns.to_csv(output_dir / "quantile_returns.csv", index=False, encoding="utf-8")
        yearly_summary.to_csv(output_dir / "yearly_summary.csv", index=False, encoding="utf-8")
        write_json(summary, output_dir / "summary.json")
        _save_rank_ic_plot(rank_ic_series, output_dir / "rank_ic.png", factor_name)
        _save_quantile_plot(quantile_returns, output_dir / "quantile_returns.png", factor_name)

    return result
