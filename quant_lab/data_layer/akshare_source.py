"""AkShare supplement data source."""

from __future__ import annotations

from typing import Iterable

import pandas as pd
from loguru import logger

from quant_lab.data_layer.base import MarketDataSource

AKSHARE_DAILY_COLUMN_MAP = {
    "\u65e5\u671f": "trade_date",
    "\u5f00\u76d8": "open",
    "\u6536\u76d8": "close",
    "\u6700\u9ad8": "high",
    "\u6700\u4f4e": "low",
    "\u6210\u4ea4\u91cf": "vol",
    "\u6210\u4ea4\u989d": "amount",
}

AKSHARE_DAILY_REQUIRED_COLUMNS = list(AKSHARE_DAILY_COLUMN_MAP.keys())


class AkshareSource(MarketDataSource):
    """Supplemental AkShare source with a real daily fallback."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def get_stock_basic(self) -> pd.DataFrame:
        return pd.DataFrame()

    def get_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame()

    def fetch_daily_one_symbol(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch one-symbol daily data from AkShare and map it to raw daily schema."""
        if not self.enabled:
            logger.info("AkShare fallback is disabled.")
            return pd.DataFrame()
        import akshare as ak

        code = symbol.split(".")[0]
        market = "sh" if symbol.endswith(".SH") else "sz"
        ak_symbol = f"{market}{code}"
        hist = ak.stock_zh_a_hist(symbol=ak_symbol, period="daily", start_date=start_date, end_date=end_date, adjust="")
        if hist.empty:
            logger.warning("AkShare returned empty daily data for {}", symbol)
            return pd.DataFrame()

        missing_columns = [column for column in AKSHARE_DAILY_REQUIRED_COLUMNS if column not in hist.columns]
        if missing_columns:
            raise ValueError(
                f"AkShare daily columns mismatch for {symbol}. Missing columns: {missing_columns}. Returned columns: {list(hist.columns)}"
            )

        mapped = hist.rename(columns=AKSHARE_DAILY_COLUMN_MAP)
        mapped["trade_date"] = pd.to_datetime(mapped["trade_date"], errors="coerce").dt.strftime("%Y%m%d")
        mapped["ts_code"] = symbol
        return mapped[["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"]]

    def get_daily(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        for symbol in symbols:
            try:
                frames.append(self.fetch_daily_one_symbol(symbol, start_date=start_date, end_date=end_date))
            except Exception as exc:
                logger.warning("AkShare daily failed for {}: {}", symbol, exc)
        valid_frames = [frame for frame in frames if not frame.empty]
        return pd.concat(valid_frames, ignore_index=True) if valid_frames else pd.DataFrame()

    def get_adj_factor(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame()

    def get_daily_basic(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame()
