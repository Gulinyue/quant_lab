"""Incrementally update raw datasets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import main as bootstrap
from quant_lab.data_layer.cache_manager import CacheManager
from quant_lab.data_layer.hybrid_source import HybridSource
from quant_lab.settings import AppSettings
from quant_lab.common.paths import RAW_AKSHARE_DIR, RAW_TUSHARE_DIR

PRIMARY_KEYS = ["ts_code", "trade_date"]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Incrementally update raw quant data.")
    parser.add_argument("--start", dest="start_date", default=None, help="Override config start date, e.g. 2024-01-01")
    parser.add_argument("--end", dest="end_date", default=None, help="Override config end date, e.g. 2024-12-31")
    parser.add_argument("--force-full", action="store_true", help="Ignore local checkpoints and refresh full configured range.")
    return parser.parse_args()


def _format_date(value: str) -> str:
    return value.replace("-", "")


def _load_open_trade_days(source: HybridSource, start_date: str, end_date: str) -> list[str]:
    trade_cal = source.get_trade_calendar(start_date, end_date)
    if trade_cal.empty:
        raise RuntimeError("trade_cal refresh failed; cannot drive incremental per-trade-date updates.")
    refreshed = trade_cal.copy()
    refreshed["cal_date"] = refreshed["cal_date"].astype(str)
    refreshed = refreshed.sort_values("cal_date")
    cache.save(refreshed, RAW_TUSHARE_DIR / "trade_cal.parquet")
    logger.info("trade_cal refreshed in full because it is small metadata and acts as the incremental driver.")
    return refreshed.loc[refreshed["is_open"].astype(str) == "1", "cal_date"].tolist()


def _refresh_stock_basic(source: HybridSource) -> None:
    stock_basic = source.get_stock_basic()
    if stock_basic.empty:
        logger.warning("stock_basic refresh returned empty data.")
        return
    cache.save(stock_basic, RAW_TUSHARE_DIR / "stock_basic.parquet")
    logger.info("stock_basic refreshed in full because it is a small reference table.")


def _get_incremental_trade_days(path: Path, open_days: list[str], force_full: bool) -> list[str]:
    if force_full or not path.exists():
        return open_days
    old_df = cache.load(path)
    if old_df.empty or "trade_date" not in old_df.columns:
        return open_days
    existing_trade_dates = {
        trade_date
        for trade_date in pd.to_datetime(old_df["trade_date"], errors="coerce").dt.strftime("%Y%m%d").dropna().tolist()
    }
    missing_trade_days = [trade_date for trade_date in open_days if trade_date not in existing_trade_dates]
    return missing_trade_days


def _fetch_by_trade_days(trade_days: list[str], fetch_func, dataset_name: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for trade_date in trade_days:
        try:
            frame = fetch_func(trade_date)
            if frame.empty:
                logger.warning("{} returned empty data for trade_date={}", dataset_name, trade_date)
                continue
            frames.append(frame)
        except Exception as exc:
            logger.warning("{} failed for trade_date={}: {}", dataset_name, trade_date, exc)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _incremental_update_table(path: Path, open_days: list[str], fetch_func, dataset_name: str) -> None:
    old_df = pd.DataFrame() if args.force_full else cache.load_if_exists(path)
    trade_days = _get_incremental_trade_days(path, open_days, args.force_full)
    if not trade_days:
        logger.info("{} already up to date. old_rows={} final_rows={} date_range=[{}, {}]", dataset_name, len(old_df), len(old_df), *(_date_range(old_df)))
        return

    logger.info(
        "{} incremental fetch start. missing_trade_days={} first_missing={} last_missing={} force_full={}",
        dataset_name,
        len(trade_days),
        trade_days[0] if trade_days else None,
        trade_days[-1] if trade_days else None,
        args.force_full,
    )
    new_df = _fetch_by_trade_days(trade_days, fetch_func=fetch_func, dataset_name=dataset_name)
    merged_df, summary = cache.merge_incremental(
        old_df=old_df,
        new_df=new_df,
        primary_keys=PRIMARY_KEYS,
        sort_columns=["trade_date", "ts_code"],
    )
    cache.save(merged_df, path)
    logger.info(
        "{} update summary old_rows={} new_rows={} merged_rows={} dedup_removed_rows={} final_rows={} final_date_range=[{}, {}]",
        dataset_name,
        summary.old_rows,
        summary.new_rows,
        summary.merged_rows,
        summary.dedup_removed_rows,
        summary.final_rows,
        summary.min_trade_date,
        summary.max_trade_date,
    )


def _date_range(df: pd.DataFrame) -> tuple[str | None, str | None]:
    if df.empty or "trade_date" not in df.columns:
        return None, None
    trade_dates = pd.to_datetime(df["trade_date"], errors="coerce")
    return (
        trade_dates.min().strftime("%Y-%m-%d") if pd.notna(trade_dates.min()) else None,
        trade_dates.max().strftime("%Y-%m-%d") if pd.notna(trade_dates.max()) else None,
    )


def run() -> None:
    """Incrementally update raw datasets."""
    bootstrap()
    settings = AppSettings.load()
    source = HybridSource()

    start_date = _format_date(args.start_date or settings.data.get("start_date", "2024-01-01"))
    end_date = _format_date(args.end_date or settings.data.get("end_date", "2025-12-31"))

    _refresh_stock_basic(source)
    open_days = _load_open_trade_days(source, start_date=start_date, end_date=end_date)

    _incremental_update_table(
        path=RAW_TUSHARE_DIR / "daily.parquet",
        open_days=open_days,
        fetch_func=source.primary.fetch_daily_by_trade_date,
        dataset_name="daily",
    )
    _incremental_update_table(
        path=RAW_TUSHARE_DIR / "adj_factor.parquet",
        open_days=open_days,
        fetch_func=source.primary.fetch_adj_factor_by_trade_date,
        dataset_name="adj_factor",
    )
    _incremental_update_table(
        path=RAW_TUSHARE_DIR / "daily_basic.parquet",
        open_days=open_days,
        fetch_func=source.primary.fetch_daily_basic_by_trade_date,
        dataset_name="daily_basic",
    )

    logger.info(
        "AkShare status: only symbol-level daily fallback is implemented; adj_factor and daily_basic remain TODO by design."
    )
    logger.info("Raw data incremental update completed.")


cache = CacheManager()
args = parse_args()


if __name__ == "__main__":
    run()
