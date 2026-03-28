"""Table generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def metrics_to_table(metrics: dict[str, float]) -> pd.DataFrame:
    """Convert metrics dictionary into a display table."""
    return pd.DataFrame({"metric": list(metrics.keys()), "value": list(metrics.values())})


def save_markdown_table(df: pd.DataFrame, output_path: Path) -> None:
    """Save a DataFrame as Markdown."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    header = "| " + " | ".join(map(str, df.columns)) + " |"
    separator = "| " + " | ".join(["---"] * len(df.columns)) + " |"
    rows = ["| " + " | ".join(map(str, row)) + " |" for row in df.itertuples(index=False, name=None)]
    output_path.write_text("\n".join([header, separator, *rows]), encoding="utf-8")
