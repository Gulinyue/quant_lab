"""Factor correlation analysis helpers."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from quant_lab.common.paths import REPORT_DIR, WAREHOUSE_DIR


def calc_factor_correlation_matrix(factor_panel: pd.DataFrame) -> pd.DataFrame:
    """Average per-date cross-sectional Spearman correlations across factors."""
    factors = list(factor_panel.columns)
    if not factors:
        return pd.DataFrame()

    sum_matrix = pd.DataFrame(0.0, index=factors, columns=factors)
    count_matrix = pd.DataFrame(0, index=factors, columns=factors, dtype=int)

    for _, group in factor_panel.groupby(level="trade_date"):
        clean = group.replace([np.inf, -np.inf], np.nan)
        if len(clean) < 2:
            continue
        corr = clean.corr(method="spearman")
        for row_name in corr.index:
            for col_name in corr.columns:
                value = corr.at[row_name, col_name]
                if pd.notna(value):
                    sum_matrix.at[row_name, col_name] += float(value)
                    count_matrix.at[row_name, col_name] += 1

    with np.errstate(invalid="ignore", divide="ignore"):
        correlation = sum_matrix.divide(count_matrix.replace(0, np.nan))
    return correlation


def extract_high_correlation_pairs(correlation_matrix: pd.DataFrame, threshold: float = 0.8) -> pd.DataFrame:
    """Extract upper-triangle factor pairs above the absolute-correlation threshold."""
    rows: list[dict[str, object]] = []
    columns = list(correlation_matrix.columns)
    for left_idx, left_name in enumerate(columns):
        for right_name in columns[left_idx + 1 :]:
            corr_value = correlation_matrix.at[left_name, right_name]
            if pd.isna(corr_value):
                continue
            if abs(float(corr_value)) >= threshold:
                rows.append(
                    {
                        "factor_left": left_name,
                        "factor_right": right_name,
                        "correlation": float(corr_value),
                        "abs_correlation": float(abs(corr_value)),
                        "redundancy_hint": f"high_corr_{left_name}_{right_name}",
                    }
                )
    if not rows:
        return pd.DataFrame(columns=["factor_left", "factor_right", "correlation", "abs_correlation", "redundancy_hint"])
    return pd.DataFrame(rows).sort_values(["abs_correlation", "factor_left", "factor_right"], ascending=[False, True, True])


def build_factor_correlation_report(
    factor_panel: pd.DataFrame,
    *,
    threshold: float = 0.8,
    matrix_path: Path | None = None,
    pairs_path: Path | None = None,
    heatmap_path: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build and persist a factor correlation report."""
    correlation_matrix = calc_factor_correlation_matrix(factor_panel)
    high_corr_pairs = extract_high_correlation_pairs(correlation_matrix, threshold=threshold)

    matrix_target = matrix_path or (WAREHOUSE_DIR / "factor_correlation_matrix.csv")
    pairs_target = pairs_path or (WAREHOUSE_DIR / "high_correlation_pairs.csv")
    heatmap_target = heatmap_path or (REPORT_DIR / "factor_research" / "factor_correlation_heatmap.png")

    matrix_target.parent.mkdir(parents=True, exist_ok=True)
    pairs_target.parent.mkdir(parents=True, exist_ok=True)
    correlation_matrix.to_csv(matrix_target, encoding="utf-8")
    high_corr_pairs.to_csv(pairs_target, index=False, encoding="utf-8")
    _save_heatmap(correlation_matrix, heatmap_target)
    return correlation_matrix, high_corr_pairs


def _save_heatmap(correlation_matrix: pd.DataFrame, path: Path) -> None:
    """Save a simple heatmap for the correlation matrix."""
    if correlation_matrix.empty:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 6))
    image = ax.imshow(correlation_matrix.fillna(0.0).values, cmap="coolwarm", vmin=-1.0, vmax=1.0)
    ax.set_xticks(range(len(correlation_matrix.columns)))
    ax.set_yticks(range(len(correlation_matrix.index)))
    ax.set_xticklabels(correlation_matrix.columns, rotation=45, ha="right")
    ax.set_yticklabels(correlation_matrix.index)
    ax.set_title("Factor Correlation Heatmap")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
