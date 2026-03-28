"""Generate target positions from factor panel and research constraints."""

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
    """Generate strategy targets and diagnostics."""
    bootstrap()
    settings = AppSettings.load()
    factor_panel = _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "factor_panel.parquet"))
    metadata = read_dataframe(WAREHOUSE_DIR / "factor_metadata.csv")
    screening_path = WAREHOUSE_DIR / "factor_screening_summary.csv"
    screening = read_dataframe(screening_path) if screening_path.exists() else None

    result = build_signals(
        factor_panel=factor_panel,
        metadata=metadata,
        screening=screening,
        strategy_config=settings.strategy,
    )

    target_path = WAREHOUSE_DIR / "target_positions.parquet"
    diagnostics_path = WAREHOUSE_DIR / "strategy_diagnostics.csv"
    write_dataframe(result.target_positions, target_path)
    diagnostics_path.parent.mkdir(parents=True, exist_ok=True)
    result.diagnostics.to_csv(diagnostics_path, index=False, encoding="utf-8")

    logger.info("Candidate factors from config: {}", settings.strategy.get("factors", {}).get("selected", []))
    logger.info("Selected factors used: {}", result.selected_factors)
    logger.info("Dropped factors: {}", result.dropped_factors)
    logger.info(
        "Daily selected counts: {}",
        result.diagnostics[["trade_date", "selected_count"]].drop_duplicates().to_dict(orient="records"),
    )
    logger.info("Target positions saved to: {}", target_path)
    logger.info("Strategy diagnostics saved to: {}", diagnostics_path)
    logger.info("Target positions shape: {}", result.target_positions.shape)


if __name__ == "__main__":
    run()
