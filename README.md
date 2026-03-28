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
- single-factor research
- factor correlation analysis
- factor screening recommendations
- strategy-layer target position generation
- backtest-layer execution and NAV generation

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

## Factor Research Scripts

Single-factor research:

```powershell
D:\anaconda\envs\alpha_lab\python.exe scripts\run_single_factor_analysis.py --factor mom_20
```

Factor correlation analysis:

```powershell
D:\anaconda\envs\alpha_lab\python.exe scripts\run_factor_correlation.py --threshold 0.8
```

Factor screening recommendation:

```powershell
D:\anaconda\envs\alpha_lab\python.exe scripts\run_factor_screening.py
```

## Research Output Files

Warehouse outputs:

- `data/warehouse/factor_research_summary.csv`
- `data/warehouse/factor_correlation_matrix.csv`
- `data/warehouse/high_correlation_pairs.csv`
- `data/warehouse/factor_screening_summary.csv`

Per-factor report outputs:

- `reports/factor_research/<factor_name>/rank_ic.csv`
- `reports/factor_research/<factor_name>/quantile_returns.csv`
- `reports/factor_research/<factor_name>/yearly_summary.csv`
- `reports/factor_research/<factor_name>/summary.json`
- `reports/factor_research/<factor_name>/rank_ic.png`
- `reports/factor_research/<factor_name>/quantile_returns.png`

## Research Definitions

Forward return:

- current default is `1D`
- definition: `close_adj(t+1) / close_adj(t) - 1`

RankIC:

- computed cross-sectionally by `trade_date`
- both factor and forward return are ranked first
- then rank correlation is computed

Quantile return:

- current default is `5` buckets
- each date splits the factor cross section into quantiles
- quantile return is the average forward return inside each bucket
- `long_short = top_quantile - bottom_quantile`

Factor correlation:

- current implementation computes cross-sectional Spearman correlation by date
- then averages those daily matrices across valid dates

Screening recommendation:

- `keep`
- `review`
- `deprecate_candidate`

These labels are research suggestions only. They are not automatic trading decisions.

## Strategy Layer Now Does

- reads `factor_panel.parquet`
- reads `factor_metadata.csv`
- optionally reads `factor_screening_summary.csv`
- filters factors by explicit config, metadata status, and screening recommendation
- builds a weighted composite score
- selects top `N` assets
- outputs standardized target positions
- outputs strategy diagnostics

## Strategy Config

Run:

```powershell
D:\anaconda\envs\alpha_lab\python.exe scripts\run_strategy.py
```

Main config file:

- `config/strategy.yaml`

Current priority order for factor admission:

1. explicit whitelist / blacklist in `strategy.yaml`
2. lifecycle status in `factor_metadata.csv`
3. recommendation in `factor_screening_summary.csv`
4. actual factor presence in `factor_panel.parquet`

Current metadata status rules:

- `active`: allowed
- `testing`: allowed only if `allow_testing_factors: true`
- `deprecated`: blocked by default
- `archived`: blocked by default if present

Current screening recommendation rules:

- `keep`: allowed
- `review`: allowed only if `allow_review_factors: true`
- `deprecate_candidate`: blocked by default

## Strategy Outputs

Warehouse outputs:

- `data/warehouse/target_positions.parquet`
- `data/warehouse/strategy_diagnostics.csv`

`target_positions.parquet` contains:

- `score`
- `target_weight`
- `rank`
- `signal`
- `selected_by_strategy`
- `factor_count_used`

`strategy_diagnostics.csv` contains:

- factor usage by date
- factor drop reasons
- candidate count
- selected count
- active factor count
- dropped factor count
- weighting method
- rebalance flag
- score non-null ratio
- score dispersion
- daily warning messages

## Backtest Layer Now Does

- reads `market_panel.parquet`
- reads `target_positions.parquet`
- shifts strategy targets to next-day execution
- simulates minimal long-only daily execution
- records `daily_positions`, `trades`, `nav`, and `performance_summary`

## Backtest Config

Run:

```powershell
D:\anaconda\envs\alpha_lab\python.exe scripts\run_backtest.py
```

Main config file:

- `config/backtest.yaml`

Current config sections:

- `execution`
- `cost`
- `portfolio`
- `constraints`

## target_positions vs daily_positions

`target_positions`:

- strategy intent
- desired weights
- not actual execution output

`daily_positions`:

- backtest result
- actual executed holdings after next-day execution
- contains `weight`, `shares`, `close`, and `market_value`

Do not use `target_positions` as a substitute for realized positions.

## Backtest Assumptions

Current assumptions:

- signal is known after `trade_date` close
- target weights execute on the next trading day
- execution price convention is currently `next_open`
- strategy is long-only
- non-rebalance days naturally carry positions forward
- no suspension modeling
- no limit-up/limit-down modeling
- no complex slippage model
- output is for structure validation and basic research, not realistic live tradability

## Backtest Outputs

Warehouse outputs:

- `data/warehouse/daily_positions.parquet`
- `data/warehouse/trades.parquet`
- `data/warehouse/nav.parquet`
- `data/warehouse/performance_summary.csv`

`nav.parquet` contains:

- `gross_ret`
- `turnover`
- `cost`
- `net_ret`
- `nav`

`performance_summary.csv` contains:

- `total_return`
- `annualized_return`
- `annualized_volatility`
- `sharpe`
- `max_drawdown`
- `avg_turnover`
- `win_rate`
- `trading_days`

## Full Script Flow

```powershell
D:\anaconda\envs\alpha_lab\python.exe scripts\update_data.py
D:\anaconda\envs\alpha_lab\python.exe scripts\build_market_panel.py
D:\anaconda\envs\alpha_lab\python.exe scripts\build_factors.py
D:\anaconda\envs\alpha_lab\python.exe scripts\run_single_factor_analysis.py --factor mom_20
D:\anaconda\envs\alpha_lab\python.exe scripts\run_factor_correlation.py
D:\anaconda\envs\alpha_lab\python.exe scripts\run_factor_screening.py
D:\anaconda\envs\alpha_lab\python.exe scripts\run_strategy.py
D:\anaconda\envs\alpha_lab\python.exe scripts\run_backtest.py
D:\anaconda\envs\alpha_lab\python.exe scripts\run_analysis.py
D:\anaconda\envs\alpha_lab\python.exe scripts\build_report.py
```

## Current TODO

- more complex fundamental factors
- industry and size neutralization
- stronger direction-to-portfolio mapping
- factor version comparison tooling
- richer factor redundancy clustering
- multi-horizon single-factor research
- more robust screening rules for short samples
- richer weighting methods beyond equal weight
- strategy-level risk controls and neutralization
- more realistic execution constraints and market frictions
- benchmark-relative performance and richer attribution
