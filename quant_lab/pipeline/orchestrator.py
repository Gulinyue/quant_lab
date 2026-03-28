"""End-to-end experiment orchestration."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from quant_lab.common.paths import CONFIG_DIR, FIGURE_DIR, HTML_DIR, TABLE_DIR, WAREHOUSE_DIR
from quant_lab.pipeline.manifest import save_manifest
from quant_lab.pipeline.run_context import RunContext
from quant_lab.pipeline.stage_runner import run_stage
from quant_lab.settings import AppSettings


def run_pipeline(
    *,
    run_id: str | None = None,
    skip_single_factor: bool = False,
    skip_correlation: bool = False,
    skip_report: bool = False,
) -> RunContext:
    """Run the minimal research-to-report pipeline."""
    from scripts.build_factors import run as build_factors_run
    from scripts.build_report import run as build_report_run
    from scripts.run_backtest import run as run_backtest_run
    from scripts.run_factor_correlation import run as run_factor_correlation_run
    from scripts.run_factor_screening import run as run_factor_screening_run
    from scripts.run_strategy import run as run_strategy_run

    context = RunContext.create(run_id=run_id)
    settings = AppSettings.load()
    config_snapshot = _snapshot_configs(context)

    stage_definitions: list[tuple[str, bool, Any]] = [
        ("build_factors", True, lambda: _invoke_script_stage(build_factors_run, "build_factors")),
        ("run_single_factor_analysis", False, _run_single_factor_batch),
        ("run_factor_correlation", False, (lambda: _invoke_script_stage(run_factor_correlation_run, "run_factor_correlation")) if not skip_correlation else lambda: None),
        ("run_factor_screening", True, lambda: _invoke_script_stage(run_factor_screening_run, "run_factor_screening")),
        ("run_strategy", True, lambda: _invoke_script_stage(run_strategy_run, "run_strategy")),
        ("run_backtest", True, lambda: _invoke_script_stage(run_backtest_run, "run_backtest")),
        ("build_report", True, (lambda: _invoke_script_stage(build_report_run, "build_report")) if not skip_report else lambda: None),
    ]

    for stage_name, critical, stage_func in stage_definitions:
        if (stage_name == "run_single_factor_analysis" and skip_single_factor) or (stage_name == "run_factor_correlation" and skip_correlation) or (stage_name == "build_report" and skip_report):
            context.stage_statuses[stage_name] = "skipped"
            context.warnings.append(f"{stage_name} skipped by flag")
            continue
        success = run_stage(context, stage_name, stage_func, critical=critical)
        if not success and critical:
            context.mark_finished("failed")
            manifest_path = save_manifest(context, _build_manifest_snapshot(settings, context))
            context.output_files.append(str(manifest_path))
            return context

    _collect_run_artifacts(context)
    _append_short_sample_warning(context)
    context.mark_finished("success")
    manifest_path = save_manifest(context, _build_manifest_snapshot(settings, context, config_snapshot))
    context.output_files.append(str(manifest_path))
    return context


def _run_single_factor_batch() -> None:
    """Run single-factor research for all currently built factor columns."""
    from quant_lab.analysis_layer.factor_research import run_single_factor_research_pipeline

    factor_panel = pd.read_parquet(WAREHOUSE_DIR / "factor_panel.parquet")
    for factor_name in factor_panel.columns:
        run_single_factor_research_pipeline(factor_name=factor_name)


def _invoke_script_stage(run_func, script_name: str) -> None:
    """Invoke an imported script run() with isolated argv."""
    old_argv = sys.argv[:]
    try:
        sys.argv = [script_name]
        run_func()
    finally:
        sys.argv = old_argv


def _snapshot_configs(context: RunContext) -> dict[str, str]:
    """Copy config files into run directory."""
    config_dir = context.artifact_root / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    snapshot_paths: dict[str, str] = {}
    for name in ["data.yaml", "factors.yaml", "strategy.yaml", "backtest.yaml", "report.yaml"]:
        src = CONFIG_DIR / name
        dst = config_dir / name
        shutil.copy2(src, dst)
        snapshot_paths[name] = str(dst)
    context.config_snapshot = snapshot_paths
    return snapshot_paths


def _collect_run_artifacts(context: RunContext) -> None:
    """Collect key warehouse/report outputs into isolated run directory."""
    warehouse_target = context.artifact_root / "warehouse_snapshots"
    figures_target = context.artifact_root / "figures"
    tables_target = context.artifact_root / "tables"
    html_target = context.artifact_root / "html"
    warehouse_target.mkdir(parents=True, exist_ok=True)
    figures_target.mkdir(parents=True, exist_ok=True)
    tables_target.mkdir(parents=True, exist_ok=True)
    html_target.mkdir(parents=True, exist_ok=True)

    warehouse_files = [
        "factor_research_summary.csv",
        "factor_screening_summary.csv",
        "strategy_diagnostics.csv",
        "nav.parquet",
        "trades.parquet",
        "daily_positions.parquet",
        "performance_summary.csv",
    ]
    for name in warehouse_files:
        src = WAREHOUSE_DIR / name
        if src.exists():
            dst = warehouse_target / name
            shutil.copy2(src, dst)
            context.output_files.append(str(dst))
            context.input_files.append(str(src))

    for src in FIGURE_DIR.glob("*.png"):
        dst = figures_target / src.name
        shutil.copy2(src, dst)
        context.output_files.append(str(dst))
    for src in TABLE_DIR.glob("*.csv"):
        dst = tables_target / src.name
        shutil.copy2(src, dst)
        context.output_files.append(str(dst))

    html_file = HTML_DIR / "backtest_report.html"
    if html_file.exists():
        dst = html_target / html_file.name
        shutil.copy2(html_file, dst)
        context.output_files.append(str(dst))


def _append_short_sample_warning(context: RunContext) -> None:
    """Record short-sample flag into warnings if present."""
    summary_path = WAREHOUSE_DIR / "performance_summary.csv"
    if not summary_path.exists():
        return
    summary = pd.read_csv(summary_path)
    if summary.empty:
        return
    row = summary.iloc[0]
    if str(row.get("message", "")) == "short_sample" or int(row.get("trading_days", 0) or 0) < 20:
        context.warnings.append("short_sample")


def _build_manifest_snapshot(settings: AppSettings, context: RunContext, config_snapshot: dict[str, str] | None = None) -> dict[str, Any]:
    """Build config-focused manifest summary."""
    strategy_cfg = settings.strategy
    backtest_cfg = settings.backtest
    report_cfg = settings.report
    return {
        "run_id": context.run_id,
        "time_range": _extract_time_range(),
        "enabled_factors": _extract_enabled_factors(settings.factors),
        "strategy_name": strategy_cfg.get("strategy", {}).get("name", strategy_cfg.get("strategy_name", "ranking_v1")),
        "backtest_execution_mode": backtest_cfg.get("execution", {}).get("price", "next_open"),
        "report_output_path": report_cfg.get("report", {}).get("output_html", "reports/html/backtest_report.html"),
        "config_snapshot": config_snapshot or context.config_snapshot,
    }


def _extract_enabled_factors(factor_config: dict[str, Any]) -> list[str]:
    """Extract enabled factors from factor config."""
    factors = factor_config.get("factors", [])
    return [item["name"] for item in factors if item.get("enabled", True)] if factors else factor_config.get("factor_names", [])


def _extract_time_range() -> dict[str, str]:
    """Extract sample range from nav output if present."""
    nav_path = WAREHOUSE_DIR / "nav.parquet"
    if not nav_path.exists():
        return {"start": "", "end": ""}
    nav = pd.read_parquet(nav_path)
    if "trade_date" in nav.columns:
        nav = nav.set_index("trade_date")
    if nav.empty:
        return {"start": "", "end": ""}
    return {"start": str(pd.to_datetime(nav.index.min()).date()), "end": str(pd.to_datetime(nav.index.max()).date())}
