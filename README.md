# Quant Lab v0.1

Quant Lab is a Windows-first A-share low-frequency research framework. The six-layer architecture remains unchanged. The factor layer now works as a minimal factor research and management system: single-factor registration, config-driven build, diagnostics output, lifecycle status, and metadata export.

## Default Startup

```powershell
D:\anaconda\envs\alpha_lab\python.exe -m streamlit run app.py
```

## Fixed Interpreter

All default commands use:

```powershell
D:\anaconda\envs\alpha_lab\python.exe
```

Check the actual interpreter:

```powershell
D:\anaconda\envs\alpha_lab\python.exe -c "import sys; print(sys.executable); print(sys.version)"
```

## Factor Layer Now Does

- single-factor registration
- metadata management
- lifecycle status management
- config-driven enable/disable
- cross-sectional preprocess
- diagnostics export
- metadata export

Supported factors:

- `mom_20`
- `rev_5`
- `vol_20`
- `turnover_20`
- `price_volume_corr_20`
- `bp`
- `ep`
- `size`

## How Factors Are Registered

Each factor is:

1. one standalone function in `technical.py` or `fundamental.py`
2. registered with metadata through the decorator
3. managed by the single-factor registry

Metadata now includes:

- `name`
- `group`
- `description`
- `required_columns`
- `direction`
- `min_history`
- `status`
- `version`
- `category`
- `tags`

## Lifecycle Status

Supported lifecycle states:

- `draft`
- `testing`
- `active`
- `deprecated`

Rules:

- active factors are normal production candidates
- testing factors can be enabled for research
- deprecated factors should normally stay disabled
- if a deprecated factor is enabled in config, build logs a warning instead of crashing

## How To Add a Factor

1. Add a new standalone factor function to `technical.py` or `fundamental.py`
2. Register it with full metadata using `@register_factor(...)`
3. Add it to `config/factors.yaml`
4. Run:

```powershell
D:\anaconda\envs\alpha_lab\python.exe scripts\build_factors.py
```

5. Inspect:

- `data/warehouse/factor_panel.parquet`
- `data/warehouse/factor_diagnostics.csv`
- `data/warehouse/factor_metadata.csv`

## How To Disable a Factor

Preferred approach:

- keep the code
- set `enabled: false` in `config/factors.yaml`

Do not delete factor code by default. Logical disable is preferred over physical removal.

## How Deprecated Factors Are Handled

- deprecated factors can remain registered
- they should usually be disabled in `config/factors.yaml`
- if manually enabled, `build_factors.py` emits a warning
- diagnostics and metadata outputs still record them

## Preprocess

The factor layer preprocess supports:

- winsorize by `trade_date`
- z-score by `trade_date`
- rank by `trade_date`

Config is read from `config/factors.yaml`.

## Factor Build Outputs

Run:

```powershell
D:\anaconda\envs\alpha_lab\python.exe scripts\build_factors.py
```

Outputs:

- `data/warehouse/factor_panel.parquet`
- `data/warehouse/factor_diagnostics.csv`
- `data/warehouse/factor_metadata.csv`

`factor_diagnostics.csv` is for build quality:

- missing ratio
- finite ratio
- dependency summary
- status
- failure message

`factor_metadata.csv` is for lifecycle and management:

- factor name
- group
- category
- status
- version
- direction
- required columns
- min history
- whether it is enabled in config

## Full Script Flow

```powershell
D:\anaconda\envs\alpha_lab\python.exe scripts\update_data.py
D:\anaconda\envs\alpha_lab\python.exe scripts\build_market_panel.py
D:\anaconda\envs\alpha_lab\python.exe scripts\build_factors.py
D:\anaconda\envs\alpha_lab\python.exe scripts\run_strategy.py
D:\anaconda\envs\alpha_lab\python.exe scripts\run_backtest.py
D:\anaconda\envs\alpha_lab\python.exe scripts\run_analysis.py
D:\anaconda\envs\alpha_lab\python.exe scripts\build_report.py
```

## Current TODO

- more complex fundamental factors
- industry and size neutralization
- stronger direction-to-portfolio mapping
- factor correlation analysis
- factor selection and elimination workflow
- factor version comparison tooling
