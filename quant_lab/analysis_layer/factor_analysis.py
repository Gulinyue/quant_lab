"""Factor diagnostic helpers."""

from __future__ import annotations

import pandas as pd


def compute_rank_ic(factor_panel: pd.DataFrame, market_panel: pd.DataFrame, factor_name: str) -> pd.DataFrame:
    """Compute a simple RankIC time series for a factor."""
    if factor_name not in factor_panel.columns:
        return pd.DataFrame(columns=["trade_date", "rank_ic"])
    future_returns = market_panel["close_adj"].unstack("asset").sort_index().pct_change().shift(-1).stack().rename("future_return")
    joined = pd.concat([factor_panel[[factor_name]], future_returns], axis=1).dropna()
    rows: list[dict[str, float | pd.Timestamp]] = []
    for trade_date, group in joined.groupby(level="trade_date"):
        corr = group[factor_name].rank().corr(group["future_return"].rank())
        rows.append({"trade_date": trade_date, "rank_ic": float(corr) if pd.notna(corr) else 0.0})
    return pd.DataFrame(rows)
