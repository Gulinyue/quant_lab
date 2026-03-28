"""Validation helpers for backtest-layer inputs."""

from __future__ import annotations

import pandas as pd


def validate_market_panel(market_panel: pd.DataFrame, execution_price: str) -> None:
    """Validate minimal market panel requirements for backtesting."""
    required_columns = {"close", "close_adj", execution_price}
    missing = sorted(required_columns - set(market_panel.columns))
    if missing:
        raise ValueError(f"market_panel missing required columns for backtest: {missing}")
    if not isinstance(market_panel.index, pd.MultiIndex) or list(market_panel.index.names) != ["trade_date", "asset"]:
        raise ValueError("market_panel must use MultiIndex(['trade_date', 'asset']).")


def validate_target_positions(target_positions: pd.DataFrame) -> None:
    """Validate target position inputs."""
    if target_positions.empty:
        raise ValueError("target_positions is empty; backtest cannot run.")
    if not isinstance(target_positions.index, pd.MultiIndex) or list(target_positions.index.names) != ["trade_date", "asset"]:
        raise ValueError("target_positions must use MultiIndex(['trade_date', 'asset']).")
    required_columns = {"target_weight"}
    missing = sorted(required_columns - set(target_positions.columns))
    if missing:
        raise ValueError(f"target_positions missing required columns: {missing}")
