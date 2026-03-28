"""Execution helpers for the minimal daily backtest engine."""

from __future__ import annotations

import pandas as pd


def shift_target_positions_for_execution(target_positions: pd.DataFrame, all_dates: pd.Index) -> pd.DataFrame:
    """Shift target weights by one trading day so signals execute on the next session."""
    weights = target_positions["target_weight"].unstack("asset").sort_index()
    weights = weights.reindex(pd.DatetimeIndex(pd.to_datetime(all_dates)).sort_values()).ffill()
    shifted = weights.shift(1).fillna(0.0)
    shifted.index.name = "trade_date"
    return shifted


def extract_execution_prices(market_panel: pd.DataFrame, price_field: str) -> pd.DataFrame:
    """Extract execution prices from market panel."""
    return market_panel[price_field].unstack("asset").sort_index()


def extract_close_prices(market_panel: pd.DataFrame) -> pd.DataFrame:
    """Extract end-of-day close prices from market panel."""
    return market_panel["close"].unstack("asset").sort_index()
