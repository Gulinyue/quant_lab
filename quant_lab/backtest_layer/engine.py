"""Minimal daily low-frequency backtest engine."""

from __future__ import annotations

from typing import Any

import pandas as pd

from quant_lab.backtest_layer.execution import (
    extract_close_prices,
    extract_execution_prices,
    shift_target_positions_for_execution,
)
from quant_lab.backtest_layer.performance import calc_performance_summary
from quant_lab.backtest_layer.portfolio import (
    normalize_target_weights,
    target_shares_from_weights,
    target_weights_for_date,
)
from quant_lab.backtest_layer.transaction_cost import estimate_trade_cost
from quant_lab.backtest_layer.validators import validate_market_panel, validate_target_positions
from quant_lab.common.types import BacktestResult


def load_backtest_config(backtest_config: dict[str, Any]) -> dict[str, Any]:
    """Normalize backtest configuration with backward compatibility."""
    execution = backtest_config.get("execution", {})
    cost = backtest_config.get("cost", {})
    portfolio = backtest_config.get("portfolio", {})
    constraints = backtest_config.get("constraints", {})

    if not cost:
        cost = {
            "commission": float(backtest_config.get("commission", 0.0003)),
            "slippage": float(backtest_config.get("slippage", 0.0005)),
            "stamp_tax_sell": float(backtest_config.get("stamp_tax", 0.001)),
        }

    return {
        "execution": {
            "price": str(execution.get("price", "next_open")).replace("next_", ""),
            "lot_size": int(execution.get("lot_size", 100)),
        },
        "cost": {
            "commission": float(cost.get("commission", 0.0003)),
            "slippage": float(cost.get("slippage", 0.0005)),
            "stamp_tax_sell": float(cost.get("stamp_tax_sell", 0.001)),
        },
        "portfolio": {
            "initial_capital": float(portfolio.get("initial_capital", 1_000_000.0)),
        },
        "constraints": {
            "long_only": bool(constraints.get("long_only", True)),
        },
    }


def run_backtest(market_panel: pd.DataFrame, target_positions: pd.DataFrame, backtest_config: dict[str, Any]) -> BacktestResult:
    """Run a minimal daily execution backtest."""
    config = load_backtest_config(backtest_config)
    execution_price_field = config["execution"]["price"]
    validate_market_panel(market_panel, execution_price_field)
    validate_target_positions(target_positions)

    execution_prices = extract_execution_prices(market_panel, execution_price_field)
    close_prices = extract_close_prices(market_panel)
    all_dates = execution_prices.index
    all_assets = execution_prices.columns
    shifted_targets = shift_target_positions_for_execution(target_positions, all_dates=all_dates)

    cash = float(config["portfolio"]["initial_capital"])
    current_shares = pd.Series(0, index=all_assets, dtype=int)
    last_desired_weights = pd.Series(0.0, index=all_assets)
    nav_rows: list[dict[str, Any]] = []
    trade_rows: list[dict[str, Any]] = []
    position_rows: list[dict[str, Any]] = []

    for trade_date in all_dates:
        exec_px = execution_prices.loc[trade_date].fillna(0.0)
        close_px = close_prices.loc[trade_date].fillna(0.0)
        start_value = float(cash + (current_shares * exec_px).sum())

        desired_weights = normalize_target_weights(
            target_weights_for_date(shifted_targets, trade_date),
            long_only=config["constraints"]["long_only"],
        ).reindex(all_assets).fillna(0.0)
        rebalance_flag = not desired_weights.round(12).equals(last_desired_weights.round(12))
        if rebalance_flag:
            desired_shares = target_shares_from_weights(
                target_weights=desired_weights,
                execution_prices=exec_px,
                portfolio_value=start_value,
                lot_size=config["execution"]["lot_size"],
            ).reindex(all_assets).fillna(0).astype(int)
            last_desired_weights = desired_weights.copy()
        else:
            desired_shares = current_shares.copy()

        delta_shares = (desired_shares - current_shares).astype(int)
        traded_amount = 0.0
        total_cost = 0.0
        cash_without_cost = cash

        for asset, delta in delta_shares.items():
            if delta == 0:
                continue
            price = float(exec_px.get(asset, 0.0))
            if price <= 0:
                continue
            side = "BUY" if delta > 0 else "SELL"
            shares = abs(int(delta))
            amount = shares * price
            cost = estimate_trade_cost(
                amount=amount,
                side=side,
                commission=config["cost"]["commission"],
                slippage=config["cost"]["slippage"],
                stamp_tax_sell=config["cost"]["stamp_tax_sell"],
            )
            if side == "BUY":
                cash_without_cost -= amount
            else:
                cash_without_cost += amount
            traded_amount += amount
            total_cost += cost
            trade_rows.append(
                {
                    "trade_date": trade_date,
                    "asset": asset,
                    "side": side,
                    "price": price,
                    "shares": shares,
                    "amount": amount,
                    "cost": cost,
                }
            )

        cash = cash_without_cost - total_cost
        current_shares = desired_shares
        holdings_value = float((current_shares * close_px).sum())
        gross_end_value = cash_without_cost + holdings_value
        end_value = cash + holdings_value
        gross_ret = (gross_end_value / start_value - 1.0) if start_value > 0 else 0.0
        turnover = (traded_amount / start_value) if start_value > 0 else 0.0
        cost_ratio = (total_cost / start_value) if start_value > 0 else 0.0
        net_ret = (end_value / start_value - 1.0) if start_value > 0 else 0.0
        nav = end_value / config["portfolio"]["initial_capital"] if config["portfolio"]["initial_capital"] > 0 else 0.0

        nav_rows.append(
            {
                "trade_date": trade_date,
                "gross_ret": gross_ret,
                "turnover": turnover,
                "cost": cost_ratio,
                "net_ret": net_ret,
                "nav": nav,
            }
        )

        if end_value > 0:
            weights = (current_shares * close_px) / end_value
        else:
            weights = pd.Series(0.0, index=all_assets)
        for asset in all_assets:
            shares = int(current_shares.get(asset, 0))
            if shares == 0:
                continue
            close = float(close_px.get(asset, 0.0))
            market_value = float(shares * close)
            position_rows.append(
                {
                    "trade_date": trade_date,
                    "asset": asset,
                    "weight": float(weights.get(asset, 0.0)),
                    "shares": shares,
                    "close": close,
                    "market_value": market_value,
                }
            )

    nav_df = pd.DataFrame(nav_rows).set_index("trade_date").sort_index()
    if position_rows:
        daily_positions = pd.DataFrame(position_rows).set_index(["trade_date", "asset"]).sort_index()
    else:
        daily_positions = pd.DataFrame(columns=["weight", "shares", "close", "market_value"])
        daily_positions.index = pd.MultiIndex.from_arrays([[], []], names=["trade_date", "asset"])
    trades = pd.DataFrame(trade_rows, columns=["trade_date", "asset", "side", "price", "shares", "amount", "cost"])
    performance_summary = calc_performance_summary(nav_df)
    return BacktestResult(
        nav=nav_df,
        daily_positions=daily_positions,
        trades=trades,
        performance_summary=performance_summary,
    )
