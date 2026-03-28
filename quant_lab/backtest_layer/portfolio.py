"""Portfolio helpers."""

from __future__ import annotations

import pandas as pd


def pivot_target_weights(target_positions: pd.DataFrame, all_dates: pd.Index) -> pd.DataFrame:
    """Convert target positions into a date x asset weight matrix."""
    weights = target_positions["target_weight"].unstack("asset").sort_index()
    return weights.reindex(all_dates).ffill().fillna(0.0)
