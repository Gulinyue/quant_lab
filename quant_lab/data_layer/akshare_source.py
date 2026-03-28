"""AkShare supplement data source."""

from __future__ import annotations

from typing import Iterable

import pandas as pd
from loguru import logger

from quant_lab.data_layer.base import MarketDataSource


class AkshareSource(MarketDataSource):
    """Supplemental AkShare source with minimal v0.1 coverage."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def get_stock_basic(self) -> pd.DataFrame:
        return pd.DataFrame()

    def get_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame()

    def get_daily(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        if not self.enabled:
            logger.info("AkShare fallback is disabled.")
            return pd.DataFrame()
        try:
            import akshare as ak
        except Exception as exc:
            logger.warning("AkShare import failed: {}", exc)
            return pd.DataFrame()

        frames: list[pd.DataFrame] = []
        for symbol in symbols:
            try:
                code = symbol.split(".")[0]
                market = "sh" if symbol.endswith(".SH") else "sz"
                hist = ak.stock_zh_a_hist(symbol=f"{market}{code}", period="daily", start_date=start_date, end_date=end_date, adjust="")
                if hist.empty:
                    continue
                hist = hist.rename(
                    columns={
                        "日期": "trade_date",
                        "开盘": "open",
                        "收盘": "close",
                        "最高": "high",
                        "最低": "low",
                        "成交量": "vol",
                        "成交额": "amount",
                    }
                )
                hist["ts_code"] = symbol
                hist["trade_date"] = pd.to_datetime(hist["trade_date"]).dt.strftime("%Y%m%d")
                frames.append(hist[["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"]])
            except Exception as exc:
                logger.warning("AkShare daily failed for {}: {}", symbol, exc)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def get_adj_factor(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame()

    def get_daily_basic(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame()
