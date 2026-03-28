"""Hybrid source that combines TuShare primary and AkShare fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
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
    """Hybrid data source with sample fallback for smoke tests."""

    def __init__(self, enable_tushare: bool = True, enable_akshare_fallback: bool = True) -> None:
        self.primary = TushareSource(enabled=enable_tushare)
        self.fallback = AkshareSource(enabled=enable_akshare_fallback)

    def get_stock_basic(self) -> pd.DataFrame:
        df = self.primary.get_stock_basic()
        return df if not df.empty else self._sample_stock_basic()

    def get_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        df = self.primary.get_trade_calendar(start_date, end_date)
        return df if not df.empty else self._sample_calendar(start_date, end_date)

    def get_daily(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        primary = self.primary.get_daily(symbols, start_date, end_date)
        if not primary.empty:
            return primary
        fallback = self.fallback.get_daily(symbols, start_date, end_date)
        return fallback if not fallback.empty else self._sample_daily(symbols, start_date, end_date)

    def get_adj_factor(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        primary = self.primary.get_adj_factor(symbols, start_date, end_date)
        return primary if not primary.empty else self._sample_adj_factor(symbols, start_date, end_date)

    def get_daily_basic(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        primary = self.primary.get_daily_basic(symbols, start_date, end_date)
        return primary if not primary.empty else self._sample_daily_basic(symbols, start_date, end_date)

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

    @staticmethod
    def _sample_stock_basic() -> pd.DataFrame:
        assets = ["000001.SZ", "000002.SZ", "600000.SH", "600519.SH", "300750.SZ"]
        return pd.DataFrame(
            {
                "ts_code": assets,
                "symbol": [x.split(".")[0] for x in assets],
                "name": assets,
                "area": ["CN"] * len(assets),
                "industry": ["sample"] * len(assets),
                "list_date": ["20100101"] * len(assets),
            }
        )

    @staticmethod
    def _sample_calendar(start_date: str, end_date: str) -> pd.DataFrame:
        dates = pd.bdate_range(pd.to_datetime(start_date), pd.to_datetime(end_date))
        return pd.DataFrame({"exchange": "SSE", "cal_date": dates.strftime("%Y%m%d"), "is_open": 1})

    @staticmethod
    def _sample_daily(symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        dates = pd.bdate_range(pd.to_datetime(start_date), pd.to_datetime(end_date))
        frames: list[pd.DataFrame] = []
        for offset, symbol in enumerate(symbols):
            rng = np.random.default_rng(2026 + offset)
            ret = rng.normal(0.0005, 0.02, size=len(dates))
            close = 20 * np.cumprod(1 + ret)
            open_ = close * (1 + rng.normal(0, 0.003, size=len(dates)))
            high = np.maximum(open_, close) * (1 + rng.uniform(0.0, 0.01, size=len(dates)))
            low = np.minimum(open_, close) * (1 - rng.uniform(0.0, 0.01, size=len(dates)))
            vol = rng.integers(1_000_000, 10_000_000, size=len(dates))
            amount = vol * close * 100
            frames.append(
                pd.DataFrame(
                    {
                        "ts_code": symbol,
                        "trade_date": dates.strftime("%Y%m%d"),
                        "open": open_,
                        "high": high,
                        "low": low,
                        "close": close,
                        "vol": vol,
                        "amount": amount,
                    }
                )
            )
        return pd.concat(frames, ignore_index=True)

    @staticmethod
    def _sample_adj_factor(symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        dates = pd.bdate_range(pd.to_datetime(start_date), pd.to_datetime(end_date))
        frames = []
        for symbol in symbols:
            frames.append(pd.DataFrame({"ts_code": symbol, "trade_date": dates.strftime("%Y%m%d"), "adj_factor": 1.0}))
        return pd.concat(frames, ignore_index=True)

    @staticmethod
    def _sample_daily_basic(symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        dates = pd.bdate_range(pd.to_datetime(start_date), pd.to_datetime(end_date))
        frames: list[pd.DataFrame] = []
        for offset, symbol in enumerate(symbols):
            rng = np.random.default_rng(3026 + offset)
            frames.append(
                pd.DataFrame(
                    {
                        "ts_code": symbol,
                        "trade_date": dates.strftime("%Y%m%d"),
                        "turnover_rate": rng.uniform(0.5, 5.0, len(dates)),
                        "pe": rng.uniform(8.0, 40.0, len(dates)),
                        "pb": rng.uniform(0.8, 6.0, len(dates)),
                        "total_mv": rng.uniform(5e5, 5e6, len(dates)),
                    }
                )
            )
        return pd.concat(frames, ignore_index=True)
