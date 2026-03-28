"""Build standardized market panel objects."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
from loguru import logger
from pandas.api.types import is_datetime64_ns_dtype

from quant_lab.data_layer.cleaner import (
    add_optional_columns_as_nan,
    assert_required_columns,
    ensure_string_asset,
    normalize_code_column,
    normalize_trade_date,
)

REQUIRED_DAILY_COLUMNS = ["trade_date", "asset", "open", "high", "low", "close", "amount"]
REQUIRED_ADJ_COLUMNS = ["trade_date", "asset", "adj_factor"]
OPTIONAL_MARKET_COLUMNS = ["turnover_rate", "pe", "pb", "total_mv"]
REQUIRED_MARKET_COLUMNS = ["open", "high", "low", "close", "volume", "amount", "adj_factor", "close_adj"]
CANONICAL_MARKET_COLUMNS = REQUIRED_MARKET_COLUMNS + OPTIONAL_MARKET_COLUMNS


@dataclass(slots=True)
class ValidationReport:
    """Validation report for market panel."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)
    optional_missing_ratio: dict[str, float] = field(default_factory=dict)
    duplicate_keys: int = 0


def _normalize_daily_columns(daily: pd.DataFrame) -> pd.DataFrame:
    result = normalize_trade_date(normalize_code_column(daily))
    if "volume" not in result.columns:
        if "vol" in result.columns:
            result = result.rename(columns={"vol": "volume"})
        else:
            raise ValueError("daily is missing required volume field: expected either 'volume' or 'vol'.")
    result = ensure_string_asset(result)
    assert_required_columns(result, REQUIRED_DAILY_COLUMNS + ["volume"], "daily")
    return result


def _normalize_adj_columns(adj_factor: pd.DataFrame) -> pd.DataFrame:
    result = ensure_string_asset(normalize_trade_date(normalize_code_column(adj_factor)))
    assert_required_columns(result, REQUIRED_ADJ_COLUMNS, "adj_factor")
    return result


def _normalize_daily_basic_columns(daily_basic: pd.DataFrame) -> pd.DataFrame:
    if daily_basic.empty:
        empty = pd.DataFrame(columns=["trade_date", "asset", *OPTIONAL_MARKET_COLUMNS])
        return empty
    result = ensure_string_asset(normalize_trade_date(normalize_code_column(daily_basic)))
    assert_required_columns(result, ["trade_date", "asset"], "daily_basic")
    result, _ = add_optional_columns_as_nan(result, OPTIONAL_MARKET_COLUMNS, "daily_basic")
    return result


def build_market_panel(daily: pd.DataFrame, adj_factor: pd.DataFrame, daily_basic: pd.DataFrame) -> pd.DataFrame:
    """Build market panel indexed by trade_date and asset."""
    daily_norm = _normalize_daily_columns(daily)
    adj_norm = _normalize_adj_columns(adj_factor)
    basic_norm = _normalize_daily_basic_columns(daily_basic)

    merged = daily_norm.merge(adj_norm[["trade_date", "asset", "adj_factor"]], on=["trade_date", "asset"], how="left")
    merged = merged.merge(
        basic_norm[["trade_date", "asset", "turnover_rate", "pe", "pb", "total_mv"]],
        on=["trade_date", "asset"],
        how="left",
    )

    missing_required = [column for column in ["open", "high", "low", "close", "volume", "amount", "adj_factor"] if column not in merged.columns]
    if missing_required:
        raise ValueError(f"market_panel build failed, missing required columns after merge: {missing_required}")

    null_required_summary = {column: int(merged[column].isna().sum()) for column in ["open", "high", "low", "close", "volume", "amount", "adj_factor"]}
    null_required_summary = {key: value for key, value in null_required_summary.items() if value > 0}
    if null_required_summary:
        raise ValueError(f"market_panel build failed, required columns contain nulls: {null_required_summary}")

    merged, missing_optional = add_optional_columns_as_nan(merged, OPTIONAL_MARKET_COLUMNS, "market_panel")
    if missing_optional:
        logger.warning("market_panel optional columns added as NaN after merge: {}", missing_optional)

    merged["close_adj"] = merged["close"] * merged["adj_factor"]
    panel = merged.sort_values(["trade_date", "asset"]).set_index(["trade_date", "asset"])
    panel.index = pd.MultiIndex.from_arrays(
        [
            pd.to_datetime(panel.index.get_level_values("trade_date")).astype("datetime64[ns]"),
            panel.index.get_level_values("asset").astype(str),
        ],
        names=["trade_date", "asset"],
    )
    return panel[CANONICAL_MARKET_COLUMNS]


def validate_market_panel(market_panel: pd.DataFrame) -> ValidationReport:
    """Validate canonical market_panel schema and index properties."""
    report = ValidationReport()

    if market_panel.index.names != ["trade_date", "asset"]:
        report.errors.append(f"index names must be ['trade_date', 'asset'], got {market_panel.index.names}")

    if not isinstance(market_panel.index, pd.MultiIndex):
        report.errors.append("market_panel index must be a MultiIndex.")
        return report

    duplicate_keys = int(market_panel.index.duplicated().sum())
    report.duplicate_keys = duplicate_keys
    if duplicate_keys > 0:
        report.errors.append(f"duplicate index keys detected: {duplicate_keys}")
    else:
        report.infos.append("index uniqueness check passed.")

    trade_dates = market_panel.index.get_level_values("trade_date")
    if not is_datetime64_ns_dtype(trade_dates.dtype):
        report.errors.append(f"trade_date dtype must be datetime64[ns], got {trade_dates.dtype}")
    else:
        report.infos.append("trade_date dtype is datetime64[ns].")

    assets = market_panel.index.get_level_values("asset")
    if not assets.map(lambda value: isinstance(value, str)).all():
        report.errors.append("asset index level must be string-like.")
    else:
        report.infos.append("asset keys are string-like.")

    missing_required_columns = [column for column in REQUIRED_MARKET_COLUMNS if column not in market_panel.columns]
    if missing_required_columns:
        report.errors.append(f"missing required market_panel columns: {missing_required_columns}")
    else:
        report.infos.append("required columns are complete.")

    if not market_panel.index.is_monotonic_increasing:
        report.errors.append("market_panel index is not sorted.")
    else:
        report.infos.append("index sorting check passed.")

    for column in OPTIONAL_MARKET_COLUMNS:
        if column not in market_panel.columns:
            report.warnings.append(f"optional column missing from market_panel: {column}")
            report.optional_missing_ratio[column] = 1.0
            continue
        ratio = float(market_panel[column].isna().mean())
        report.optional_missing_ratio[column] = ratio
        if ratio > 0:
            report.warnings.append(f"optional column {column} has missing ratio {ratio:.2%}")

    return report
