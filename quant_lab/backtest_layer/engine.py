"""Simplified daily low-frequency backtest engine."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_lab.analysis_layer.performance import compute_performance_metrics
from quant_lab.backtest_layer.portfolio import pivot_target_weights
from quant_lab.backtest_layer.transaction_cost import estimate_daily_costs
from quant_lab.common.types import BacktestResult


def run_backtest(
    market_panel: pd.DataFrame,
    target_positions: pd.DataFrame,
    commission: float,
    slippage: float,
    stamp_tax: float,
) -> BacktestResult:
    """Run a simplified next-day-return backtest."""
    returns = market_panel["close_adj"].unstack("asset").sort_index().pct_change().shift(-1).fillna(0.0)
    all_dates = returns.index
    weights = pivot_target_weights(target_positions, all_dates).reindex(columns=returns.columns).fillna(0.0)
    prev_weights = weights.shift(1).fillna(0.0)
    weight_delta = weights - prev_weights
    gross_returns = (prev_weights * returns).sum(axis=1)
    costs = estimate_daily_costs(weight_delta, commission=commission, slippage=slippage, stamp_tax=stamp_tax)
    net_returns = gross_returns - costs
    nav = pd.DataFrame({"daily_return": net_returns, "nav": (1.0 + net_returns).cumprod()}, index=all_dates)
    nav.index.name = "trade_date"

    trades = weight_delta.stack().reset_index()
    trades.columns = ["trade_date", "asset", "weight_delta"]
    trades = trades[trades["weight_delta"].abs() > 1e-12]
    trades["side"] = np.where(trades["weight_delta"] > 0, "BUY", "SELL")

    daily_positions = weights.stack().reset_index()
    daily_positions.columns = ["trade_date", "asset", "target_weight"]
    metrics = compute_performance_metrics(nav["daily_return"])
    return BacktestResult(nav=nav, daily_positions=daily_positions, trades=trades, metrics=metrics)
