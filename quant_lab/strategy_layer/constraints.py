"""Strategy-layer constraint helpers."""

from __future__ import annotations

import math

import pandas as pd


def compute_rebalance_flags(trade_dates: pd.Index, rebalance: str) -> dict[pd.Timestamp, bool]:
    """Return per-date rebalance flags for daily or weekly rebalancing."""
    date_index = pd.DatetimeIndex(pd.to_datetime(trade_dates)).sort_values().unique()
    if rebalance == "daily":
        return {timestamp: True for timestamp in date_index}
    if rebalance == "weekly":
        period_keys = date_index.to_period("W")
        flags = {timestamp: False for timestamp in date_index}
        for period in period_keys.unique():
            period_dates = date_index[period_keys == period]
            flags[period_dates[0]] = True
        return flags
    raise ValueError(f"Unsupported rebalance rule: {rebalance}")


def apply_weight_constraints(selected_count: int, max_weight_per_asset: float) -> float:
    """Return equal weight after applying a max single-asset weight cap."""
    if selected_count <= 0:
        return 0.0
    equal_weight = 1.0 / selected_count
    if max_weight_per_asset <= 0:
        return 0.0
    return min(equal_weight, max_weight_per_asset)


def min_assets_for_full_investment(max_weight_per_asset: float) -> int:
    """Approximate minimum asset count required to stay fully invested under a cap."""
    if max_weight_per_asset <= 0:
        return math.inf
    return int(math.ceil(1.0 / max_weight_per_asset))
