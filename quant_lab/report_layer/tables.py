"""Table builders for report outputs."""

from __future__ import annotations

import pandas as pd


def build_performance_table(performance_summary: pd.DataFrame) -> pd.DataFrame:
    """Return performance summary table."""
    return performance_summary.copy()


def build_strategy_summary_table(strategy_diagnostics: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    """Build high-level strategy summary table."""
    daily = strategy_diagnostics.drop_duplicates(subset=["trade_date"])[["trade_date", "candidate_count", "selected_count"]]
    return pd.DataFrame(
        [
            {
                "rebalance_days": int(strategy_diagnostics["rebalance_flag"].fillna(False).astype(bool).sum() / max(strategy_diagnostics["factor_name"].nunique(), 1)),
                "trade_count": int(len(trades)),
                "avg_candidate_count": float(daily["candidate_count"].mean()) if not daily.empty else 0.0,
                "avg_selected_count": float(daily["selected_count"].mean()) if not daily.empty else 0.0,
            }
        ]
    )


def build_factor_summary_table(metadata: pd.DataFrame | None, screening: pd.DataFrame | None) -> pd.DataFrame:
    """Build factor-layer summary counts."""
    meta_counts = metadata["status"].value_counts().to_dict() if metadata is not None and not metadata.empty and "status" in metadata.columns else {}
    screening_counts = screening["recommendation"].value_counts().to_dict() if screening is not None and not screening.empty and "recommendation" in screening.columns else {}
    return pd.DataFrame(
        [
            {
                "active_factor_count": int(meta_counts.get("active", 0)),
                "testing_factor_count": int(meta_counts.get("testing", 0)),
                "deprecated_factor_count": int(meta_counts.get("deprecated", 0)),
                "keep_count": int(screening_counts.get("keep", 0)),
                "review_count": int(screening_counts.get("review", 0)),
                "deprecate_candidate_count": int(screening_counts.get("deprecate_candidate", 0)),
            }
        ]
    )


def build_top_trades_table(trades: pd.DataFrame, max_rows: int = 20) -> pd.DataFrame:
    """Build top trades table sorted by amount."""
    if trades.empty:
        return pd.DataFrame(columns=["trade_date", "asset", "side", "price", "shares", "amount", "cost"])
    return trades.sort_values(["amount", "cost"], ascending=[False, False]).head(max_rows).reset_index(drop=True)


def build_latest_positions_table(daily_positions: pd.DataFrame, max_rows: int = 20) -> pd.DataFrame:
    """Build latest positions snapshot."""
    if daily_positions.empty:
        return pd.DataFrame(columns=["trade_date", "asset", "weight", "shares", "close", "market_value"])
    latest_date = daily_positions.index.get_level_values("trade_date").max()
    latest = daily_positions.xs(latest_date, level="trade_date").reset_index()
    latest.insert(0, "trade_date", latest_date)
    return latest.sort_values("market_value", ascending=False).head(max_rows).reset_index(drop=True)
