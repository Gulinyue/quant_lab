"""Generate figures, markdown tables, and HTML report."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import main as bootstrap
from quant_lab.common.io import read_dataframe, read_json
from quant_lab.common.paths import FIGURE_DIR, HTML_DIR, TABLE_DIR, WAREHOUSE_DIR
from quant_lab.report_layer.html_report import build_html_report
from quant_lab.report_layer.plots import plot_nav
from quant_lab.report_layer.tables import metrics_to_table, save_markdown_table
from quant_lab.settings import AppSettings


def run() -> None:
    """Build report assets."""
    bootstrap()
    settings = AppSettings.load()
    nav = read_dataframe(WAREHOUSE_DIR / "backtest" / "nav.parquet")
    if "trade_date" in nav.columns:
        nav = nav.set_index("trade_date")
    metrics = read_json(TABLE_DIR / "analysis_metrics.json")
    metrics_table = metrics_to_table(metrics)
    figure_path = FIGURE_DIR / "nav.png"
    markdown_path = TABLE_DIR / "metrics.md"
    html_path = HTML_DIR / "report.html"

    plot_nav(nav, figure_path)
    save_markdown_table(metrics_table, markdown_path)
    build_html_report(
        title=settings.report.get("title", "Quant Lab Report"),
        summary=settings.report.get("summary", ""),
        metrics_table=metrics_table,
        nav_figure="../figures/nav.png",
        output_path=html_path,
    )


if __name__ == "__main__":
    run()
