"""Performance analytics."""

from __future__ import annotations

import math

import pandas as pd


def compute_performance_metrics(daily_returns: pd.Series, trading_days: int = 252) -> dict[str, float]:
    """Compute core performance metrics."""
    daily_returns = daily_returns.fillna(0.0)
    nav = (1.0 + daily_returns).cumprod()
    total_periods = max(len(daily_returns), 1)
    annual_return = nav.iloc[-1] ** (trading_days / total_periods) - 1 if not nav.empty else 0.0
    annual_vol = daily_returns.std(ddof=0) * math.sqrt(trading_days)
    sharpe = annual_return / annual_vol if annual_vol > 0 else 0.0
    drawdown = nav / nav.cummax() - 1.0
    max_drawdown = drawdown.min() if not drawdown.empty else 0.0
    return {
        "annual_return": float(annual_return),
        "annual_volatility": float(annual_vol),
        "sharpe": float(sharpe),
        "max_drawdown": float(max_drawdown),
    }


def yearly_breakdown(daily_returns: pd.Series) -> pd.DataFrame:
    """Compute yearly performance breakdown."""
    frame = pd.DataFrame({"daily_return": daily_returns.fillna(0.0)})
    frame["year"] = pd.to_datetime(frame.index).year
    rows: list[dict[str, float | int]] = []
    for year, group in frame.groupby("year"):
        metrics = compute_performance_metrics(group["daily_return"])
        metrics["year"] = int(year)
        rows.append(metrics)
    return pd.DataFrame(rows)
