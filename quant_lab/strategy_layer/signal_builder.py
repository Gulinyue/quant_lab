"""Strategy-layer orchestration helpers."""

from __future__ import annotations

import pandas as pd

from quant_lab.strategy_layer.base import StrategyRunResult
from quant_lab.strategy_layer.factor_selector import load_strategy_config
from quant_lab.strategy_layer.ranking_strategy import RankingStrategy


def build_signals(
    factor_panel: pd.DataFrame,
    metadata: pd.DataFrame,
    screening: pd.DataFrame | None,
    strategy_config: dict,
) -> StrategyRunResult:
    """Build target positions from standard strategy-layer inputs."""
    normalized_config = load_strategy_config(strategy_config)
    strategy = RankingStrategy(strategy_config=normalized_config)
    return strategy.run(factor_panel=factor_panel, metadata=metadata, screening=screening)
