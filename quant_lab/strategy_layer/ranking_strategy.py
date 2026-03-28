"""Simple ranking strategy."""

from __future__ import annotations

import pandas as pd

from quant_lab.strategy_layer.base import Strategy


class RankingStrategy(Strategy):
    """Linear weighted ranking strategy with equal-weight top-N holdings."""

    def __init__(self, factor_weights: dict[str, float], top_n: int = 10, rebalance_every: int = 5) -> None:
        self.factor_weights = factor_weights
        self.top_n = top_n
        self.rebalance_every = rebalance_every

    def generate_target_positions(self, factor_panel: pd.DataFrame) -> pd.DataFrame:
        frame = factor_panel.copy()
        weighted_score = 0.0
        for factor_name, weight in self.factor_weights.items():
            if factor_name not in frame.columns:
                continue
            weighted_score = weighted_score + frame[factor_name].fillna(0.0) * weight
        signal = frame.assign(score=weighted_score).reset_index()
        rebalance_dates = sorted(signal["trade_date"].drop_duplicates())
        selected_dates = set(rebalance_dates[:: max(self.rebalance_every, 1)])
        outputs: list[pd.DataFrame] = []
        for trade_date, group in signal.groupby("trade_date"):
            ranked = group.sort_values("score", ascending=False).copy()
            ranked["target_weight"] = 0.0
            if trade_date in selected_dates:
                chosen_idx = ranked.head(self.top_n).index
                if len(chosen_idx) > 0:
                    ranked.loc[chosen_idx, "target_weight"] = 1.0 / len(chosen_idx)
            outputs.append(ranked[["trade_date", "asset", "score", "target_weight"]])
        return pd.concat(outputs, ignore_index=True).set_index(["trade_date", "asset"]).sort_index()
