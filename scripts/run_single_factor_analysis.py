"""Run minimal single-factor research."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import main as bootstrap
from quant_lab.analysis_layer.factor_research import run_single_factor_research_pipeline


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Run single-factor research.")
    parser.add_argument("--factor", required=True, help="Factor name to research.")
    parser.add_argument("--horizon", type=int, default=1, help="Forward-return horizon in trading days.")
    parser.add_argument("--quantiles", type=int, default=5, help="Number of quantile buckets.")
    return parser.parse_args()


def run() -> None:
    """Execute the single-factor research pipeline."""
    bootstrap()
    args = parse_args()
    result = run_single_factor_research_pipeline(
        factor_name=args.factor,
        horizon=args.horizon,
        quantiles=args.quantiles,
    )
    logger.info("Single-factor summary: {}", result.summary)


if __name__ == "__main__":
    run()
