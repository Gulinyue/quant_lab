"""Build standardized market panel from raw datasets."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import main as bootstrap
from quant_lab.common.io import read_dataframe, write_dataframe
from quant_lab.common.paths import RAW_TUSHARE_DIR, WAREHOUSE_DIR
from quant_lab.data_layer.market_panel import build_market_panel


def run() -> None:
    """Build and persist market panel."""
    bootstrap()
    daily = read_dataframe(RAW_TUSHARE_DIR / "daily.parquet")
    adj_factor = read_dataframe(RAW_TUSHARE_DIR / "adj_factor.parquet")
    daily_basic = read_dataframe(RAW_TUSHARE_DIR / "daily_basic.parquet")
    market_panel = build_market_panel(daily=daily, adj_factor=adj_factor, daily_basic=daily_basic)
    write_dataframe(market_panel, WAREHOUSE_DIR / "market_panel.parquet")
    logger.info("Market panel saved with shape {}", market_panel.shape)


if __name__ == "__main__":
    run()
