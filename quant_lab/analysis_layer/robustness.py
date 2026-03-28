"""Basic robustness placeholders for v0.1."""

from __future__ import annotations

import pandas as pd


def summarize_turnover(trades: pd.DataFrame) -> dict[str, float]:
    """Summarize turnover from weight change records."""
    if trades.empty:
        return {"avg_abs_weight_delta": 0.0, "trade_count": 0.0}
    return {
        "avg_abs_weight_delta": float(trades["weight_delta"].abs().mean()),
        "trade_count": float(len(trades)),
    }
