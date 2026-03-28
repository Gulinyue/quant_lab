"""Portfolio construction helpers for the minimal backtest engine."""

from __future__ import annotations

import math

import pandas as pd


def target_weights_for_date(target_weights: pd.DataFrame, trade_date: pd.Timestamp) -> pd.Series:
    """Return target weights for one execution date."""
    if trade_date not in target_weights.index:
        return pd.Series(dtype=float)
    series = target_weights.loc[trade_date].fillna(0.0)
    series.name = "target_weight"
    return series


def normalize_target_weights(target_weights: pd.Series, long_only: bool = True) -> pd.Series:
    """Clean target weights without forcing full investment."""
    if target_weights.empty:
        return target_weights
    weights = target_weights.astype(float).copy()
    if long_only:
        weights = weights.clip(lower=0.0)
    weights = weights.fillna(0.0)
    return weights


def target_shares_from_weights(
    target_weights: pd.Series,
    execution_prices: pd.Series,
    portfolio_value: float,
    lot_size: int,
) -> pd.Series:
    """Convert target weights into rounded target share counts."""
    if portfolio_value <= 0:
        return pd.Series(0, index=target_weights.index, dtype=int)
    shares = {}
    for asset, weight in target_weights.items():
        price = float(execution_prices.get(asset, float("nan")))
        if pd.isna(price) or price <= 0 or weight <= 0:
            shares[asset] = 0
            continue
        target_value = portfolio_value * float(weight)
        raw_shares = target_value / price
        rounded = int(math.floor(raw_shares / lot_size) * lot_size) if lot_size > 1 else int(math.floor(raw_shares))
        shares[asset] = max(rounded, 0)
    return pd.Series(shares, dtype=int)
