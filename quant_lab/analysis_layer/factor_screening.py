"""Factor screening helpers for research-stage keep/review decisions."""

from __future__ import annotations

import pandas as pd


def screen_factor_quality(
    diagnostics: pd.DataFrame,
    *,
    missing_ratio_threshold: float = 0.6,
    finite_ratio_threshold: float = 0.8,
) -> pd.DataFrame:
    """Screen basic factor data quality from diagnostics output."""
    records: list[dict[str, object]] = []
    for _, row in diagnostics.iterrows():
        reasons: list[str] = []
        if float(row.get("missing_ratio", 1.0)) > missing_ratio_threshold:
            reasons.append("missing_ratio_too_high")
        if float(row.get("finite_ratio", 0.0)) < finite_ratio_threshold:
            reasons.append("finite_ratio_too_low")
        quality_status = "bad" if reasons else "ok"
        records.append(
            {
                "factor_name": row["factor_name"],
                "quality_status": quality_status,
                "quality_reasons": ";".join(reasons),
            }
        )
    return pd.DataFrame(records)


def screen_factor_predictiveness(
    research_summary: pd.DataFrame,
    *,
    min_valid_dates: int = 20,
    weak_rank_ic_threshold: float = 0.02,
) -> pd.DataFrame:
    """Screen predictive strength from single-factor research summary."""
    records: list[dict[str, object]] = []
    for _, row in research_summary.iterrows():
        reasons: list[str] = []
        valid_dates = int(row.get("valid_rank_ic_dates", 0) or 0)
        rank_ic_mean = row.get("rank_ic_mean")
        if valid_dates < min_valid_dates:
            reasons.append("insufficient_history")
        if pd.isna(rank_ic_mean) or abs(float(rank_ic_mean)) < weak_rank_ic_threshold:
            reasons.append("weak_rank_ic")
        predictiveness_status = "weak" if reasons else "ok"
        records.append(
            {
                "factor_name": row["factor_name"],
                "predictiveness_status": predictiveness_status,
                "predictiveness_reasons": ";".join(reasons),
            }
        )
    return pd.DataFrame(records)


def screen_factor_redundancy(
    high_corr_pairs: pd.DataFrame,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    """Screen redundancy based on high-correlation factor pairs."""
    active_factors = set(metadata.loc[metadata["status"] == "active", "name"]) if not metadata.empty else set()
    factor_names = set(metadata["name"]) if not metadata.empty else set()
    reasons_map: dict[str, list[str]] = {name: [] for name in factor_names}

    for _, row in high_corr_pairs.iterrows():
        left = row["factor_left"]
        right = row["factor_right"]
        if left not in reasons_map:
            reasons_map[left] = []
        if right not in reasons_map:
            reasons_map[right] = []
        if right in active_factors:
            reasons_map[left].append(f"high_corr_with_{right}")
        if left in active_factors:
            reasons_map[right].append(f"high_corr_with_{left}")
        if right not in active_factors and left not in active_factors:
            reasons_map[left].append(f"high_corr_with_{right}")
            reasons_map[right].append(f"high_corr_with_{left}")

    records = []
    for factor_name in sorted(reasons_map):
        reasons = sorted(set(reasons_map[factor_name]))
        redundancy_status = "redundant" if reasons else "ok"
        records.append(
            {
                "factor_name": factor_name,
                "redundancy_status": redundancy_status,
                "redundancy_reasons": ";".join(reasons),
            }
        )
    return pd.DataFrame(records)


def build_factor_screening_summary(
    diagnostics: pd.DataFrame,
    research_summary: pd.DataFrame,
    high_corr_pairs: pd.DataFrame,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    """Build final factor screening recommendation table."""
    quality = screen_factor_quality(diagnostics)
    predictiveness = screen_factor_predictiveness(research_summary)
    redundancy = screen_factor_redundancy(high_corr_pairs, metadata)

    summary = metadata[["name", "status"]].rename(columns={"name": "factor_name"}).copy()
    summary = summary.merge(quality, on="factor_name", how="left")
    summary = summary.merge(predictiveness, on="factor_name", how="left")
    summary = summary.merge(redundancy, on="factor_name", how="left")
    summary["quality_status"] = summary["quality_status"].fillna("not_built")
    summary["predictiveness_status"] = summary["predictiveness_status"].fillna("not_researched")
    summary["redundancy_status"] = summary["redundancy_status"].fillna("ok")
    summary["quality_reasons"] = summary["quality_reasons"].fillna("")
    summary["predictiveness_reasons"] = summary["predictiveness_reasons"].fillna("")
    summary["redundancy_reasons"] = summary["redundancy_reasons"].fillna("")

    recommendations: list[str] = []
    reasons_column: list[str] = []
    for _, row in summary.iterrows():
        raw_reasons = [row.get("quality_reasons", ""), row.get("predictiveness_reasons", ""), row.get("redundancy_reasons", "")]
        reasons = [str(reason) for reason in raw_reasons if pd.notna(reason) and str(reason)]
        flat_reasons = ";".join(reason for chunk in reasons for reason in chunk.split(";") if reason)
        if row.get("status") == "deprecated":
            recommendation = "deprecate_candidate"
        elif row.get("quality_status") == "bad":
            recommendation = "deprecate_candidate"
        elif row.get("predictiveness_status") == "weak" or row.get("redundancy_status") == "redundant":
            recommendation = "review"
        else:
            recommendation = "keep"
        recommendations.append(recommendation)
        reasons_column.append(flat_reasons)

    summary["recommendation"] = recommendations
    summary["reasons"] = reasons_column
    return summary[
        [
            "factor_name",
            "quality_status",
            "predictiveness_status",
            "redundancy_status",
            "recommendation",
            "reasons",
        ]
    ].sort_values("factor_name")
