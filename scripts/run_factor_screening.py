"""Build minimal factor screening recommendations."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import main as bootstrap
from quant_lab.analysis_layer.factor_screening import build_factor_screening_summary
from quant_lab.common.io import read_dataframe
from quant_lab.common.paths import WAREHOUSE_DIR


def run() -> None:
    """Generate factor screening summary from existing research artifacts."""
    bootstrap()
    diagnostics = read_dataframe(WAREHOUSE_DIR / "factor_diagnostics.csv")
    research_summary = read_dataframe(WAREHOUSE_DIR / "factor_research_summary.csv")
    high_corr_pairs = read_dataframe(WAREHOUSE_DIR / "high_correlation_pairs.csv")
    metadata = read_dataframe(WAREHOUSE_DIR / "factor_metadata.csv")

    summary = build_factor_screening_summary(
        diagnostics=diagnostics,
        research_summary=research_summary,
        high_corr_pairs=high_corr_pairs,
        metadata=metadata,
    )
    output_path = WAREHOUSE_DIR / "factor_screening_summary.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_path, index=False, encoding="utf-8")
    logger.info("Factor screening summary saved: {}", output_path)
    logger.info("Screening summary: {}", summary.to_dict(orient="records"))


if __name__ == "__main__":
    run()
