"""Report context builder."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from quant_lab.common.io import read_dataframe
from quant_lab.common.paths import FIGURE_DIR, REPORT_DIR, TABLE_DIR, WAREHOUSE_DIR
from quant_lab.report_layer.summary_cards import build_summary_cards
from quant_lab.report_layer.validators import require_files


def load_report_inputs() -> dict[str, Any]:
    """Load standard report-layer input objects."""
    required = [
        WAREHOUSE_DIR / "factor_research_summary.csv",
        WAREHOUSE_DIR / "factor_screening_summary.csv",
        WAREHOUSE_DIR / "strategy_diagnostics.csv",
        WAREHOUSE_DIR / "nav.parquet",
        WAREHOUSE_DIR / "trades.parquet",
        WAREHOUSE_DIR / "daily_positions.parquet",
        WAREHOUSE_DIR / "performance_summary.csv",
    ]
    require_files(required)

    optional_paths = {
        "factor_metadata": WAREHOUSE_DIR / "factor_metadata.csv",
        "high_correlation_pairs": WAREHOUSE_DIR / "high_correlation_pairs.csv",
        "factor_correlation_matrix": WAREHOUSE_DIR / "factor_correlation_matrix.csv",
    }

    inputs: dict[str, Any] = {
        "factor_research_summary": read_dataframe(WAREHOUSE_DIR / "factor_research_summary.csv"),
        "factor_screening_summary": read_dataframe(WAREHOUSE_DIR / "factor_screening_summary.csv"),
        "strategy_diagnostics": read_dataframe(WAREHOUSE_DIR / "strategy_diagnostics.csv"),
        "nav": read_dataframe(WAREHOUSE_DIR / "nav.parquet"),
        "trades": read_dataframe(WAREHOUSE_DIR / "trades.parquet"),
        "daily_positions": read_dataframe(WAREHOUSE_DIR / "daily_positions.parquet"),
        "performance_summary": read_dataframe(WAREHOUSE_DIR / "performance_summary.csv"),
        "optional_loaded": [],
        "optional_skipped": [],
    }
    for key, path in optional_paths.items():
        if path.exists():
            inputs[key] = read_dataframe(path)
            inputs["optional_loaded"].append(str(path))
        else:
            inputs[key] = pd.DataFrame()
            inputs["optional_skipped"].append(str(path))
    return inputs


def build_report_context(inputs: dict[str, Any], report_config: dict[str, Any]) -> dict[str, Any]:
    """Build HTML report render context."""
    performance_summary = inputs["performance_summary"]
    nav = inputs["nav"].copy()
    if "trade_date" in nav.columns:
        nav = nav.set_index("trade_date")
    nav.index = pd.to_datetime(nav.index)

    strategy_diag = inputs["strategy_diagnostics"]
    factor_screening = inputs["factor_screening_summary"]
    factor_research_summary = inputs["factor_research_summary"]
    factor_metadata = inputs.get("factor_metadata", pd.DataFrame())

    perf_row = performance_summary.iloc[0] if not performance_summary.empty else pd.Series(dtype=object)
    trading_days = int(perf_row.get("trading_days", 0) or 0)
    short_sample = str(perf_row.get("message", "")) == "short_sample" or trading_days < 20

    sample_start = str(nav.index.min().date()) if not nav.empty else "n/a"
    sample_end = str(nav.index.max().date()) if not nav.empty else "n/a"
    strategy_daily = strategy_diag.drop_duplicates(subset=["trade_date"]) if not strategy_diag.empty else pd.DataFrame()

    return {
        "title": report_config["report"]["title"],
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary_cards": build_summary_cards(performance_summary),
        "short_sample_warning": short_sample,
        "warning_message": "Sample is too short. Report is only for structure validation and does not support strategy conclusions."
        if short_sample
        else "",
        "run_environment": {
            "workspace": str(REPORT_DIR.parent),
            "figure_dir": str(FIGURE_DIR),
            "table_dir": str(TABLE_DIR),
        },
        "backtest_assumptions": [
            "Signals are known after close and execute on next_open.",
            "Current backtest is long-only and strategy weights are equal-weight targets.",
            "Cost model includes commission, slippage, and stamp_tax_sell.",
            "Suspension, limit-up/down, complex slippage, and risk model are not supported.",
            "Results are for research and structure validation, not live tradability.",
        ],
        "sample_summary": {
            "sample_start": sample_start,
            "sample_end": sample_end,
            "trading_days": trading_days,
        },
        "strategy_summary": {
            "rebalance_days": int(strategy_diag["rebalance_flag"].fillna(False).astype(bool).sum() / max(strategy_diag["factor_name"].nunique(), 1))
            if not strategy_diag.empty
            else 0,
            "avg_candidate_count": float(strategy_daily["candidate_count"].mean()) if not strategy_daily.empty else 0.0,
            "avg_selected_count": float(strategy_daily["selected_count"].mean()) if not strategy_daily.empty else 0.0,
        },
        "factor_summary": {
            "research_rows": int(len(factor_research_summary)),
            "screening_rows": int(len(factor_screening)),
            "metadata_rows": int(len(factor_metadata)),
        },
        "include_factor_section": bool(report_config["report"].get("include_factor_section", True)),
        "include_strategy_section": bool(report_config["report"].get("include_strategy_section", True)),
        "include_trade_table": bool(report_config["report"].get("include_trade_table", True)),
        "max_trade_rows": int(report_config["report"].get("max_trade_rows", 20)),
        "max_position_rows": int(report_config["report"].get("max_position_rows", 20)),
    }
