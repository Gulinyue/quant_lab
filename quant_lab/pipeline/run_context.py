"""Run-context definitions for experiment orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from quant_lab.common.paths import RUNS_DIR


def generate_run_id(label: str | None = None) -> str:
    """Generate a readable run id suitable for local file paths."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = (label or "run").strip().replace(" ", "_")
    suffix = "".join(ch for ch in suffix if ch.isalnum() or ch in {"_", "-"}).strip("_") or "run"
    return f"{timestamp}_{suffix}"


@dataclass(slots=True)
class RunContext:
    """Mutable context for one end-to-end pipeline run."""

    run_id: str
    started_at: str
    artifact_root: Path
    status: str = "running"
    finished_at: str | None = None
    stage_statuses: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    input_files: list[str] = field(default_factory=list)
    output_files: list[str] = field(default_factory=list)
    config_snapshot: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(cls, run_id: str | None = None) -> "RunContext":
        """Create a new run context and artifact root."""
        resolved_run_id = run_id or generate_run_id()
        artifact_root = RUNS_DIR / resolved_run_id
        artifact_root.mkdir(parents=True, exist_ok=True)
        return cls(
            run_id=resolved_run_id,
            started_at=datetime.now().isoformat(timespec="seconds"),
            artifact_root=artifact_root,
        )

    def mark_finished(self, status: str) -> None:
        """Mark the run as finished."""
        self.status = status
        self.finished_at = datetime.now().isoformat(timespec="seconds")
