# Backtest Layer v0.1

## Responsibility

The backtest layer converts strategy target positions into executed holdings, trade records, NAV, and minimal performance statistics.

It does not model:

- live trading
- exchange microstructure
- complex matching logic
- multi-strategy allocation
- risk model optimization

## Input Objects

- `data/warehouse/market_panel.parquet`
- `data/warehouse/target_positions.parquet`
- `config/backtest.yaml`

## Output Objects

- `data/warehouse/daily_positions.parquet`
- `data/warehouse/trades.parquet`
- `data/warehouse/nav.parquet`
- `data/warehouse/performance_summary.csv`

## target_positions vs daily_positions

`target_positions`:

- strategy intent
- desired portfolio weights
- not actual executed holdings

`daily_positions`:

- backtest execution result
- realized holdings after next-day execution
- contains actual shares, close price, and end-of-day market value

These two objects are intentionally different and should not be mixed.

## Execution Convention

Current convention:

- signals are assumed known after `trade_date` close
- target weights are executed on the next trading day
- execution price is currently `next_open`

Meaning:

- target on `T`
- execution on `T+1` open
- holdings are marked to `T+1` close for end-of-day NAV

## Cost Model

Current cost model:

- `commission`
- `slippage`
- `stamp_tax_sell`

Buy cost:

- `amount * (commission + slippage)`

Sell cost:

- `amount * (commission + slippage + stamp_tax_sell)`

## Turnover Definition

Current daily turnover is:

- `sum(abs(traded_amount)) / start_of_day_portfolio_value`

This is a simple research-stage portfolio turnover measure.

## NAV Logic

For each execution day:

1. start with cash plus previous shares valued at execution price
2. compute desired shares from shifted target weights
3. trade at execution price
4. subtract costs from cash
5. mark holdings to close price
6. compute:
   - `gross_ret`
   - `turnover`
   - `cost`
   - `net_ret`
   - `nav`

## Performance Summary

Current metrics:

- `total_return`
- `annualized_return`
- `annualized_volatility`
- `sharpe`
- `max_drawdown`
- `avg_turnover`
- `win_rate`
- `trading_days`

If the sample is very short, summary message is marked as `short_sample`.

## Limits

- only long-only
- only next-day execution
- only one simple execution price convention
- no停牌 / 涨跌停 / 成交量约束
- no intraday path
- no cash interest
- no borrow / shorting

## TODO

- support `next_close`
- more robust lot-size and residual cash handling
- suspension and limit-up/limit-down constraints
- richer trade validation and audit output
- benchmark-relative performance
