"""Factor preprocessing helpers."""

from __future__ import annotations

import pandas as pd


def winsorize_by_date(df: pd.DataFrame, lower: float = 0.05, upper: float = 0.95) -> pd.DataFrame:
    """Winsorize cross-sectional factor values by trade date."""
    def _clip(group: pd.DataFrame) -> pd.DataFrame:
        lower_q = group.quantile(lower)
        upper_q = group.quantile(upper)
        return group.clip(lower=lower_q, upper=upper_q, axis=1)

    return df.groupby(level="trade_date", group_keys=False).apply(_clip)


def zscore_by_date(df: pd.DataFrame) -> pd.DataFrame:
    """Z-score factor values by trade date."""
    def _zscore(group: pd.DataFrame) -> pd.DataFrame:
        std = group.std(ddof=0).replace(0, 1.0)
        return (group - group.mean()) / std

    return df.groupby(level="trade_date", group_keys=False).apply(_zscore)


def rank_by_date(df: pd.DataFrame, ascending: bool = True) -> pd.DataFrame:
    """Rank factor values by trade date."""
    return df.groupby(level="trade_date", group_keys=False).rank(pct=True, ascending=ascending)
