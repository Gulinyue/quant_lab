"""High-level entry points for factor research workflows."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_lab.analysis_layer.factor_analysis import FactorResearchResult, run_single_factor_research
from quant_lab.common.io import read_dataframe
from quant_lab.common.paths import REPORT_DIR, WAREHOUSE_DIR


def run_single_factor_research_pipeline(
    factor_name: str,
    *,
    market_panel_path: Path | None = None,
    factor_panel_path: Path | None = None,
    horizon: int = 1,
    quantiles: int = 5,
) -> FactorResearchResult:
    """Load inputs, run single-factor research, and update warehouse summary."""
    market_path = market_panel_path or (WAREHOUSE_DIR / "market_panel.parquet")
    factor_path = factor_panel_path or (WAREHOUSE_DIR / "factor_panel.parquet")
    market_panel = read_dataframe(market_path)
    factor_panel = read_dataframe(factor_path)

    output_dir = REPORT_DIR / "factor_research" / factor_name
    result = run_single_factor_research(
        market_panel=market_panel,
        factor_panel=factor_panel,
        factor_name=factor_name,
        horizon=horizon,
        quantiles=quantiles,
        output_dir=output_dir,
    )
    _update_research_summary(result.summary)
    return result


def _update_research_summary(summary: dict[str, object]) -> None:
    """Upsert single-factor summary into warehouse CSV."""
    path = WAREHOUSE_DIR / "factor_research_summary.csv"
    incoming = pd.DataFrame([summary])
    if path.exists():
        existing = pd.read_csv(path)
        existing = existing[existing["factor_name"] != summary["factor_name"]]
        merged = pd.concat([existing, incoming], ignore_index=True)
    else:
        merged = incoming
    path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(path, index=False, encoding="utf-8")
