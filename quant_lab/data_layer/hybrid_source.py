"""Hybrid source that combines TuShare primary and AkShare daily fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd
from loguru import logger

from quant_lab.data_layer.akshare_source import AkshareSource
from quant_lab.data_layer.base import MarketDataSource
from quant_lab.data_layer.tushare_source import TushareSource


@dataclass(slots=True)
class RawDatasetBundle:
    """Raw dataset bundle."""

    stock_basic: pd.DataFrame
    trade_calendar: pd.DataFrame
    daily: pd.DataFrame
    adj_factor: pd.DataFrame
    daily_basic: pd.DataFrame


class HybridSource(MarketDataSource):
    """Hybrid data source with TuShare primary and AkShare daily supplement."""

    def __init__(self, enable_tushare: bool = True, enable_akshare_fallback: bool = True) -> None:
        self.primary = TushareSource(enabled=enable_tushare)
        self.fallback = AkshareSource(enabled=enable_akshare_fallback)

    def get_stock_basic(self) -> pd.DataFrame:
        return self.primary.get_stock_basic()

    def get_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        return self.primary.get_trade_calendar(start_date, end_date)

    def get_daily(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        primary = self.primary.get_daily(symbols, start_date, end_date)
        if not primary.empty:
            return primary
        logger.warning("TuShare daily returned empty data, trying AkShare symbol-level fallback.")
        return self.fallback.get_daily(symbols, start_date, end_date)

    def get_adj_factor(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        return self.primary.get_adj_factor(symbols, start_date, end_date)

    def get_daily_basic(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        return self.primary.get_daily_basic(symbols, start_date, end_date)

    def fetch_bundle(self, symbols: Iterable[str], start_date: str, end_date: str) -> RawDatasetBundle:
        """Fetch all raw datasets required for v0.1."""
        symbol_list = list(symbols)
        logger.info("Fetching raw data for {} symbols from {} to {}", len(symbol_list), start_date, end_date)
        return RawDatasetBundle(
            stock_basic=self.get_stock_basic(),
            trade_calendar=self.get_trade_calendar(start_date, end_date),
            daily=self.get_daily(symbol_list, start_date, end_date),
            adj_factor=self.get_adj_factor(symbol_list, start_date, end_date),
            daily_basic=self.get_daily_basic(symbol_list, start_date, end_date),
        )

    def supplement_daily_by_symbols(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Expose AkShare symbol-level daily supplement for manual gap filling."""
        return self.fallback.get_daily(symbols, start_date, end_date)
