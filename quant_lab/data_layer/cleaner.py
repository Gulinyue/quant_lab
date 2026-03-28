"""Market data cleaning helpers."""

from __future__ import annotations

from typing import Iterable

import pandas as pd
from loguru import logger


def normalize_code_column(df: pd.DataFrame, code_column: str = "ts_code") -> pd.DataFrame:
    """Normalize symbol naming to asset."""
    result = df.copy()
    if code_column in result.columns and "asset" not in result.columns:
        result["asset"] = result[code_column].astype(str)
    return result


def normalize_trade_date(df: pd.DataFrame, column: str = "trade_date") -> pd.DataFrame:
    """Normalize trade_date to pandas datetime64[ns]."""
    result = df.copy()
    if column in result.columns:
        result[column] = pd.to_datetime(result[column], format="%Y%m%d", errors="coerce").astype("datetime64[ns]")
    return result


def ensure_string_asset(df: pd.DataFrame, column: str = "asset") -> pd.DataFrame:
    """Ensure asset is stored as a stable string key."""
    result = df.copy()
    if column in result.columns:
        result[column] = result[column].astype(str)
    return result


def assert_required_columns(df: pd.DataFrame, required_columns: Iterable[str], dataset_name: str) -> None:
    """Raise if required columns are missing."""
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"{dataset_name} missing required columns: {missing}")


def add_optional_columns_as_nan(df: pd.DataFrame, optional_columns: Iterable[str], dataset_name: str) -> tuple[pd.DataFrame, list[str]]:
    """Add missing optional columns as NaN and return the missing list."""
    result = df.copy()
    missing: list[str] = []
    for column in optional_columns:
        if column not in result.columns:
            result[column] = float("nan")
            missing.append(column)
    if missing:
        logger.warning("{} missing optional columns, filled with NaN: {}", dataset_name, missing)
    return result, missing
