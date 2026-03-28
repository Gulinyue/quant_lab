"""Factor selection rules for strategy-layer inputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(slots=True)
class FactorSelectionResult:
    """Selected and dropped factor names with reasons."""

    selected_factors: list[str]
    dropped_factors: dict[str, str]
    weights: dict[str, float]


def load_strategy_config(strategy_config: dict[str, Any]) -> dict[str, Any]:
    """Load and normalize strategy configuration with backward compatibility."""
    strategy_section = strategy_config.get("strategy", {})
    factor_section = strategy_config.get("factors", {})
    constraint_section = strategy_config.get("constraints", {})

    if "top_n" not in strategy_section and "top_n" in strategy_config:
        strategy_section["top_n"] = strategy_config.get("top_n")
    if "rebalance" not in strategy_section and "rebalance_every" in strategy_config:
        strategy_section["rebalance"] = "weekly" if int(strategy_config.get("rebalance_every", 1)) > 1 else "daily"
    if "weighting" not in strategy_section:
        strategy_section["weighting"] = "equal"

    if "weights" not in factor_section and "factor_weights" in strategy_config:
        factor_weights = strategy_config.get("factor_weights", {})
        factor_section["selected"] = list(factor_weights.keys())
        factor_section["weights"] = factor_weights
        factor_section["mode"] = "explicit"

    return {
        "strategy": {
            "name": strategy_section.get("name", strategy_config.get("strategy_name", "ranking_v1")),
            "enabled": bool(strategy_section.get("enabled", True)),
            "rebalance": str(strategy_section.get("rebalance", "daily")).lower(),
            "top_n": int(strategy_section.get("top_n", 30)),
            "weighting": str(strategy_section.get("weighting", "equal")).lower(),
            "allow_testing_factors": bool(strategy_section.get("allow_testing_factors", False)),
            "allow_review_factors": bool(strategy_section.get("allow_review_factors", False)),
        },
        "factors": {
            "mode": str(factor_section.get("mode", "explicit")).lower(),
            "selected": list(factor_section.get("selected", [])),
            "blacklist": list(factor_section.get("blacklist", [])),
            "weights": dict(factor_section.get("weights", {})),
            "score_transform": str(factor_section.get("score_transform", "none")).lower(),
        },
        "constraints": {
            "max_weight_per_asset": float(constraint_section.get("max_weight_per_asset", 1.0)),
            "min_selected_assets": int(constraint_section.get("min_selected_assets", 1)),
        },
    }


def select_eligible_factors(
    factor_panel: pd.DataFrame,
    metadata: pd.DataFrame,
    screening: pd.DataFrame | None,
    strategy_config: dict[str, Any],
) -> FactorSelectionResult:
    """Select final factors using explicit config, metadata status, screening, and panel availability."""
    factor_cfg = strategy_config["factors"]
    strategy_cfg = strategy_config["strategy"]

    selected = factor_cfg.get("selected", [])
    blacklist = set(factor_cfg.get("blacklist", []))
    weights = factor_cfg.get("weights", {})
    dropped: dict[str, str] = {}

    if factor_cfg.get("mode") != "explicit":
        raise ValueError("Only explicit factor selection mode is supported in v0.1.")
    if not selected:
        raise ValueError("strategy.yaml must define factors.selected in explicit mode.")

    metadata_map = metadata.set_index("name").to_dict(orient="index") if not metadata.empty else {}
    screening_map = screening.set_index("factor_name").to_dict(orient="index") if screening is not None and not screening.empty else {}

    final_selected: list[str] = []
    for factor_name in selected:
        if factor_name in blacklist:
            dropped[factor_name] = "blacklist"
            continue
        if factor_name not in weights:
            dropped[factor_name] = "missing_weight"
            continue
        meta = metadata_map.get(factor_name)
        if meta is None:
            dropped[factor_name] = "missing_metadata"
            continue
        status = str(meta.get("status", "testing"))
        if status == "deprecated":
            dropped[factor_name] = "metadata_deprecated"
            continue
        if status == "archived":
            dropped[factor_name] = "metadata_archived"
            continue
        if status == "testing" and not strategy_cfg.get("allow_testing_factors", False):
            dropped[factor_name] = "metadata_testing_blocked"
            continue

        screening_row = screening_map.get(factor_name)
        if screening_row is not None:
            recommendation = str(screening_row.get("recommendation", "keep"))
            if recommendation == "deprecate_candidate":
                dropped[factor_name] = "screening_deprecate_candidate"
                continue
            if recommendation == "review" and not strategy_cfg.get("allow_review_factors", False):
                dropped[factor_name] = "screening_review_blocked"
                continue

        if factor_name not in factor_panel.columns:
            dropped[factor_name] = "missing_in_factor_panel"
            continue
        final_selected.append(factor_name)

    selected_weights = {factor_name: float(weights[factor_name]) for factor_name in final_selected}
    return FactorSelectionResult(selected_factors=final_selected, dropped_factors=dropped, weights=selected_weights)
