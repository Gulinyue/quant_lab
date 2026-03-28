"""Generate figures, tables, and HTML report."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import main as bootstrap
from quant_lab.report_layer.exporter import export_report
from quant_lab.settings import AppSettings


def run() -> None:
    """Build the minimal HTML backtest report."""
    bootstrap()
    settings = AppSettings.load()
    result = export_report(settings.report)
    logger.info("Successfully loaded required report inputs.")
    if result["inputs"]["optional_loaded"]:
        logger.info("Loaded optional inputs: {}", result["inputs"]["optional_loaded"])
    if result["inputs"]["optional_skipped"]:
        logger.info("Skipped optional inputs: {}", result["inputs"]["optional_skipped"])
    logger.info("Generated figure count: {}", len(result["figure_paths"]))
    logger.info("Generated table count: {}", len(result["table_paths"]))
    logger.info("HTML report path: {}", result["html_path"])


if __name__ == "__main__":
    run()
