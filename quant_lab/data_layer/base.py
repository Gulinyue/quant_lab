"""Market data source abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

import pandas as pd


class MarketDataSource(ABC):
    """Abstract market data source."""

    @abstractmethod
    def get_stock_basic(self) -> pd.DataFrame:
        """Return stock master data."""

    @abstractmethod
    def get_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Return trading calendar."""

    @abstractmethod
    def get_daily(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Return daily OHLCV data."""

    @abstractmethod
    def get_adj_factor(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Return adjustment factors."""

    @abstractmethod
    def get_daily_basic(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Return daily basic metrics."""
