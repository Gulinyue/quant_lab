"""Factor diagnostics and metadata export helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_lab.factor_layer.factor_metadata import FactorMetadata


def build_factor_diagnostic_row(
    metadata: FactorMetadata,
    factor_series: pd.Series | None,
    row_count: int,
    status: str,
    message: str = "",
) -> dict[str, object]:
    """Build one diagnostics row."""
    if factor_series is None or factor_series.empty:
        return {
            "factor_name": metadata.name,
            "group": metadata.group,
            "required_columns": ",".join(metadata.required_columns),
            "direction": metadata.direction,
            "min_history": metadata.min_history,
            "row_count": row_count,
            "non_null_ratio": 0.0,
            "finite_ratio": 0.0,
            "missing_ratio": 1.0,
            "status": status,
            "message": message,
        }

    non_null_ratio = float(factor_series.notna().mean())
    finite_mask = pd.Series(False, index=factor_series.index)
    valid = factor_series.dropna()
    if not valid.empty:
        finite_mask.loc[valid.index] = np.isfinite(pd.to_numeric(valid, errors="coerce"))
        finite_ratio = float(finite_mask.mean())
    else:
        finite_ratio = 0.0

    return {
        "factor_name": metadata.name,
        "group": metadata.group,
        "required_columns": ",".join(metadata.required_columns),
        "direction": metadata.direction,
        "min_history": metadata.min_history,
        "row_count": row_count,
        "non_null_ratio": non_null_ratio,
        "finite_ratio": finite_ratio,
        "missing_ratio": 1.0 - non_null_ratio,
        "status": status,
        "message": message,
    }


def build_metadata_frame(metadata_list: list[FactorMetadata], enabled_factors: set[str]) -> pd.DataFrame:
    """Build a flat factor metadata DataFrame."""
    rows = []
    for metadata in metadata_list:
        row = metadata.to_record()
        row["enabled_in_config"] = metadata.name in enabled_factors
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["status", "group", "name"]).reset_index(drop=True) if rows else pd.DataFrame()
