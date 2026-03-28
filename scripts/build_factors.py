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
from quant_lab.settings import AppSettings


def _ensure_panel_index(df):
    if {"trade_date", "asset"}.issubset(df.columns):
        return df.set_index(["trade_date", "asset"])
    return df


def run() -> None:
    """Build and persist factor panel."""
    bootstrap()
    settings = AppSettings.load()
    market_panel = _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "market_panel.parquet"))
    result = build_factor_panel(market_panel, factor_config=settings.factors)
    write_dataframe(result.factor_panel, WAREHOUSE_DIR / "factor_panel.parquet")
    diagnostics_path = WAREHOUSE_DIR / "factor_diagnostics.csv"
    diagnostics_path.parent.mkdir(parents=True, exist_ok=True)
    result.diagnostics.to_csv(diagnostics_path, index=False, encoding="utf-8")
    logger.info("Enabled factors: {}", result.enabled_factors)
    logger.info("Succeeded factors: {}", result.succeeded_factors)
    logger.info("Failed factors: {}", result.failed_factors)
    if not result.diagnostics.empty:
        logger.info(
            "Factor missing summary: {}",
            result.diagnostics[["factor_name", "missing_ratio", "status"]].to_dict(orient="records"),
        )
    logger.info("Factor panel saved with shape {}", result.factor_panel.shape)


if __name__ == "__main__":
    run()
