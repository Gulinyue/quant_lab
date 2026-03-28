"""Run factor correlation analysis."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import main as bootstrap
from quant_lab.analysis_layer.factor_correlation import build_factor_correlation_report
from quant_lab.common.io import read_dataframe
from quant_lab.common.paths import WAREHOUSE_DIR


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Run factor correlation analysis.")
    parser.add_argument("--threshold", type=float, default=0.8, help="Absolute correlation threshold.")
    return parser.parse_args()


def run() -> None:
    """Execute factor correlation analysis."""
    bootstrap()
    args = parse_args()
    factor_panel = read_dataframe(WAREHOUSE_DIR / "factor_panel.parquet")
    matrix, pairs = build_factor_correlation_report(factor_panel, threshold=args.threshold)
    logger.info("Correlation matrix shape: {}", matrix.shape)
    logger.info("High-correlation pairs: {}", pairs.to_dict(orient="records"))


if __name__ == "__main__":
    run()
