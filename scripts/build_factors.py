"""Build factor panel from market panel."""

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
from quant_lab.factor_layer.factor_panel import build_factor_panel


def _ensure_panel_index(df):
    if {"trade_date", "asset"}.issubset(df.columns):
        return df.set_index(["trade_date", "asset"])
    return df


def run() -> None:
    """Build and persist factor panel."""
    bootstrap()
    market_panel = _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "market_panel.parquet"))
    factor_panel = build_factor_panel(market_panel)
    write_dataframe(factor_panel, WAREHOUSE_DIR / "factor_panel.parquet")
    logger.info("Factor panel saved with shape {}", factor_panel.shape)


if __name__ == "__main__":
    run()
