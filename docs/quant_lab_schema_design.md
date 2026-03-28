# quant_lab 各层标准数据 schema 设计文档

## 1. 文档目标与设计原则

### 1.1 文档目标

本文件用于定义 `quant_lab` 六层架构之间的标准数据对象和层间契约，作为 v0.1 的工程实现基线。目标不是补充业务功能，而是先统一输入输出边界，避免数据层、因子层、策略层、回测层、分析层、报告层分别定义自己的表结构，导致接口失控。

本文件回答以下工程问题：

- 各层之间通过哪些标准对象通信。
- 每个对象的主键、索引、字段、数据类型、空值规则和校验规则是什么。
- 每个对象应落盘到哪里，用什么格式存储。
- 当前阶段是否需要传统数据库，以及未来如何引入 DuckDB 或数据库而不破坏现有 schema。

### 1.2 为什么先定义 schema

- 低频量化研究链路天然依赖多个中间结果复用，先定义 schema 可以降低层间耦合。
- 统一对象后，脚本、模块、人工分析和后续自动化都能围绕同一组表结构协作。
- 文件式落盘只有在 schema 明确时才可维护，否则同名文件会逐渐变成“语义不稳定”的缓存。
- 后续即使引入 DuckDB、SQLite、PostgreSQL，也应映射现有对象，而不是重写对象语义。

### 1.3 设计原则

- 单一主键体系：项目内部统一主键为 `trade_date + asset`。
- 分层解耦：每一层只消费上层标准对象，只输出本层标准对象。
- 中间结果可落盘：核心对象必须可序列化为 `parquet/csv/json/html/png`。
- 先文件式存储，后查询增强：v0.1 以本地文件为主，不以数据库为前提。
- 向后兼容优先：新增字段优先追加，避免重命名、换主键、换索引。

## 2. 六层架构总览

| 层级 | 职责 | 不负责 |
|---|---|---|
| 数据层 | 获取、清洗、标准化、缓存原始行情与基础面数据，产出 `market_panel` | 不负责因子计算、选股逻辑、回测收益归因 |
| 因子层 | 基于 `market_panel` 计算数值型因子，并做截面预处理 | 不负责交易规则、仓位约束、成交模拟 |
| 策略层 | 基于 `factor_panel` 生成信号、打分和目标权重，产出 `target_positions` | 不负责撮合成交、收益计算、绩效评估 |
| 回测层 | 基于行情和目标权重模拟持仓演变、交易与净值，产出 `daily_positions`、`trades`、`nav` | 不负责因子构造、图表展示、报告排版 |
| 分析层 | 对回测结果和因子结果做绩效、稳健性、诊断分析，产出 `analysis_result` | 不负责 HTML 报告渲染 |
| 可视化与报告层 | 负责表格、图像、HTML 报告等展示型产物，产出 `report_artifacts` | 不负责修改核心研究数据对象 |

边界要求：

- 数据层只负责获取、清洗、标准化、缓存。
- 因子层只负责计算与预处理。
- 策略层只负责信号与目标权重。
- 回测层只负责模拟执行与净值。
- 分析层只负责指标与检验。
- 报告层只负责展示输出。

## 3. 全项目统一命名规范

### 3.1 主键与统一字段

v0.1 必须统一：

| 字段 | 标准含义 | 类型 | 规则 |
|---|---|---|---|
| `trade_date` | 交易日 | `datetime64[ns]` | 项目内部统一日期列；不得保留字符串日期作为主日期列 |
| `asset` | 项目内部统一证券标识 | `string` | 项目统一主键的一部分 |
| `ts_code` | TuShare 原始代码 | `string` | 来源字段，不作为内部主键 |
| `symbol` | 非 TuShare 风格代码或展示代码 | `string` | 辅助字段，不作为内部主键 |

统一规则：

- 项目内部标准主键统一为 `trade_date + asset`。
- `asset` 是标准内部标识；`ts_code`、`symbol` 只作为来源字段或辅助字段。
- 同一对象内不得混用 `asset` 和 `ts_code` 作为索引。

### 3.2 市场与策略字段命名

| 语义 | 标准列名 | 禁止或不推荐 |
|---|---|---|
| 开盘价 | `open` | `open_price` |
| 最高价 | `high` | `high_price` |
| 最低价 | `low` | `low_price` |
| 收盘价 | `close` | `close_price` |
| 成交量 | `volume` | `vol` |
| 成交额 | `amount` | `amt` |
| 复权因子 | `adj_factor` | `adj` |
| 复权收盘价 | `close_adj` | `adj_close` |
| 打分 | `score` | `alpha_score` |
| 目标权重 | `target_weight` | `weight_target` |
| 日净收益 | `net_ret` | `daily_return` 作为标准列名不再推荐 |
| 净值 | `nav` | `cum_nav` |

v0.1 必须遵守：

- `volume` 作为统一标准列名，不再混用 `vol`。
- `net_ret` 作为净收益标准列名；若历史实现存在 `daily_return`，应在接口层兼容映射到 `net_ret`。

### 3.3 `trade_date / asset / symbol / ts_code` 映射规则

- `trade_date`：统一为 pandas `datetime64[ns]`，时区为空，不带交易时刻。
- `asset`：统一为字符串证券代码，建议沿用 A 股标准代码字符串，例如 `000001.SZ`、`600000.SH`。
- `ts_code`：保留 TuShare 原始代码；若来源即 TuShare，可令 `asset == ts_code`。
- `symbol`：展示用或来源补充字段，例如 `000001`。若上游来源缺失，可为空。

推荐映射：

| 来源 | 来源代码列 | 标准 `asset` | 标准 `ts_code` | 标准 `symbol` |
|---|---|---|---|---|
| TuShare | `ts_code` | 直接复制 `ts_code` | 原值保留 | 可由 `ts_code` 去后缀生成 |
| AkShare | `symbol` / `code` | 需映射成带交易所后缀的标准代码 | 如无法可靠构造可为空 | 原值保留 |

## 4. 标准数据对象总表

| 对象名 | 所属层 | 输入来源 | 输出去向 | 存储格式 | 索引 | 核心字段 | 是否落盘 | 推荐文件路径 |
|---|---|---|---|---|---|---|---|---|
| `market_panel` | 数据层 | `daily`、`adj_factor`、`daily_basic`、补充元数据 | 因子层、回测层 | `parquet` | `MultiIndex(trade_date, asset)` | `open/high/low/close/volume/amount/adj_factor/close_adj/...` | 是 | `data/warehouse/market_panel.parquet` |
| `factor_panel` | 因子层 | `market_panel` | 策略层、分析层 | `parquet` | `MultiIndex(trade_date, asset)` | `mom_20/rev_5/vol_20/...` | 是 | `data/warehouse/factor_panel.parquet` |
| `target_positions` | 策略层 | `factor_panel` | 回测层 | `parquet` | `MultiIndex(trade_date, asset)` | `score/target_weight` | 是 | `data/warehouse/target_positions.parquet` |
| `daily_positions` | 回测层 | `market_panel`、`target_positions` | 分析层、报告层 | `parquet` | `MultiIndex(trade_date, asset)` | `weight/shares/close/market_value` | 是 | `data/warehouse/backtest/daily_positions.parquet` |
| `trades` | 回测层 | `market_panel`、`target_positions`、上日持仓 | 分析层、报告层 | `parquet` | 推荐普通索引或 `MultiIndex(trade_date, asset)` | `side/price/shares/amount/cost` | 是 | `data/warehouse/backtest/trades.parquet` |
| `nav` | 回测层 | 回测逐日收益 | 分析层、报告层 | `parquet` | `Index(trade_date)` | `gross_ret/cost/net_ret/nav` | 是 | `data/warehouse/backtest/nav.parquet` |
| `analysis_result` | 分析层 | `factor_panel`、`daily_positions`、`trades`、`nav` | 报告层 | `json/csv/parquet` | 依子对象而定 | `performance/robustness/factor_diagnostics` | 是 | `data/warehouse/backtest/analysis/` |
| `report_artifacts` | 报告层 | `analysis_result`、`nav`、图表数据 | 最终展示 | `html/png/csv` | 不要求统一索引 | 报告页面、图表、汇总表 | 是 | `reports/html/`、`reports/figures/`、`reports/tables/` |

## 5. 数据层 schema 详细定义

### 5.1 `market_panel` 定义

- 类型：`pandas.DataFrame`
- 索引：`MultiIndex([trade_date, asset])`
- 排序规则：必须按 `trade_date ASC, asset ASC` 排序
- 主键唯一性：`trade_date + asset` 必须唯一
- 存储格式：优先 `parquet`

### 5.2 字段集合

#### 最低字段集合，v0.1 必须字段

| 字段 | 类型 | 必填 | 允许空值 | 说明 |
|---|---|---|---|---|
| `open` | `float64` | 是 | 否 | 当日开盘价 |
| `high` | `float64` | 是 | 否 | 当日最高价 |
| `low` | `float64` | 是 | 否 | 当日最低价 |
| `close` | `float64` | 是 | 否 | 当日收盘价 |
| `volume` | `float64` | 是 | 否 | 成交量，统一使用 `volume` |
| `amount` | `float64` | 是 | 是 | 成交额，缺失时可为 `NaN` |
| `adj_factor` | `float64` | 是 | 否 | 标准化后的复权因子 |
| `close_adj` | `float64` | 是 | 否 | 复权收盘价，定义为 `close * adj_factor` |
| `turnover_rate` | `float64` | 否 | 是 | 换手率 |
| `pe` | `float64` | 否 | 是 | 市盈率 |
| `pb` | `float64` | 否 | 是 | 市净率 |
| `total_mv` | `float64` | 否 | 是 | 总市值 |

#### 推荐来源辅助字段

| 字段 | 类型 | 必填 | 允许空值 | 说明 |
|---|---|---|---|---|
| `ts_code` | `string` | 否 | 是 | TuShare 原始代码 |
| `symbol` | `string` | 否 | 是 | 原始或展示代码 |
| `source` | `string` | 否 | 是 | 数据来源，如 `tushare`、`akshare` |
| `is_suspended` | `boolean` | 否 | 是 | 是否停牌 |

#### 可选扩展字段

- `vwap`
- `limit_up`
- `limit_down`
- `float_mv`
- `circ_mv`
- `industry`

### 5.3 空值规则

v0.1 必须遵守：

- `open/high/low/close/volume/adj_factor/close_adj` 不允许空值。
- `amount/turnover_rate/pe/pb/total_mv` 允许空值。
- 来源缺字段时，必须补标准列并填 `NaN`，不得直接缺列。
- 不允许用 `0` 伪装缺失基本面字段；`pe/pb/turnover_rate/total_mv` 缺失应保持 `NaN`。

### 5.4 来源映射规则

- TuShare 为主数据源，原始文件保存在 `data/raw/tushare/`。
- AkShare 为补充或兜底源，原始文件保存在 `data/raw/akshare/`。
- 来源差异必须在数据层被吸收，不得把来源差异传播到 `market_panel`。

统一转换要求：

- `trade_date` 统一转为 `datetime64[ns]`。
- `asset` 统一转为字符串代码。
- `vol` 必须重命名为 `volume`。
- 若来源提供的是“原始累计复权因子”，则应先在数据层转换为标准 `adj_factor`，使 `close_adj = close * adj_factor` 成立。

### 5.5 字段计算规则

- `close_adj = close * adj_factor`
- `adj_factor` 在标准对象中表示已标准化复权因子，而不是任意来源原始字段

### 5.6 索引与排序示例

```text
Index: MultiIndex(levels=[trade_date, asset], names=["trade_date", "asset"])
Sort:  trade_date ascending, asset ascending
```

## 6. 因子层 schema 详细定义

### 6.1 `factor_panel` 定义

- 类型：`pandas.DataFrame`
- 索引：`MultiIndex([trade_date, asset])`
- 排序：必须与 `market_panel` 同序
- 对齐要求：`factor_panel.index` 必须严格对齐 `market_panel.index` 或为其子集；不得引入不存在于 `market_panel` 的索引

### 6.2 因子列命名规范

- 使用小写蛇形命名。
- 推荐格式：`{factor_name}_{window}`。
- 禁止把预处理状态编码进原始因子名，例如不推荐 `mom_20_zscore` 作为基础标准列。
- 若需要保留原始值和预处理值，推荐分为两个对象：
  - `factor_panel_raw`
  - `factor_panel`

### 6.3 v0.1 计划因子

| 因子列 | 类型 | 必填 | 允许空值 | 说明 |
|---|---|---|---|---|
| `mom_20` | `float64` | 是 | 是 | 20 日动量 |
| `rev_5` | `float64` | 是 | 是 | 5 日短期反转 |
| `vol_20` | `float64` | 是 | 是 | 20 日波动率 |
| `turnover_20` | `float64` | 是 | 是 | 20 日平均换手 |
| `price_volume_corr_20` | `float64` | 是 | 是 | 20 日收益与量变相关性 |
| `bp` | `float64` | 是 | 是 | `1 / pb` |
| `ep` | `float64` | 是 | 是 | `1 / pe` |
| `size` | `float64` | 是 | 是 | `log(total_mv)` |

### 6.4 空值与稀疏规则

- 因子允许为空，常见原因包括滚动窗口不足、来源缺失、停牌、基本面缺失。
- 因子允许稀疏，但必须保证列存在。
- 不允许使用字符串、对象类型存储因子值。
- `NaN` 是合法缺失值表示，不应用 `0` 替代。

### 6.5 预处理规则

- 因子层负责数值预处理，如去极值、标准化、中性化。
- 因子层不负责交易逻辑。
- 因子层只输出数值因子面板。

v0.1 建议：

- 预处理后输出新表，不覆盖原值。
- 若仓库当前只保留一个对象，优先把最终供策略使用的标准化结果命名为 `factor_panel`，原始版本可选存为 `factor_panel_raw.parquet`。

## 7. 策略层 schema 详细定义

### 7.1 `target_positions` 定义

- 类型：`pandas.DataFrame`
- 索引：`MultiIndex([trade_date, asset])`
- 含义：某交易日收盘后或调仓时点，策略希望在下一执行周期持有的目标组合

### 7.2 字段定义

#### v0.1 必须字段

| 字段 | 类型 | 必填 | 允许空值 | 说明 |
|---|---|---|---|---|
| `score` | `float64` | 是 | 是 | 策略打分，可为空 |
| `target_weight` | `float64` | 是 | 否 | 目标权重，空仓资产填 `0.0` |

#### 可选扩展字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `rank` | `float64` / `int64` | 截面排名 |
| `signal` | `float64` | 原始信号值 |
| `side` | `string` | `LONG`/`SHORT` |
| `group` | `string` | 分组、行业、中性化桶等 |

### 7.3 约束规则

- 策略层输出的是目标持仓，不是成交记录。
- `target_weight` 建议范围为 `[-1.0, 1.0]`。
- 纯多头 v0.1 默认约束：`0 <= target_weight <= 1`。
- 单日权重和约束：
  - 纯多策略建议满足 `sum(target_weight) <= 1.0 + tol`
  - 满仓策略建议满足 `abs(sum(target_weight) - 1.0) <= tol`
  - `tol` 推荐为 `1e-6`
- 允许空仓日：
  - 方式一：该日保留资产行，`target_weight = 0.0`
  - 方式二：该日无任何资产行，但回测层需在接口处补零
  - v0.1 推荐方式一，便于显式表达

## 8. 回测层 schema 详细定义

### 8.1 回测层输入输出边界

输入：

- `market_panel`
- `target_positions`
- 回测配置，如手续费、滑点、印花税、初始资金

输出：

- `daily_positions`
- `trades`
- `nav`
- 可选 `metrics.json`

边界说明：

- 回测层只做简化模拟执行，不做真实交易所级撮合。
- v0.1 简化边界：按日频、按收盘或次日收益近似执行，可支持简单交易成本模型。
- 委托簿、盘口冲击、部分成交、涨跌停成交失败等不属于 v0.1 必须能力。

### 8.2 `daily_positions`

- 类型：`pandas.DataFrame`
- 索引：推荐 `MultiIndex([trade_date, asset])`
- 与 `target_positions` 关系：由目标权重经过回测执行和持仓延续得到的实际日度持仓

#### 建议字段

| 字段 | 类型 | 必填 | 允许空值 | 说明 |
|---|---|---|---|---|
| `weight` | `float64` | 是 | 否 | 实际持仓权重 |
| `shares` | `float64` | 否 | 是 | 持仓股数，简化回测可选 |
| `close` | `float64` | 是 | 否 | 当日收盘价 |
| `market_value` | `float64` | 否 | 是 | 市值 |

v0.1 最低实现可以只有 `weight`，但标准对象推荐扩展为上表四列。

### 8.3 `trades`

- 类型：`pandas.DataFrame`
- 索引：默认普通 RangeIndex；也可按 `trade_date, asset` 排序后保存
- 与 `target_positions` 关系：由目标权重变化推导出的调仓记录

#### 建议字段

| 字段 | 类型 | 必填 | 允许空值 | 说明 |
|---|---|---|---|---|
| `trade_date` | `datetime64[ns]` | 是 | 否 | 交易日 |
| `asset` | `string` | 是 | 否 | 证券代码 |
| `side` | `string` | 是 | 否 | `BUY` 或 `SELL` |
| `price` | `float64` | 否 | 是 | 成交价格，简化回测可近似为收盘价 |
| `shares` | `float64` | 否 | 是 | 成交数量 |
| `amount` | `float64` | 否 | 是 | 成交金额 |
| `cost` | `float64` | 否 | 是 | 交易成本 |
| `weight_delta` | `float64` | 否 | 是 | 权重变化，作为简化回测兼容字段 |

### 8.4 `nav`

- 类型：`pandas.DataFrame`
- 索引：`Index(trade_date)`

#### v0.1 标准字段

| 字段 | 类型 | 必填 | 允许空值 | 说明 |
|---|---|---|---|---|
| `gross_ret` | `float64` | 是 | 否 | 扣成本前组合收益 |
| `cost` | `float64` | 是 | 否 | 当日总成本 |
| `net_ret` | `float64` | 是 | 否 | 扣成本后日收益 |
| `nav` | `float64` | 是 | 否 | 累计净值 |

兼容建议：

- 若历史实现存在 `daily_return`，应在读取层映射到 `net_ret`。

## 9. 分析层与报告层 schema 详细定义

### 9.1 `analysis_result` 组织形式

推荐组织为一个目录，而不是单个巨型对象：

- `performance`
- `robustness`
- `factor_diagnostics`

推荐结构：

| 子对象 | 推荐 Python 形态 | 推荐落盘 | 说明 |
|---|---|---|---|
| `performance` | `dict[str, float]` + `DataFrame` | `json` + `csv` | 核心绩效指标、年度分解 |
| `robustness` | `DataFrame` | `csv/parquet` | 参数敏感性、样本切分结果 |
| `factor_diagnostics` | `DataFrame` / `dict` | `csv/parquet/json` | IC、分组收益、覆盖率、缺失率 |

### 9.2 各格式角色

- `parquet`：适合中大型结构化表，如分组收益面板、逐期诊断面板。
- `csv`：适合轻量表格和人工查看，如年度绩效表、参数扫描摘要。
- `json`：适合标量指标、嵌套分析摘要、元数据。
- `html`：适合汇总展示。
- `png`：适合曲线图、柱状图、热力图等最终图形产物。

### 9.3 `report_artifacts`

报告层输出不再强调统一 DataFrame schema，而强调产物归类：

- `reports/tables/*.csv`
- `reports/figures/*.png`
- `reports/html/*.html`

## 10. 存储策略设计

### 10.1 为什么第一版优先采用 Parquet 文件式存储

- `parquet` 对列式研究数据友好，适合面板数据压缩和按列读取。
- 与 pandas 直接兼容，工程复杂度低。
- 适合本地单机研究流，不需要额外部署数据库服务。
- 中间结果文件化后，调试和复现比数据库表更直接。

### 10.2 为什么当前阶段不需要 MySQL / PostgreSQL / MongoDB

- v0.1 目标是打通本地研究链路，不是服务化多用户系统。
- 当前对象主要是批处理面板，不是高并发事务型读写。
- 数据来源本身是文件批量更新，先落盘再计算更自然。
- 数据库会引入额外 schema migration、权限、运维、备份复杂度，但对当前单机研究收益有限。

结论：

- 当前阶段不需要传统数据库作为主存储。

### 10.3 CSV、HTML、PNG、日志文件角色

- `CSV`：轻量导出、人工检查、报告表格交换格式。
- `HTML`：最终汇总报告。
- `PNG`：静态图形。
- `logs/*.log`：任务执行日志，不属于核心研究 schema，但属于运行审计产物。

### 10.4 DuckDB 的未来位置

若后续引入 DuckDB，推荐作为“查询增强层”或“仓库访问加速层”：

- 不替代 `data/raw/` 原始文件存储。
- 不改变 `market_panel/factor_panel/target_positions/nav` 等标准对象定义。
- 主要用于：
  - 快速 SQL 查询 parquet
  - 跨对象联表分析
  - 报告层临时查询加速

因此，DuckDB 应放在文件仓库之上，作为辅助能力，而不是主数据源。

## 11. 数据校验规则

### 11.1 最小校验规则

v0.1 必须至少校验：

- 索引唯一性检查
- `trade_date` 类型检查
- `asset` 类型检查
- 必填列检查
- 数值列类型检查
- 排序检查
- 重复行检查
- 可选字段缺失告警

### 11.2 建议函数签名

```python
def validate_panel_schema(
    df: pd.DataFrame,
    *,
    required_columns: list[str],
    numeric_columns: list[str],
    allow_nullable_columns: list[str],
    require_multiindex: bool = True,
) -> None:
    ...


def validate_trade_asset_index(df: pd.DataFrame) -> None:
    ...


def validate_nav_schema(df: pd.DataFrame) -> None:
    ...
```

### 11.3 建议校验逻辑伪代码

```python
if require_multiindex:
    assert list(df.index.names) == ["trade_date", "asset"]
    assert df.index.is_unique

trade_dates = df.index.get_level_values("trade_date")
assets = df.index.get_level_values("asset")

assert pd.api.types.is_datetime64_ns_dtype(trade_dates)
assert pd.api.types.is_string_dtype(pd.Series(assets, dtype="string"))
assert df.sort_index().index.equals(df.index)

for col in required_columns:
    assert col in df.columns

for col in numeric_columns:
    assert pd.api.types.is_numeric_dtype(df[col])

duplicates = df.reset_index().duplicated(subset=["trade_date", "asset"])
assert not duplicates.any()

for col in df.columns:
    if col in allow_nullable_columns and df[col].isna().any():
        warnings.warn(f"{col} has missing values")
```

## 12. 版本与兼容性策略

### 12.1 为什么需要 schema version

- 文件式仓库没有数据库 migration 系统，因此必须显式标记 schema 版本。
- 版本号用于约束脚本、校验器、报告构建器之间的兼容关系。

### 12.2 v0.1 标记方式

推荐在以下位置至少保留一个版本标记：

- 文档中声明当前版本为 `schema_version = "0.1"`
- 可选在对象元数据 JSON 中保存：
  - `data/warehouse/_meta/schema_version.json`
- 可选在每个输出目录附带 `manifest.json`

### 12.3 向后兼容策略

- 新增非必填字段：属于兼容变更。
- 新增可选对象：属于兼容变更。
- 新增校验告警但不改变对象结构：属于兼容变更。

### 12.4 Breaking change 定义

以下变更属于 breaking change：

- 修改统一主键，从 `trade_date + asset` 改为其他体系。
- 重命名标准字段，如把 `volume` 改回 `vol`。
- 改变字段含义，如 `target_weight` 从目标权重变成实际权重。
- 改变索引类型，如把 `factor_panel` 从双索引改为宽表日期索引。
- 将原本必填字段改为缺失或删除。

## 13. 建议的目录与文件命名规范

### 13.1 推荐目录

```text
data/
  raw/
    tushare/
    akshare/
  cache/
  temp/
  warehouse/
    market_panel.parquet
    factor_panel.parquet
    target_positions.parquet
    backtest/
      daily_positions.parquet
      trades.parquet
      nav.parquet
      metrics.json
      analysis/
        performance.json
        yearly_breakdown.csv
        factor_diagnostics.parquet
reports/
  tables/
  figures/
  html/
logs/
```

### 13.2 文件命名规范

- 标准对象使用稳定文件名，不在文件名里编码日期范围：
  - `market_panel.parquet`
  - `factor_panel.parquet`
  - `target_positions.parquet`
  - `nav.parquet`
- 分析与报告产物可按任务名或时间戳命名：
  - `performance_summary.csv`
  - `nav_curve.png`
  - `backtest_report.html`

## 14. 从 schema 到代码接口的映射建议

以下接口签名应与本文件定义的标准对象一致：

```python
def build_market_panel(
    daily: pd.DataFrame,
    adj_factor: pd.DataFrame,
    daily_basic: pd.DataFrame,
) -> pd.DataFrame:
    """Return market_panel indexed by [trade_date, asset]."""


def build_factor_panel(
    market_panel: pd.DataFrame,
    apply_standardize: bool = True,
) -> pd.DataFrame:
    """Return factor_panel indexed by [trade_date, asset]."""


def generate_target_positions(
    factor_panel: pd.DataFrame,
    factor_weights: dict[str, float],
    top_n: int,
    rebalance_every: int,
) -> pd.DataFrame:
    """Return target_positions indexed by [trade_date, asset]."""


@dataclass(slots=True)
class BacktestResult:
    nav: pd.DataFrame
    daily_positions: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict[str, float]


def run_backtest(
    market_panel: pd.DataFrame,
    target_positions: pd.DataFrame,
    commission: float,
    slippage: float,
    stamp_tax: float,
) -> BacktestResult:
    """Return nav, daily_positions and trades under the standard schema."""


def analyze_backtest_result(result: BacktestResult) -> dict:
    """Return analysis_result grouped by performance, robustness and diagnostics."""


def build_report(
    analysis_result: dict,
    output_dir: str | Path,
) -> None:
    """Render report_artifacts into reports/tables, reports/figures and reports/html."""
```

实现建议：

- 策略脚本内部可以继续调用现有 `build_signals(...)`，但对外推荐统一为 `generate_target_positions(...)`。
- 回测层建议逐步把 `nav` 列从 `daily_return` 迁移到 `net_ret`。

## 15. 结论与实施优先级

### 15.1 第一优先级必须先实现的 4 个标准对象

- `market_panel`
- `factor_panel`
- `target_positions`
- `nav`

原因：

- 这四个对象构成研究链路最短闭环。
- 先统一这四个对象，数据层、策略层、回测层即可稳定对接。

### 15.2 第二阶段再完善的对象

- `daily_positions`
- `trades`
- `analysis_result`
- `report_artifacts`

### 15.3 当前项目下一步最优先工作

- 先让 `market_panel`、`factor_panel`、`target_positions`、`nav` 的 schema 与本文件完全一致。
- 补充统一校验函数，在每个脚本落盘前执行 schema 检查。
- 对现有实现中的命名差异做兼容层，例如把 `daily_return` 统一映射为 `net_ret`。

---

## 附录 A：字段词典

| 字段 | 中文说明 | 所属对象 |
|---|---|---|
| `trade_date` | 交易日 | 全局主键 |
| `asset` | 内部统一证券标识 | 全局主键 |
| `ts_code` | TuShare 原始代码 | 数据层来源字段 |
| `symbol` | 展示或来源代码 | 数据层来源字段 |
| `open/high/low/close` | OHLC 行情字段 | `market_panel` |
| `volume` | 成交量 | `market_panel` |
| `amount` | 成交额 | `market_panel` |
| `adj_factor` | 标准化复权因子 | `market_panel` |
| `close_adj` | 复权收盘价 | `market_panel` |
| `score` | 策略打分 | `target_positions` |
| `target_weight` | 目标权重 | `target_positions` |
| `weight` | 实际持仓权重 | `daily_positions` |
| `gross_ret` | 扣成本前收益 | `nav` |
| `cost` | 交易成本 | `nav` / `trades` |
| `net_ret` | 扣成本后收益 | `nav` |
| `nav` | 累计净值 | `nav` |

## 附录 B：v0.1 必须遵守 vs 后续建议

### v0.1 必须遵守

- 主键统一为 `trade_date + asset`
- `trade_date` 类型统一为 `datetime64[ns]`
- `volume` 统一命名，不再混用 `vol`
- 六层只通过标准对象通信
- 核心对象优先落盘为 `parquet`
- 当前阶段不需要传统数据库作为主存储

### 后续扩展建议

- 引入 `factor_panel_raw`
- 为对象增加 `manifest.json`
- 以 DuckDB 作为 parquet 查询加速层
- 为 `daily_positions` 和 `trades` 增加更完整的成交字段
