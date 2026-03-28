"""Stage validators for minimal pipeline orchestration."""

from __future__ import annotations

from pathlib import Path

from quant_lab.common.paths import HTML_DIR, WAREHOUSE_DIR


def validate_stage_output(stage_name: str) -> tuple[bool, str]:
    """Validate required output existence for one stage."""
    checks: dict[str, list[Path]] = {
        "build_factors": [WAREHOUSE_DIR / "factor_panel.parquet"],
        "run_factor_screening": [WAREHOUSE_DIR / "factor_screening_summary.csv"],
        "run_strategy": [WAREHOUSE_DIR / "target_positions.parquet"],
        "run_backtest": [WAREHOUSE_DIR / "nav.parquet", WAREHOUSE_DIR / "performance_summary.csv"],
        "build_report": [HTML_DIR / "backtest_report.html"],
    }
    required_paths = checks.get(stage_name, [])
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        return False, f"Missing required outputs for {stage_name}: {missing}"
    return True, ""
