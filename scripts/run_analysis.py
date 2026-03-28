"""Run performance and factor analysis."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import main as bootstrap
from quant_lab.analysis_layer.factor_analysis import compute_rank_ic
from quant_lab.analysis_layer.performance import yearly_breakdown
from quant_lab.analysis_layer.robustness import summarize_turnover
from quant_lab.common.io import read_dataframe, read_json, write_dataframe, write_json
from quant_lab.common.paths import TABLE_DIR, WAREHOUSE_DIR


def _ensure_panel_index(df):
    if {"trade_date", "asset"}.issubset(df.columns):
        return df.set_index(["trade_date", "asset"])
    return df


def run() -> None:
    """Build analysis outputs."""
    bootstrap()
    nav = read_dataframe(WAREHOUSE_DIR / "backtest" / "nav.parquet")
    if "trade_date" in nav.columns:
        nav = nav.set_index("trade_date")
    trades = read_dataframe(WAREHOUSE_DIR / "backtest" / "trades.parquet")
    metrics = read_json(WAREHOUSE_DIR / "backtest" / "metrics.json")
    market_panel = _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "market_panel.parquet"))
    factor_panel = _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "factor_panel.parquet"))

    yearly = yearly_breakdown(nav["daily_return"])
    rank_ic = compute_rank_ic(factor_panel, market_panel, "mom_20")
    robustness = summarize_turnover(trades)
    merged_metrics = {**metrics, **robustness}

    write_dataframe(yearly, TABLE_DIR / "yearly_breakdown.csv")
    write_dataframe(rank_ic, TABLE_DIR / "rank_ic_mom20.csv")
    write_json(merged_metrics, TABLE_DIR / "analysis_metrics.json")
    logger.info("Analysis outputs saved.")


if __name__ == "__main__":
    run()
