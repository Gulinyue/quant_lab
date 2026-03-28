"""Reusable file IO helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def write_dataframe(df: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame to parquet or CSV based on suffix."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".parquet":
        df.to_parquet(path, index=True)
        return
    if path.suffix.lower() == ".csv":
        df.to_csv(path, encoding="utf-8")
        return
    raise ValueError(f"Unsupported dataframe path: {path}")


def read_dataframe(path: Path) -> pd.DataFrame:
    """Read a DataFrame from parquet or CSV based on suffix."""
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported dataframe path: {path}")


def write_json(data: dict[str, Any], path: Path) -> None:
    """Write JSON with UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def read_json(path: Path) -> dict[str, Any]:
    """Read JSON with UTF-8 encoding."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
