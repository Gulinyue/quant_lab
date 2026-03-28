"""Generate target positions from factor panel."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import main as bootstrap
from quant_lab.common.io import read_dataframe, write_dataframe
from quant_lab.common.paths import WAREHOUSE_DIR
from quant_lab.settings import AppSettings
from quant_lab.strategy_layer.signal_builder import build_signals


def _ensure_panel_index(df):
    if {"trade_date", "asset"}.issubset(df.columns):
        return df.set_index(["trade_date", "asset"])
    return df


def run() -> None:
    """Generate strategy targets."""
    bootstrap()
    settings = AppSettings.load()
    factor_panel = _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "factor_panel.parquet"))
    strategy_cfg = settings.strategy
    target_positions = build_signals(
        factor_panel=factor_panel,
        factor_weights=strategy_cfg.get("factor_weights", {}),
        top_n=int(strategy_cfg.get("top_n", 3)),
        rebalance_every=int(strategy_cfg.get("rebalance_every", 5)),
    )
    write_dataframe(target_positions, WAREHOUSE_DIR / "target_positions.parquet")
    logger.info("Target positions saved with shape {}", target_positions.shape)


if __name__ == "__main__":
    run()
