"""Backtest output persistence helpers."""

from __future__ import annotations

from pathlib import Path

from quant_lab.common.io import write_dataframe, write_json
from quant_lab.common.types import BacktestResult


def save_backtest_result(result: BacktestResult, output_dir: Path) -> None:
    """Persist backtest outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    write_dataframe(result.nav, output_dir / "nav.parquet")
    write_dataframe(result.daily_positions, output_dir / "daily_positions.parquet")
    write_dataframe(result.trades, output_dir / "trades.parquet")
    write_json(result.metrics, output_dir / "metrics.json")
