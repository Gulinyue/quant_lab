# Factor Research v0.1

## Goal

The factor research layer is the minimal bridge from factor generation to factor evaluation. It does not optimize multi-factor weights. It only answers three questions:

1. Does a single factor show basic predictive signal?
2. Is a factor highly redundant versus other factors?
3. Should a factor be kept, reviewed, or considered for deprecation?

## Single-Factor Research Scope

Current outputs:

- RankIC time series
- RankIC mean
- ICIR
- 5-quantile forward-return buckets
- yearly RankIC summary
- yearly long-short summary
- research status

## Definitions

### Forward Return

Current implementation uses adjusted close:

- `forward_return_1d = close_adj(t+1) / close_adj(t) - 1`

Only 1-day horizon is required in v0.1, although the code accepts other positive horizons.

### RankIC

For each `trade_date`:

1. take the cross section of a factor
2. take the cross section of forward return
3. compute Spearman-style rank correlation by ranking both series first

Dates with too few samples, constant factor values, or constant returns are marked as invalid instead of being treated as normal observations.

### ICIR

Current ICIR is:

- `mean(rank_ic) / std(rank_ic) * sqrt(252 / horizon)`

This is a research-stage annualized stability proxy, not a production risk model.

### Quantile Return

For each `trade_date`:

1. rank factor values in the cross section
2. split into 5 quantiles
3. compute average forward return for each quantile
4. compute `long_short = top_quantile - bottom_quantile`

If one date has too few valid assets or insufficient factor dispersion, that date is skipped.

## Factor Correlation Scope

Current implementation uses:

- per-date cross-sectional Spearman correlation matrix
- average that matrix across all valid dates

This is a simple redundancy check. It is not a regime-aware correlation model.

## Screening Recommendation

Current recommendation labels:

- `keep`
- `review`
- `deprecate_candidate`

This is only a research suggestion. It is not an automatic trading decision and it does not delete factors.

Current screening reasons include:

- `missing_ratio_too_high`
- `finite_ratio_too_low`
- `weak_rank_ic`
- `insufficient_history`
- `high_corr_with_<factor>`

## Standard Workflow

```powershell
D:\anaconda\envs\alpha_lab\python.exe scripts\build_factors.py
D:\anaconda\envs\alpha_lab\python.exe scripts\run_single_factor_analysis.py --factor mom_20
D:\anaconda\envs\alpha_lab\python.exe scripts\run_factor_correlation.py --threshold 0.8
D:\anaconda\envs\alpha_lab\python.exe scripts\run_factor_screening.py
```

## Current Boundaries

- no multi-factor portfolio optimizer
- no machine-learning feature selection
- no industry-neutral or size-neutral research adjustment
- no factor turnover cost model
- no automated archive or delete workflow

## TODO

- factor version comparison
- cross-factor clustering
- decay analysis by multiple horizons
- sector-neutral single-factor research
- more robust sample sufficiency rules
