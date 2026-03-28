"""Market data cleaning helpers."""

from __future__ import annotations

import pandas as pd


def normalize_code_column(df: pd.DataFrame, code_column: str = "ts_code") -> pd.DataFrame:
    """Normalize symbol naming to asset."""
    result = df.copy()
    if code_column in result.columns and "asset" not in result.columns:
        result["asset"] = result[code_column].astype(str)
    return result


def normalize_trade_date(df: pd.DataFrame, column: str = "trade_date") -> pd.DataFrame:
    """Normalize trade_date to pandas datetime."""
    result = df.copy()
    if column in result.columns:
        result[column] = pd.to_datetime(result[column], format="%Y%m%d", errors="coerce")
    return result


def ensure_columns(df: pd.DataFrame, columns: list[str], fill_value: float = 0.0) -> pd.DataFrame:
    """Ensure required columns exist."""
    result = df.copy()
    for column in columns:
        if column not in result.columns:
            result[column] = fill_value
    return result
