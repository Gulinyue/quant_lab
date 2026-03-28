"""Shared typed containers."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class BacktestResult:
    """Backtest outputs."""

    nav: pd.DataFrame
    daily_positions: pd.DataFrame
    trades: pd.DataFrame
    performance_summary: pd.DataFrame
