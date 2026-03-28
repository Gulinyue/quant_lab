# Strategy Layer v0.1

## Responsibility

The strategy layer converts researched factors into standardized target holdings. It does not run backtests, optimize a risk model, or connect to live trading.

## Current RankingStrategy Logic

Current strategy is a minimal long-only ranking strategy:

1. load configured factors from `config/strategy.yaml`
2. apply factor whitelist and blacklist
3. filter factors by metadata status
4. filter factors by screening recommendation
5. build a linear composite score
6. select top `N` assets on rebalance dates
7. output equal-weight target holdings

## Score Construction

Current score is:

- weighted linear sum of selected factor columns

Optional score transform:

- `none`
- `rank`
- `zscore`

The transform is applied cross-sectionally by `trade_date` inside the strategy layer.

## Factor Admission Priority

Current priority order is:

1. `strategy.yaml` explicit selected list and blacklist
2. factor metadata status
3. factor screening recommendation
4. actual presence in `factor_panel`

Meaning:

- `deprecated` and `archived` factors are blocked by default
- `testing` factors require `allow_testing_factors: true`
- `review` recommendations require `allow_review_factors: true`
- `deprecate_candidate` factors are blocked by default

## Standard Inputs

- `data/warehouse/factor_panel.parquet`
- `data/warehouse/factor_metadata.csv`
- `data/warehouse/factor_screening_summary.csv` if available
- `config/strategy.yaml`

## Standard Outputs

### target_positions.parquet

Index:

- `MultiIndex([trade_date, asset])`

Columns:

- `score`
- `target_weight`
- `rank`
- `signal`
- `selected_by_strategy`
- `factor_count_used`

### strategy_diagnostics.csv

Current fields:

- `trade_date`
- `factor_name`
- `factor_used`
- `factor_drop_reason`
- `candidate_count`
- `selected_count`
- `active_factor_count`
- `dropped_factor_count`
- `weighting_method`
- `rebalance_flag`
- `score_non_null_ratio`
- `score_std`
- `message`

## Limits

- only long-only
- only equal-weight
- only explicit factor mode
- no industry neutrality
- no turnover control
- no transaction cost model
- no optimizer

## TODO

- weekly rebalance validation on longer samples
- richer weighting methods
- explicit cash handling when `max_weight_per_asset` is binding
- strategy-level risk filters
- position carry and drift policies
