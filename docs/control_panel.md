# Control Panel

## Responsibility

The Streamlit control panel is the local experiment console for `quant_lab`.

Its job is to:

- load baseline YAML configs
- let the user override runtime parameters in the UI
- validate manual stock-pool input before runtime
- extend local data coverage for uncovered assets
- provide a minimal custom-factor experiment entry
- trigger existing factor / analysis / strategy / backtest / report logic
- show logs, artifact status, and key result summaries

It is not intended to replace the existing six-layer architecture.

## Relationship To Config Files

Current behavior:

- the panel reads baseline config from:
  - `config/data.yaml`
  - `config/factors.yaml`
  - `config/strategy.yaml`
  - `config/backtest.yaml`
  - `config/report.yaml`
- the user edits only the in-memory runtime config in the panel
- clicking a run button creates a runtime config snapshot
- that snapshot is written to `runs/<run_id>/configs/`

By default, the panel does not overwrite repo YAML files.

## Stock-Pool Filtering

The panel currently supports these stock-pool modes:

- all available assets
- manual asset list
- multi-select from available assets
- index constituent placeholder

Current implementation boundary:

- stock-pool filtering is applied after `market_panel` / `factor_panel` already exist
- this round does not change raw data download scope
- the whitelist affects:
  - factor build
  - single-factor research
  - factor screening inputs
  - strategy
  - backtest
  - report outputs through filtered warehouse artifacts

The panel now separates manual input into:

- valid asset codes already covered by current data
- invalid-format asset codes
- valid-format asset codes not yet covered by current data

If invalid or uncovered asset codes exist, stock-pool dependent run buttons are disabled.

## Universe Extension

If a manually entered asset code is valid but not covered by the current panel, the user can click:

- `加入 universe 并刷新数据`

Current behavior:

1. append the asset code into `config/data.yaml`
2. run raw-data update
3. rebuild `market_panel`

This is a minimal data-coverage extension path. It does not change the broader data architecture.

## Buttons And Stage Mapping

Current buttons map to these actions:

- `加入 universe 并刷新数据`
  - updates `config/data.yaml`
  - refreshes raw data
  - rebuilds `market_panel`
- `构建因子`
  - filters `market_panel`
  - runs factor build
  - writes `factor_panel.parquet`, diagnostics, and metadata
- `运行单因子研究`
  - filters market and factor panels
  - runs single-factor research
  - writes `factor_research_summary.csv`
- `运行因子筛选`
  - builds correlation outputs and screening summary
- `运行策略`
  - filters `factor_panel`
  - applies metadata and screening constraints
  - writes `target_positions.parquet` and `strategy_diagnostics.csv`
- `运行回测`
  - filters market and target positions
  - writes `daily_positions.parquet`, `trades.parquet`, `nav.parquet`, and `performance_summary.csv`
- `生成报告`
  - builds figures, tables, and HTML from current warehouse artifacts
- `全流程运行`
  - factor build -> research -> screening -> strategy -> backtest -> report

## Custom Factor Experiment

The panel includes a minimal custom-factor experiment entry.

Current modes:

- expression
- uploaded CSV

Expression mode evaluates against the current filtered `market_panel`.

Available helpers:

- `shift(series, n)`
- `pct_change(series, n)`
- `rolling_mean(series, window)`
- `rolling_std(series, window)`
- `rolling_corr(left, right, window)`
- `cs_rank(series)`
- `log(...)`
- `abs(...)`

Uploaded CSV mode expects:

- `trade_date`
- `asset`
- one factor value column

Current output path:

- `reports/factor_research/custom/<factor_name>/`
- `data/warehouse/custom_factor_research_summary.csv`

## Log And Result Areas

The panel shows:

- current runtime status
- detailed run logs
- current runtime config preview
- artifact existence checks
- performance summary table
- latest positions preview
- custom-factor research summary
- report path
- run artifact directory
- NAV figure preview when available

## Launch

```powershell
D:\anaconda\envs\alpha_lab\python.exe -m streamlit run app.py
```

## Current Limits And TODO

- index constituent mode is still a placeholder
- runtime config is not yet persisted back to YAML by default
- no multi-run comparison inside the panel yet
- no advanced report embedding inside the panel yet
- no direct raw data stock-pool download narrowing yet
- custom factors are not automatically registered into the main factor registry
