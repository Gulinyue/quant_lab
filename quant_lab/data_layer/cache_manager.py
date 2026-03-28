"""Simple cache manager for raw and warehouse data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_lab.common.io import read_dataframe, write_dataframe


class CacheManager:
    """Filesystem-backed cache helper."""

    def exists(self, path: Path) -> bool:
        """Check whether a cache file exists."""
        return path.exists()

    def load(self, path: Path) -> pd.DataFrame:
        """Load a cached DataFrame."""
        return read_dataframe(path)

    def save(self, df: pd.DataFrame, path: Path) -> None:
        """Save a cached DataFrame."""
        write_dataframe(df, path)
