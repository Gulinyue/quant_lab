"""Transaction cost helpers."""

from __future__ import annotations

import pandas as pd


def estimate_daily_costs(weight_delta: pd.DataFrame, commission: float, slippage: float, stamp_tax: float) -> pd.Series:
    """Estimate daily transaction costs from weight changes."""
    buy_turnover = weight_delta.clip(lower=0.0).sum(axis=1)
    sell_turnover = (-weight_delta.clip(upper=0.0)).sum(axis=1)
    return buy_turnover * (commission + slippage) + sell_turnover * (commission + slippage + stamp_tax)
