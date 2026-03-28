# Quant Lab v0.1

Quant Lab is a Windows-first A-share low-frequency research framework. The six-layer architecture remains unchanged in this repository. This round only hardens the data layer so raw updates are incremental, AkShare is a real daily fallback, and `market_panel` enforces a trustworthy canonical schema.

## Default Startup

The default local UI entry point remains:

```powershell
D:\anaconda\envs\alpha_lab\python.exe -m streamlit run app.py
```

## Fixed Interpreter

All default commands in this repository use:

```powershell
D:\anaconda\envs\alpha_lab\python.exe
```

To verify the actual interpreter:

```powershell
D:\anaconda\envs\alpha_lab\python.exe -c "import sys; print(sys.executable); print(sys.version)"
```

## Install

```powershell
D:\anaconda\envs\alpha_lab\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

`.env` example:

```env
TUSHARE_TOKEN=your_tushare_token_here
```

## Raw Layer vs Canonical Layer

Raw layer keeps source-native fields when practical:

- TuShare raw files may use `ts_code`, `trade_date`, `vol`
- AkShare daily fallback is also normalized only to the raw daily schema, not to the full canonical schema

Canonical layer means `market_panel`:

- index: `trade_date`, `asset`
- `trade_date` is `datetime64[ns]`
- `asset` is the internal string key
- `volume` is used instead of raw `vol`

## Data Update Logic

Run the data-layer entry point:

```powershell
D:\anaconda\envs\alpha_lab\python.exe scripts\update_data.py
```

Optional arguments:

```powershell
D:\anaconda\envs\alpha_lab\python.exe scripts\update_data.py --start 2024-01-01 --end 2024-03-31
D:\anaconda\envs\alpha_lab\python.exe scripts\update_data.py --force-full
```

### What updates incrementally

These raw tables now use real incremental merge logic:

- `data/raw/tushare/daily.parquet`
- `data/raw/tushare/adj_factor.parquet`
- `data/raw/tushare/daily_basic.parquet`

Incremental rule:

1. If local parquet exists, read it and find the max `trade_date`
2. Use refreshed `trade_cal` to find the next open day
3. Pull only missing open dates up to `end_date`
4. Merge old and new data
5. Deduplicate by `ts_code + trade_date`
6. Sort by `trade_date, ts_code`
7. Persist again

Each incremental update logs:

- `old_rows`
- `new_rows`
- `merged_rows`
- `dedup_removed_rows`
- `final_rows`
- final date range

### What still refreshes in full

- `trade_cal`
- `stock_basic`

Reason:

- they are small reference tables
- `trade_cal` is the driver for per-trade-date incremental pulls
- full refresh is simpler and low risk here

## AkShare Fallback Scope

AkShare is currently used only as a real `daily` fallback at symbol level.

What is implemented:

- real A-share daily fetch
- explicit column mapping
- returned raw schema includes `ts_code`, `trade_date`, `open`, `high`, `low`, `close`, `vol`, `amount`
- column assertions on AkShare response

What is not implemented yet:

- AkShare `adj_factor`
- AkShare `daily_basic`
- full-market automatic AkShare supplementation

So the current fallback strategy is:

- TuShare remains primary
- AkShare is daily-only fallback/supplement

## market_panel Missing-Value Policy

Build command:

```powershell
D:\anaconda\envs\alpha_lab\python.exe scripts\build_market_panel.py
```

Required canonical columns:

- `open`
- `high`
- `low`
- `close`
- `volume`
- `amount`
- `adj_factor`

If any required column is missing, build stops with a clear error.

Derived column:

- `close_adj = close * adj_factor`

Optional columns:

- `turnover_rate`
- `pe`
- `pb`
- `total_mv`

If optional columns are missing:

- they are added as `NaN`
- a warning is logged
- no silent `0.0` fill is allowed

## market_panel Validator

The market-panel builder validates:

1. index names are `trade_date, asset`
2. index is unique
3. `trade_date` is `datetime64[ns]`
4. `asset` is string-like
5. required columns are complete
6. index is sorted
7. optional-column missing ratios
8. duplicate-key count

## Full Script Flow

Advanced script-style flow remains compatible:

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

- AkShare does not provide `adj_factor` in this project yet
- AkShare does not provide `daily_basic` in this project yet
- fallback still focuses on `daily`
- no automatic full-market gap-repair loop using AkShare yet
