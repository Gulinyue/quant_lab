"""Run minimal low-frequency daily backtest."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import main as bootstrap
from quant_lab.backtest_layer.engine import load_backtest_config, run_backtest
from quant_lab.backtest_layer.recorder import save_backtest_result
from quant_lab.common.io import read_dataframe
from quant_lab.common.paths import WAREHOUSE_DIR
from quant_lab.settings import AppSettings


def _ensure_panel_index(df):
    if {"trade_date", "asset"}.issubset(df.columns):
        return df.set_index(["trade_date", "asset"])
    return df


def run() -> None:
    """Run the daily backtest and persist outputs."""
    bootstrap()
    settings = AppSettings.load()
    market_panel = _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "market_panel.parquet"))
    target_positions = _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "target_positions.parquet"))
    config = load_backtest_config(settings.backtest)
    result = run_backtest(market_panel=market_panel, target_positions=target_positions, backtest_config=settings.backtest)
    save_backtest_result(result, WAREHOUSE_DIR)

    target_weight_matrix = target_positions["target_weight"].unstack("asset").sort_index()
    rebalance_dates = int((target_weight_matrix.fillna(0.0).diff().abs().sum(axis=1) > 0).sum())
    logger.info(
        "Backtest window: {} -> {}",
        str(result.nav.index.min().date()) if not result.nav.empty else "n/a",
        str(result.nav.index.max().date()) if not result.nav.empty else "n/a",
    )
    logger.info("Execution price convention: next_{}", config["execution"]["price"])
    logger.info("Rebalance date count: {}", rebalance_dates)
    logger.info("Trade record count: {}", len(result.trades))
    logger.info("NAV rows: {}", len(result.nav))
    logger.info("Final NAV: {}", float(result.nav['nav'].iloc[-1]) if not result.nav.empty else 0.0)
    logger.info("Performance summary: {}", result.performance_summary.to_dict(orient="records"))


if __name__ == "__main__":
    run()
