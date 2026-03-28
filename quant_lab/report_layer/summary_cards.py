"""Summary card helpers for HTML report context."""

from __future__ import annotations

import pandas as pd


def build_summary_cards(performance_summary: pd.DataFrame) -> list[dict[str, str]]:
    """Convert performance summary row into simple HTML summary cards."""
    if performance_summary.empty:
        return []
    row = performance_summary.iloc[0]
    return [
        {"label": "Total Return", "value": f"{float(row.get('total_return', 0.0)):.2%}"},
        {"label": "Annualized Return", "value": f"{float(row.get('annualized_return', 0.0)):.2%}"},
        {"label": "Sharpe", "value": f"{float(row.get('sharpe', 0.0)):.2f}"},
        {"label": "Max Drawdown", "value": f"{float(row.get('max_drawdown', 0.0)):.2%}"},
        {"label": "Trading Days", "value": str(int(row.get("trading_days", 0)))},
    ]
