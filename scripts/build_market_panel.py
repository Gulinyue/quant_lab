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
from quant_lab.data_layer.market_panel import build_market_panel, validate_market_panel


def _date_range(df) -> tuple[str | None, str | None]:
    if df.empty:
        return None, None
    trade_dates = df.index.get_level_values("trade_date")
    return trade_dates.min().strftime("%Y-%m-%d"), trade_dates.max().strftime("%Y-%m-%d")


def run() -> None:
    """Build and persist market panel."""
    bootstrap()
    daily = read_dataframe(RAW_TUSHARE_DIR / "daily.parquet")
    adj_factor = read_dataframe(RAW_TUSHARE_DIR / "adj_factor.parquet")
    daily_basic = read_dataframe(RAW_TUSHARE_DIR / "daily_basic.parquet")

    logger.info(
        "market_panel inputs daily_rows={} adj_factor_rows={} daily_basic_rows={}",
        len(daily),
        len(adj_factor),
        len(daily_basic),
    )

    market_panel = build_market_panel(daily=daily, adj_factor=adj_factor, daily_basic=daily_basic)
    report = validate_market_panel(market_panel)
    if report.errors:
        for item in report.errors:
            logger.error("market_panel validator: {}", item)
        raise RuntimeError("market_panel validation failed.")
    for item in report.warnings:
        logger.warning("market_panel validator: {}", item)
    for item in report.infos:
        logger.info("market_panel validator: {}", item)

    write_dataframe(market_panel, WAREHOUSE_DIR / "market_panel.parquet")
    min_date, max_date = _date_range(market_panel)
    logger.info(
        "Market panel saved rows={} date_range=[{}, {}] columns={} optional_missing_ratio={} duplicate_keys={}",
        len(market_panel),
        min_date,
        max_date,
        list(market_panel.columns),
        report.optional_missing_ratio,
        report.duplicate_keys,
    )


if __name__ == "__main__":
    run()
