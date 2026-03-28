"""Validation helpers for report-layer inputs."""

from __future__ import annotations

from pathlib import Path


def require_files(paths: list[Path]) -> None:
    """Raise if any required report-layer inputs are missing."""
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required report-layer inputs: {missing}")
