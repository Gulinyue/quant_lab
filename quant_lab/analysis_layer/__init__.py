"""Analysis layer."""

from quant_lab.analysis_layer.factor_analysis import (
    FactorResearchResult,
    calc_factor_research_summary,
    calc_forward_return,
    calc_quantile_returns,
    calc_rank_ic_series,
    run_single_factor_research,
)
from quant_lab.analysis_layer.factor_correlation import (
    build_factor_correlation_report,
    calc_factor_correlation_matrix,
    extract_high_correlation_pairs,
)
from quant_lab.analysis_layer.factor_research import run_single_factor_research_pipeline
from quant_lab.analysis_layer.factor_screening import (
    build_factor_screening_summary,
    screen_factor_predictiveness,
    screen_factor_quality,
    screen_factor_redundancy,
)

__all__ = [
    "FactorResearchResult",
    "build_factor_correlation_report",
    "build_factor_screening_summary",
    "calc_factor_correlation_matrix",
    "calc_factor_research_summary",
    "calc_forward_return",
    "calc_quantile_returns",
    "calc_rank_ic_series",
    "extract_high_correlation_pairs",
    "run_single_factor_research",
    "run_single_factor_research_pipeline",
    "screen_factor_predictiveness",
    "screen_factor_quality",
    "screen_factor_redundancy",
]
