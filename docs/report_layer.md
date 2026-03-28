# Report Layer v0.1

## Responsibility

The report layer converts warehouse backtest outputs into readable figures, tables, and a local HTML report.

It does not:

- rebuild strategy logic
- rerun factor research
- compare many strategies
- export PDF
- send email

## Standard Inputs

Required:

- `data/warehouse/factor_research_summary.csv`
- `data/warehouse/factor_screening_summary.csv`
- `data/warehouse/strategy_diagnostics.csv`
- `data/warehouse/nav.parquet`
- `data/warehouse/trades.parquet`
- `data/warehouse/daily_positions.parquet`
- `data/warehouse/performance_summary.csv`
- `config/report.yaml`

Optional:

- `data/warehouse/factor_metadata.csv`
- `data/warehouse/high_correlation_pairs.csv`
- `data/warehouse/factor_correlation_matrix.csv`

## Standard Outputs

- `reports/figures/*.png`
- `reports/tables/*.csv`
- `reports/html/backtest_report.html`

## Figure Meanings

- `nav_curve.png`: strategy NAV path
- `drawdown_curve.png`: NAV drawdown path
- `turnover_curve.png`: daily portfolio turnover
- `screening_distribution.png`: count of `keep / review / deprecate_candidate`
- `factor_correlation_heatmap.png`: optional factor correlation heatmap

## Table Meanings

- `performance_summary.csv`: core backtest metrics
- `strategy_summary.csv`: rebalance count, trade count, average candidates, average selected
- `factor_summary.csv`: metadata status counts and screening recommendation counts
- `top_trades.csv`: largest trades by amount / cost
- `latest_positions.csv`: latest daily position snapshot

## HTML Structure

Current HTML report includes:

1. title and generation time
2. short-sample warning block if triggered
3. summary cards
4. run environment summary
5. backtest convention summary
6. sample window summary
7. performance table
8. NAV / drawdown / turnover figures
9. strategy summary section
10. factor summary section
11. optional correlation heatmap
12. top trades and latest positions
13. limitations

## Short Sample Warning

Warning is triggered when:

- `performance_summary.csv` has `message = short_sample`
- or `trading_days < 20`

When triggered, the HTML report shows a visible warning block near the top.

## Limits

- current report is for research only
- current backtest convention is `next_open`
- no real tradability guarantee
- no suspension / limit-up-down validation
- no multi-strategy comparison

## TODO

- benchmark comparison charts
- richer factor diagnostics tables
- report index page
- PDF export
