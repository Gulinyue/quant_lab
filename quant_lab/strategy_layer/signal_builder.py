"""Strategy signal helpers."""

from __future__ import annotations

import pandas as pd

from quant_lab.strategy_layer.ranking_strategy import RankingStrategy


def build_signals(factor_panel: pd.DataFrame, factor_weights: dict[str, float], top_n: int, rebalance_every: int) -> pd.DataFrame:
    """Build target positions from a ranking strategy."""
    strategy = RankingStrategy(factor_weights=factor_weights, top_n=top_n, rebalance_every=rebalance_every)
    return strategy.generate_target_positions(factor_panel)
