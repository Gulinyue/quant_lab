"""Factor preprocessing helpers."""

from __future__ import annotations

import pandas as pd


def winsorize_by_date(df: pd.DataFrame, lower: float = 0.05, upper: float = 0.95) -> pd.DataFrame:
    """Winsorize a factor DataFrame cross-sectionally by trade date."""

    def _clip(group: pd.DataFrame) -> pd.DataFrame:
        if group.empty:
            return group
        valid = group.dropna(how="all", axis=1)
        if valid.empty:
            return group
        lower_q = valid.quantile(lower)
        upper_q = valid.quantile(upper)
        clipped = group.copy()
        clipped[valid.columns] = valid.clip(lower=lower_q, upper=upper_q, axis=1)
        return clipped

    return df.groupby(level="trade_date", group_keys=False).apply(_clip)


def zscore_by_date(df: pd.DataFrame) -> pd.DataFrame:
    """Z-score a factor DataFrame cross-sectionally by trade date."""

    def _zscore(group: pd.DataFrame) -> pd.DataFrame:
        if group.empty:
            return group
        mean = group.mean()
        std = group.std(ddof=0)
        safe_std = std.mask(std.abs() < 1e-12, 1.0).fillna(1.0)
        return (group - mean) / safe_std

    return df.groupby(level="trade_date", group_keys=False).apply(_zscore)


def rank_by_date(df: pd.DataFrame, ascending: bool = True) -> pd.DataFrame:
    """Rank a factor DataFrame cross-sectionally by trade date."""
    return df.groupby(level="trade_date", group_keys=False).rank(pct=True, ascending=ascending)
