"""Factor panel construction and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from loguru import logger
from pandas.api.types import is_numeric_dtype

from quant_lab.factor_layer import technical as _technical  # noqa: F401
from quant_lab.factor_layer import fundamental as _fundamental  # noqa: F401
from quant_lab.factor_layer.factor_diagnostics import build_factor_diagnostic_row, build_metadata_frame
from quant_lab.factor_layer.lifecycle import is_deprecated_status
from quant_lab.factor_layer.preprocess import winsorize_by_date, zscore_by_date
from quant_lab.factor_layer.registry import FACTOR_REGISTRY, FactorSpec


@dataclass(slots=True)
class FactorBuildResult:
    """Factor panel build outputs."""

    factor_panel: pd.DataFrame
    diagnostics: pd.DataFrame
    enabled_factors: list[str]
    succeeded_factors: list[str]
    failed_factors: dict[str, str]
    deprecated_enabled_factors: list[str]
    metadata: pd.DataFrame


def _validate_market_panel_index(market_panel: pd.DataFrame) -> None:
    if not isinstance(market_panel.index, pd.MultiIndex):
        raise ValueError("market_panel must use MultiIndex[trade_date, asset].")
    if market_panel.index.names != ["trade_date", "asset"]:
        raise ValueError(f"market_panel index names must be ['trade_date', 'asset'], got {market_panel.index.names}")
    if not market_panel.index.is_unique:
        raise ValueError("market_panel index must be unique.")


def _extract_enabled_factor_names(factor_config: dict) -> list[str]:
    if "factors" in factor_config:
        return [item["name"] for item in factor_config.get("factors", []) if item.get("enabled", True)]
    return list(factor_config.get("factor_names", []))


def build_factor_panel(market_panel: pd.DataFrame, factor_config: dict | None = None) -> FactorBuildResult:
    """Build a factor panel and diagnostics from the market panel."""
    _validate_market_panel_index(market_panel)
    factor_config = factor_config or {}
    preprocess_cfg = factor_config.get("preprocess", {})
    enabled_factors = _extract_enabled_factor_names(factor_config)

    factor_frames: list[pd.Series] = []
    diagnostics_rows: list[dict[str, object]] = []
    succeeded: list[str] = []
    failed: dict[str, str] = {}
    deprecated_enabled: list[str] = []

    for factor_name in enabled_factors:
        if not FACTOR_REGISTRY.has(factor_name):
            failed[factor_name] = "factor not registered"
            diagnostics_rows.append(
                {
                    "factor_name": factor_name,
                    "group": "unknown",
                    "required_columns": "",
                    "direction": "",
                    "min_history": None,
                    "row_count": len(market_panel),
                    "non_null_ratio": 0.0,
                    "finite_ratio": 0.0,
                    "missing_ratio": 1.0,
                    "status": "failed",
                    "message": "factor not registered",
                }
            )
            logger.warning("Factor skipped because it is not registered: {}", factor_name)
            continue

        spec = FACTOR_REGISTRY.get(factor_name)
        if is_deprecated_status(spec.status):
            deprecated_enabled.append(spec.name)
            logger.warning("Deprecated factor is enabled in config: {}", spec.name)
        missing_dependencies = [column for column in spec.required_columns if column not in market_panel.columns]
        if missing_dependencies:
            message = f"missing dependencies: {missing_dependencies}"
            failed[factor_name] = message
            diagnostics_rows.append(build_factor_diagnostic_row(spec.metadata, None, len(market_panel), "failed", message))
            logger.warning("Factor {} failed dependency check: {}", factor_name, missing_dependencies)
            continue

        try:
            factor_series = spec.func(market_panel)
            factor_series = factor_series.reindex(market_panel.index)
            factor_series.name = spec.name
            factor_series = pd.to_numeric(factor_series, errors="coerce").replace([float("inf"), float("-inf")], pd.NA)
            factor_frames.append(factor_series)
            succeeded.append(spec.name)
            diagnostics_rows.append(build_factor_diagnostic_row(spec.metadata, factor_series, len(market_panel), "ok"))
        except Exception as exc:
            message = str(exc)
            failed[factor_name] = message
            diagnostics_rows.append(build_factor_diagnostic_row(spec.metadata, None, len(market_panel), "failed", message))
            logger.warning("Factor {} build failed: {}", factor_name, exc)

    factor_panel = pd.concat(factor_frames, axis=1) if factor_frames else pd.DataFrame(index=market_panel.index)
    if not factor_panel.empty:
        factor_panel = factor_panel.sort_index()

    if preprocess_cfg.get("winsorize", True) and not factor_panel.empty:
        factor_panel = winsorize_by_date(
            factor_panel,
            lower=float(preprocess_cfg.get("winsorize_lower", 0.05)),
            upper=float(preprocess_cfg.get("winsorize_upper", 0.95)),
        )
    if preprocess_cfg.get("zscore", True) and not factor_panel.empty:
        factor_panel = zscore_by_date(factor_panel)

    diagnostics = pd.DataFrame(diagnostics_rows)
    if not diagnostics.empty:
        diagnostics = diagnostics.sort_values(["status", "factor_name"]).reset_index(drop=True)
    metadata = build_metadata_frame([spec.metadata for spec in FACTOR_REGISTRY.list_specs()], set(enabled_factors))

    if not factor_panel.empty:
        if factor_panel.index.names != ["trade_date", "asset"]:
            raise ValueError("factor_panel index names must be ['trade_date', 'asset']")
        if not factor_panel.index.is_unique:
            raise ValueError("factor_panel index must be unique")
        if factor_panel.columns.duplicated().any():
            raise ValueError("factor_panel contains duplicate factor columns")
        non_numeric = [column for column in factor_panel.columns if not is_numeric_dtype(factor_panel[column])]
        if non_numeric:
            raise ValueError(f"factor_panel contains non-numeric columns: {non_numeric}")

    return FactorBuildResult(
        factor_panel=factor_panel,
        diagnostics=diagnostics,
        enabled_factors=enabled_factors,
        succeeded_factors=succeeded,
        failed_factors=failed,
        deprecated_enabled_factors=deprecated_enabled,
        metadata=metadata,
    )
