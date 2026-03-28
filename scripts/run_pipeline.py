"""Run the end-to-end research-to-report pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import main as bootstrap
from quant_lab.pipeline.orchestrator import run_pipeline


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Run Quant Lab end-to-end pipeline.")
    parser.add_argument("--run-id", default=None, help="Readable run id suffix or full run id.")
    parser.add_argument("--skip-correlation", action="store_true", help="Skip factor correlation stage.")
    parser.add_argument("--skip-single-factor", action="store_true", help="Skip batch single-factor research stage.")
    parser.add_argument("--skip-report", action="store_true", help="Skip report generation stage.")
    return parser.parse_args()


def run() -> None:
    """Execute the full pipeline with artifact isolation."""
    bootstrap()
    args = parse_args()
    context = run_pipeline(
        run_id=args.run_id,
        skip_correlation=args.skip_correlation,
        skip_single_factor=args.skip_single_factor,
        skip_report=args.skip_report,
    )
    logger.info("Pipeline run_id: {}", context.run_id)
    logger.info("Pipeline status: {}", context.status)
    logger.info("Artifact root: {}", context.artifact_root)
    logger.info("Stage statuses: {}", context.stage_statuses)
    if context.warnings:
        logger.warning("Pipeline warnings: {}", context.warnings)
    if context.errors:
        logger.error("Pipeline errors: {}", context.errors)


if __name__ == "__main__":
    run()
