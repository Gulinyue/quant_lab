"""Fetch and persist raw datasets."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import main as bootstrap
from quant_lab.common.io import write_dataframe
from quant_lab.common.paths import RAW_AKSHARE_DIR, RAW_TUSHARE_DIR
from quant_lab.data_layer.hybrid_source import HybridSource
from quant_lab.settings import AppSettings


def run() -> None:
    """Fetch raw data from TuShare primary and sample fallback."""
    bootstrap()
    settings = AppSettings.load()
    source = HybridSource()
    bundle = source.fetch_bundle(
        symbols=settings.data.get("universe", []),
        start_date=settings.data.get("start_date", "20240101").replace("-", ""),
        end_date=settings.data.get("end_date", "20251231").replace("-", ""),
    )
    write_dataframe(bundle.stock_basic, RAW_TUSHARE_DIR / "stock_basic.parquet")
    write_dataframe(bundle.trade_calendar, RAW_TUSHARE_DIR / "trade_calendar.parquet")
    write_dataframe(bundle.daily, RAW_TUSHARE_DIR / "daily.parquet")
    write_dataframe(bundle.adj_factor, RAW_TUSHARE_DIR / "adj_factor.parquet")
    write_dataframe(bundle.daily_basic, RAW_TUSHARE_DIR / "daily_basic.parquet")
    write_dataframe(bundle.daily.iloc[0:0], RAW_AKSHARE_DIR / "daily.parquet")
    logger.info("Raw data update completed.")


if __name__ == "__main__":
    run()
