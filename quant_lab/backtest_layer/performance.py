"""Performance summary helpers for backtest outputs."""

from __future__ import annotations

import math

import pandas as pd


def calc_performance_summary(nav: pd.DataFrame, trading_days_per_year: int = 252) -> pd.DataFrame:
    """Calculate minimal performance summary from nav table."""
    if nav.empty:
        return pd.DataFrame(
            [
                {
                    "total_return": 0.0,
                    "annualized_return": 0.0,
                    "annualized_volatility": 0.0,
                    "sharpe": 0.0,
                    "max_drawdown": 0.0,
                    "avg_turnover": 0.0,
                    "win_rate": 0.0,
                    "trading_days": 0,
                    "message": "empty_nav",
                }
            ]
        )

    net_ret = nav["net_ret"].fillna(0.0)
    nav_series = nav["nav"].ffill().fillna(1.0)
    periods = max(len(nav), 1)
    total_return = float(nav_series.iloc[-1] - 1.0)
    annualized_return = float(nav_series.iloc[-1] ** (trading_days_per_year / periods) - 1.0) if periods > 0 else 0.0
    annualized_volatility = float(net_ret.std(ddof=0) * math.sqrt(trading_days_per_year))
    sharpe = float(annualized_return / annualized_volatility) if annualized_volatility > 0 else 0.0
    drawdown = nav_series / nav_series.cummax() - 1.0
    max_drawdown = float(drawdown.min()) if not drawdown.empty else 0.0
    avg_turnover = float(nav["turnover"].fillna(0.0).mean()) if "turnover" in nav else 0.0
    win_rate = float((net_ret > 0).mean()) if periods > 0 else 0.0
    message = "short_sample" if periods < 20 else "ok"
    return pd.DataFrame(
        [
            {
                "total_return": total_return,
                "annualized_return": annualized_return,
                "annualized_volatility": annualized_volatility,
                "sharpe": sharpe,
                "max_drawdown": max_drawdown,
                "avg_turnover": avg_turnover,
                "win_rate": win_rate,
                "trading_days": periods,
                "message": message,
            }
        ]
    )
