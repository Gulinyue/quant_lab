"""Run simplified low-frequency backtest."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import main as bootstrap
from quant_lab.backtest_layer.engine import run_backtest
from quant_lab.backtest_layer.recorder import save_backtest_result
from quant_lab.common.io import read_dataframe
from quant_lab.common.paths import WAREHOUSE_DIR
from quant_lab.settings import AppSettings


def _ensure_panel_index(df):
    if {"trade_date", "asset"}.issubset(df.columns):
        return df.set_index(["trade_date", "asset"])
    return df


def run() -> None:
    """Run backtest and persist outputs."""
    bootstrap()
    settings = AppSettings.load()
    market_panel = _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "market_panel.parquet"))
    target_positions = _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "target_positions.parquet"))
    result = run_backtest(
        market_panel=market_panel,
        target_positions=target_positions,
        commission=float(settings.backtest.get("commission", 0.0003)),
        slippage=float(settings.backtest.get("slippage", 0.0005)),
        stamp_tax=float(settings.backtest.get("stamp_tax", 0.001)),
    )
    save_backtest_result(result, WAREHOUSE_DIR / "backtest")
    logger.info("Backtest completed.")


if __name__ == "__main__":
    run()
