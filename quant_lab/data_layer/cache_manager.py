"""Simple cache manager for raw and warehouse data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from quant_lab.common.io import read_dataframe, write_dataframe


@dataclass(slots=True)
class MergeSummary:
    """Incremental merge statistics."""

    old_rows: int
    new_rows: int
    merged_rows: int
    dedup_removed_rows: int
    final_rows: int
    min_trade_date: str | None
    max_trade_date: str | None


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

    def load_if_exists(self, path: Path) -> pd.DataFrame:
        """Load cached data if present, else return an empty DataFrame."""
        return self.load(path) if self.exists(path) else pd.DataFrame()

    def merge_incremental(
        self,
        old_df: pd.DataFrame,
        new_df: pd.DataFrame,
        primary_keys: list[str],
        sort_columns: list[str],
    ) -> tuple[pd.DataFrame, MergeSummary]:
        """Merge old and new data, deduplicate on primary keys, and sort."""
        old_rows = len(old_df)
        new_rows = len(new_df)
        if old_df.empty and new_df.empty:
            summary = MergeSummary(0, 0, 0, 0, 0, None, None)
            return pd.DataFrame(), summary

        if old_df.empty:
            merged = new_df.copy()
        elif new_df.empty:
            merged = old_df.copy()
        else:
            merged = pd.concat([old_df, new_df], ignore_index=True, sort=False)

        merged_rows = len(merged)
        deduped = merged.drop_duplicates(subset=primary_keys, keep="last").sort_values(sort_columns).reset_index(drop=True)
        final_rows = len(deduped)
        dedup_removed_rows = merged_rows - final_rows

        if "trade_date" in deduped.columns and not deduped.empty:
            trade_dates = pd.to_datetime(deduped["trade_date"], errors="coerce")
            min_trade_date = trade_dates.min().strftime("%Y-%m-%d") if pd.notna(trade_dates.min()) else None
            max_trade_date = trade_dates.max().strftime("%Y-%m-%d") if pd.notna(trade_dates.max()) else None
        else:
            min_trade_date = None
            max_trade_date = None

        summary = MergeSummary(
            old_rows=old_rows,
            new_rows=new_rows,
            merged_rows=merged_rows,
            dedup_removed_rows=dedup_removed_rows,
            final_rows=final_rows,
            min_trade_date=min_trade_date,
            max_trade_date=max_trade_date,
        )
        return deduped, summary
