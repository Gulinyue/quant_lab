# Pipeline Orchestration v0.1

## Responsibility

The pipeline layer provides one reproducible research-to-report run. It does not replace the individual stage scripts. It only coordinates them, validates key outputs, snapshots configs, and collects artifacts by `run_id`.

## Core Concepts

### run_id

- readable local identifier
- format: `YYYYMMDD_HHMMSS_suffix`
- examples:
  - `20260328_213000_demo`
  - `20260328_213000_run001`

### artifact_dir

Each run writes into:

- `runs/<run_id>/`

Current structure:

- `runs/<run_id>/manifest.json`
- `runs/<run_id>/configs/`
- `runs/<run_id>/warehouse_snapshots/`
- `runs/<run_id>/figures/`
- `runs/<run_id>/tables/`
- `runs/<run_id>/html/`

### manifest

Current manifest records:

- `run_id`
- `started_at`
- `finished_at`
- `status`
- `artifact_root`
- `stage_statuses`
- `config_snapshot`
- `input_files`
- `output_files`
- `warnings`
- `errors`

## Stage Order

Current default stage order:

1. `build_factors`
2. `run_single_factor_analysis`
3. `run_factor_correlation`
4. `run_factor_screening`
5. `run_strategy`
6. `run_backtest`
7. `build_report`

## Critical vs Optional Stages

Critical:

- `build_factors`
- `run_factor_screening`
- `run_strategy`
- `run_backtest`
- `build_report`

Optional:

- `run_single_factor_analysis`
- `run_factor_correlation`

Reason:

- optional research stages should not block the main strategy-backtest-report chain in v0.1
- screening is treated as critical because strategy-layer constraints depend on it in the current implementation

## Failure Rules

- critical stage failure: stop pipeline immediately
- optional stage failure: record warning and continue
- missing required output after a stage counts as stage failure

## Stage Validation

Current validator checks:

- after `build_factors`: `factor_panel.parquet`
- after `run_factor_screening`: `factor_screening_summary.csv`
- after `run_strategy`: `target_positions.parquet`
- after `run_backtest`: `nav.parquet` and `performance_summary.csv`
- after `build_report`: `backtest_report.html`

## Config Snapshots

Each run copies the current configs into:

- `runs/<run_id>/configs/`

Files copied:

- `data.yaml`
- `factors.yaml`
- `strategy.yaml`
- `backtest.yaml`
- `report.yaml`

This is the minimal reproducibility layer for v0.1.

## Limits

- no parallel execution
- no distributed scheduler
- no retry queue
- no resumable partial run recovery
- still relies on default warehouse/report outputs before collecting snapshots

## TODO

- stage-level retry policy
- resume from a failed intermediate stage
- richer manifest CSV export
- compare two run manifests side by side
