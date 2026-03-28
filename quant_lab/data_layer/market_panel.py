"""Build standardized market panel objects."""

from __future__ import annotations

import pandas as pd

from quant_lab.data_layer.cleaner import ensure_columns, normalize_code_column, normalize_trade_date

REQUIRED_MARKET_COLUMNS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "adj_factor",
    "close_adj",
    "turnover_rate",
    "pe",
    "pb",
    "total_mv",
]


def build_market_panel(daily: pd.DataFrame, adj_factor: pd.DataFrame, daily_basic: pd.DataFrame) -> pd.DataFrame:
    """Build market panel indexed by trade_date and asset."""
    daily = normalize_trade_date(normalize_code_column(daily))
    adj_factor = normalize_trade_date(normalize_code_column(adj_factor))
    daily_basic = normalize_trade_date(normalize_code_column(daily_basic))
    if "vol" in daily.columns and "volume" not in daily.columns:
        daily = daily.rename(columns={"vol": "volume"})
    merged = daily.merge(adj_factor[["trade_date", "asset", "adj_factor"]], on=["trade_date", "asset"], how="left")
    merged = merged.merge(
        daily_basic[["trade_date", "asset", "turnover_rate", "pe", "pb", "total_mv"]],
        on=["trade_date", "asset"],
        how="left",
    )
    merged = ensure_columns(merged, REQUIRED_MARKET_COLUMNS, fill_value=0.0)
    merged["adj_factor"] = merged["adj_factor"].replace(0.0, 1.0).fillna(1.0)
    latest_adj = merged.groupby("asset")["adj_factor"].transform("max").replace(0.0, 1.0)
    merged["close_adj"] = merged["close"] * merged["adj_factor"] / latest_adj
    merged = merged.sort_values(["trade_date", "asset"]).set_index(["trade_date", "asset"])
    return merged[REQUIRED_MARKET_COLUMNS]
