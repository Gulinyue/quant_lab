"""TuShare data source implementation."""

from __future__ import annotations

import os
import time
from typing import Callable, Iterable

import pandas as pd
from loguru import logger

from quant_lab.data_layer.base import MarketDataSource


class TushareSource(MarketDataSource):
    """Primary TuShare data source."""

    def __init__(self, enabled: bool = True, retry_times: int = 3, retry_sleep: float = 0.8) -> None:
        self.enabled = enabled
        self.retry_times = retry_times
        self.retry_sleep = retry_sleep
        self.token = os.getenv("TUSHARE_TOKEN", "").strip()
        self._pro = None

    def _client(self):
        """Build a TuShare client lazily."""
        if not self.enabled:
            raise RuntimeError("TuShare is disabled.")
        if self._pro is not None:
            return self._pro
        if not self.token:
            raise RuntimeError("TUSHARE_TOKEN is not configured.")
        import tushare as ts

        ts.set_token(self.token)
        self._pro = ts.pro_api()
        return self._pro

    def _call_with_retry(self, label: str, func: Callable[[], pd.DataFrame]) -> pd.DataFrame:
        """Retry a TuShare API call a small number of times."""
        last_error: Exception | None = None
        for attempt in range(1, self.retry_times + 1):
            try:
                return func()
            except Exception as exc:
                last_error = exc
                logger.warning("TuShare call failed for {} on attempt {}/{}: {}", label, attempt, self.retry_times, exc)
                if attempt < self.retry_times:
                    time.sleep(self.retry_sleep)
        raise RuntimeError(f"TuShare call failed for {label}: {last_error}") from last_error

    def get_stock_basic(self) -> pd.DataFrame:
        try:
            return self._call_with_retry(
                "stock_basic",
                lambda: self._client().stock_basic(
                    exchange="",
                    list_status="L",
                    fields="ts_code,symbol,name,area,industry,list_date",
                ),
            )
        except Exception as exc:
            logger.warning("TuShare stock_basic failed: {}", exc)
            return pd.DataFrame()

    def get_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        try:
            return self._call_with_retry(
                f"trade_cal:{start_date}:{end_date}",
                lambda: self._client().trade_cal(exchange="", start_date=start_date, end_date=end_date),
            )
        except Exception as exc:
            logger.warning("TuShare trade_cal failed: {}", exc)
            return pd.DataFrame()

    def fetch_daily_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        """Fetch the full-market daily snapshot for one trade date."""
        return self._call_with_retry(
            f"daily:{trade_date}",
            lambda: self._client().daily(trade_date=trade_date),
        )

    def fetch_adj_factor_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        """Fetch the full-market adj_factor snapshot for one trade date."""
        return self._call_with_retry(
            f"adj_factor:{trade_date}",
            lambda: self._client().adj_factor(trade_date=trade_date),
        )

    def fetch_daily_basic_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        """Fetch the full-market daily_basic snapshot for one trade date."""
        return self._call_with_retry(
            f"daily_basic:{trade_date}",
            lambda: self._client().daily_basic(
                trade_date=trade_date,
                fields="ts_code,trade_date,turnover_rate,pe,pb,total_mv",
            ),
        )

    def get_daily(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        try:
            client = self._client()
        except Exception as exc:
            logger.warning("TuShare client init failed for daily: {}", exc)
            return pd.DataFrame()
        for symbol in symbols:
            try:
                frames.append(client.daily(ts_code=symbol, start_date=start_date, end_date=end_date))
            except Exception as exc:
                logger.warning("TuShare daily failed for {}: {}", symbol, exc)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def get_adj_factor(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        try:
            client = self._client()
        except Exception as exc:
            logger.warning("TuShare client init failed for adj_factor: {}", exc)
            return pd.DataFrame()
        for symbol in symbols:
            try:
                frames.append(client.adj_factor(ts_code=symbol, start_date=start_date, end_date=end_date))
            except Exception as exc:
                logger.warning("TuShare adj_factor failed for {}: {}", symbol, exc)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def get_daily_basic(self, symbols: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        try:
            client = self._client()
        except Exception as exc:
            logger.warning("TuShare client init failed for daily_basic: {}", exc)
            return pd.DataFrame()
        for symbol in symbols:
            try:
                frames.append(
                    client.daily_basic(
                        ts_code=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        fields="ts_code,trade_date,turnover_rate,pe,pb,total_mv",
                    )
                )
            except Exception as exc:
                logger.warning("TuShare daily_basic failed for {}: {}", symbol, exc)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
