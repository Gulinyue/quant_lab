"""Report-layer exporter orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from quant_lab.common.paths import FIGURE_DIR, TABLE_DIR
from quant_lab.report_layer.context_builder import build_report_context, load_report_inputs
from quant_lab.report_layer.html_report import build_html_report
from quant_lab.report_layer.plots import (
    plot_correlation_heatmap,
    plot_drawdown,
    plot_nav,
    plot_screening_distribution,
    plot_turnover,
)
from quant_lab.report_layer.tables import (
    build_factor_summary_table,
    build_latest_positions_table,
    build_performance_table,
    build_strategy_summary_table,
    build_top_trades_table,
)


def export_report(report_config: dict[str, Any]) -> dict[str, Any]:
    """Generate report figures, tables, and HTML."""
    inputs = load_report_inputs()
    nav = inputs["nav"]
    if "trade_date" in nav.columns:
        nav = nav.set_index("trade_date")
    screening = inputs["factor_screening_summary"]
    strategy_diag = inputs["strategy_diagnostics"]
    trades = inputs["trades"]
    daily_positions = inputs["daily_positions"]
    performance_summary = inputs["performance_summary"]
    metadata = inputs.get("factor_metadata", pd.DataFrame())
    corr_matrix = inputs.get("factor_correlation_matrix", pd.DataFrame())

    figures = {
        "nav": FIGURE_DIR / "nav_curve.png",
        "drawdown": FIGURE_DIR / "drawdown_curve.png",
        "turnover": FIGURE_DIR / "turnover_curve.png",
        "screening_distribution": FIGURE_DIR / "screening_distribution.png",
        "correlation_heatmap": FIGURE_DIR / "factor_correlation_heatmap.png",
    }
    plot_nav(nav, figures["nav"])
    plot_drawdown(nav, figures["drawdown"])
    plot_turnover(nav, figures["turnover"])
    plot_screening_distribution(screening, figures["screening_distribution"])
    if corr_matrix is not None and not corr_matrix.empty:
        plot_correlation_heatmap(corr_matrix.set_index(corr_matrix.columns[0]) if "Unnamed: 0" in corr_matrix.columns else corr_matrix, figures["correlation_heatmap"])

    performance_table = build_performance_table(performance_summary)
    strategy_table = build_strategy_summary_table(strategy_diag, trades)
    factor_table = build_factor_summary_table(metadata, screening)
    top_trades_table = build_top_trades_table(trades, max_rows=int(report_config["report"].get("max_trade_rows", 20)))
    latest_positions_table = build_latest_positions_table(daily_positions, max_rows=int(report_config["report"].get("max_position_rows", 20)))

    tables = {
        "performance_summary": TABLE_DIR / "performance_summary.csv",
        "strategy_summary": TABLE_DIR / "strategy_summary.csv",
        "factor_summary": TABLE_DIR / "factor_summary.csv",
        "top_trades": TABLE_DIR / "top_trades.csv",
        "latest_positions": TABLE_DIR / "latest_positions.csv",
    }
    performance_table.to_csv(tables["performance_summary"], index=False, encoding="utf-8")
    strategy_table.to_csv(tables["strategy_summary"], index=False, encoding="utf-8")
    factor_table.to_csv(tables["factor_summary"], index=False, encoding="utf-8")
    top_trades_table.to_csv(tables["top_trades"], index=False, encoding="utf-8")
    latest_positions_table.to_csv(tables["latest_positions"], index=False, encoding="utf-8")

    context = build_report_context(inputs, report_config)
    context.update(
        {
            "figures": {
                "nav": "../figures/nav_curve.png",
                "drawdown": "../figures/drawdown_curve.png",
                "turnover": "../figures/turnover_curve.png",
                "screening_distribution": "../figures/screening_distribution.png",
                "correlation_heatmap": "../figures/factor_correlation_heatmap.png" if figures["correlation_heatmap"].exists() else "",
            },
            "performance_table": performance_table.to_html(index=False),
            "strategy_table": strategy_table.to_html(index=False),
            "factor_table": factor_table.to_html(index=False),
            "top_trades_table": top_trades_table.to_html(index=False),
            "latest_positions_table": latest_positions_table.to_html(index=False),
        }
    )

    output_html = Path(report_config["report"].get("output_html", "reports/html/backtest_report.html"))
    build_html_report(context, output_html)
    return {
        "inputs": inputs,
        "figure_paths": [str(path) for path in figures.values() if path.exists()],
        "table_paths": [str(path) for path in tables.values()],
        "html_path": str(output_html),
    }
