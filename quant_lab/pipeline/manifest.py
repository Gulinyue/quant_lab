"""Manifest builders for pipeline runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from quant_lab.pipeline.run_context import RunContext


def build_manifest(context: RunContext, config_snapshot: dict[str, Any]) -> dict[str, Any]:
    """Build manifest payload from run context."""
    short_sample = _extract_short_sample_flag_from_context(context)
    return {
        "run_id": context.run_id,
        "started_at": context.started_at,
        "finished_at": context.finished_at,
        "status": context.status,
        "artifact_root": str(context.artifact_root),
        "stage_statuses": context.stage_statuses,
        "config_snapshot": config_snapshot,
        "input_files": context.input_files,
        "output_files": context.output_files,
        "warnings": context.warnings,
        "errors": context.errors,
        "short_sample": short_sample,
    }


def save_manifest(context: RunContext, config_snapshot: dict[str, Any]) -> Path:
    """Persist manifest.json and update runs index."""
    manifest = build_manifest(context, config_snapshot)
    manifest_path = context.artifact_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    _update_run_index(manifest)
    return manifest_path


def _update_run_index(manifest: dict[str, Any]) -> None:
    """Append or replace one row in runs/index.csv."""
    index_path = Path(manifest["artifact_root"]).parents[0] / "index.csv"
    row = {
        "run_id": manifest["run_id"],
        "started_at": manifest["started_at"],
        "finished_at": manifest["finished_at"],
        "status": manifest["status"],
        "artifact_root": manifest["artifact_root"],
        "short_sample": bool(manifest.get("short_sample", False)),
    }
    incoming = pd.DataFrame([row])
    if index_path.exists():
        existing = pd.read_csv(index_path)
        existing = existing[existing["run_id"] != manifest["run_id"]]
        merged = pd.concat([existing, incoming], ignore_index=True)
    else:
        merged = incoming
    merged.to_csv(index_path, index=False, encoding="utf-8")


def _extract_short_sample_flag_from_context(context: RunContext) -> bool:
    """Infer short sample flag from run warnings."""
    for warning in context.warnings:
        if "short_sample" in warning:
            return True
    return False
