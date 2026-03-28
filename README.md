# Quant Lab v0.1

Quant Lab is a Windows-first A-share low-frequency research framework. The six-layer architecture remains unchanged. The factor layer now supports single-factor registration, config-driven builds, preprocessing, and diagnostics output.

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

## Factor Layer Overview

The factor layer currently supports these factors:

- `mom_20`
- `rev_5`
- `vol_20`
- `turnover_20`
- `price_volume_corr_20`
- `bp`
- `ep`
- `size`

Each factor is registered independently with metadata:

- factor name
- group
- description
- required columns
- direction
- minimum history window

## Registry Design

The factor registry is single-factor based.

- each factor is one registered function
- each factor has unique metadata
- the builder fetches factors by name
- config can enable or disable factors independently

## Factor Config

`config/factors.yaml` controls:

- which factors are enabled
- whether winsorization is enabled
- winsorize lower and upper quantiles
- whether z-score normalization is enabled

Example run:

```powershell
D:\anaconda\envs\alpha_lab\python.exe scripts\build_factors.py
```

## Preprocess Behavior

The factor layer preprocess currently supports:

- cross-sectional winsorization by `trade_date`
- cross-sectional z-score by `trade_date`
- rank transform helper by `trade_date`

The implementation is compatible with:

- all-null slices
- constant slices
- small samples

## Factor Build Outputs

`scripts/build_factors.py` now writes:

- `data/warehouse/factor_panel.parquet`
- `data/warehouse/factor_diagnostics.csv`

`factor_diagnostics.csv` is used to inspect:

- factor name
- factor group
- required columns
- direction
- min history
- row count
- non-null ratio
- finite ratio
- missing ratio
- build status
- failure message if any

## Script Flow

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
- stronger factor-direction and portfolio-mapping controls
