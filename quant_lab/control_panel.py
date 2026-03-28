"""Thin orchestration layer for the local control panel."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quant_lab.analysis_layer.factor_analysis import compute_rank_ic
from quant_lab.analysis_layer.performance import yearly_breakdown
from quant_lab.analysis_layer.robustness import summarize_turnover
from quant_lab.backtest_layer.engine import run_backtest
from quant_lab.backtest_layer.recorder import save_backtest_result
from quant_lab.common.io import read_dataframe, read_json, write_dataframe, write_json
from quant_lab.common.logger import setup_logger
from quant_lab.common.paths import FIGURE_DIR, HTML_DIR, RAW_AKSHARE_DIR, RAW_TUSHARE_DIR, TABLE_DIR, WAREHOUSE_DIR, ensure_directories
from quant_lab.data_layer.hybrid_source import HybridSource
from quant_lab.data_layer.market_panel import build_market_panel
from quant_lab.factor_layer.factor_panel import build_factor_panel
from quant_lab.report_layer.html_report import build_html_report
from quant_lab.report_layer.plots import plot_nav
from quant_lab.report_layer.tables import metrics_to_table, save_markdown_table
from quant_lab.settings import AppSettings
from quant_lab.strategy_layer.signal_builder import build_signals


@dataclass(slots=True)
class PanelConfig:
    """Runtime config overrides from the Streamlit panel."""

    start_date: str
    end_date: str
    top_n: int
    rebalance_every: int
    commission: float
    slippage: float
    enable_tushare: bool
    enable_akshare_fallback: bool


def _bootstrap() -> None:
    ensure_directories()
    setup_logger()


def _ensure_panel_index(df):
    if {"trade_date", "asset"}.issubset(df.columns):
        return df.set_index(["trade_date", "asset"])
    return df


def run_update_data(config: PanelConfig) -> str:
    """Fetch and persist raw data."""
    _bootstrap()
    settings = AppSettings.load()
    source = HybridSource(
        enable_tushare=config.enable_tushare,
        enable_akshare_fallback=config.enable_akshare_fallback,
    )
    bundle = source.fetch_bundle(
        symbols=settings.data.get("universe", []),
        start_date=config.start_date.replace("-", ""),
        end_date=config.end_date.replace("-", ""),
    )
    write_dataframe(bundle.stock_basic, RAW_TUSHARE_DIR / "stock_basic.parquet")
    write_dataframe(bundle.trade_calendar, RAW_TUSHARE_DIR / "trade_calendar.parquet")
    write_dataframe(bundle.daily, RAW_TUSHARE_DIR / "daily.parquet")
    write_dataframe(bundle.adj_factor, RAW_TUSHARE_DIR / "adj_factor.parquet")
    write_dataframe(bundle.daily_basic, RAW_TUSHARE_DIR / "daily_basic.parquet")
    write_dataframe(bundle.daily.iloc[0:0], RAW_AKSHARE_DIR / "daily.parquet")
    return "原始数据更新完成"


def run_build_market_panel() -> str:
    """Build the market panel."""
    _bootstrap()
    daily = read_dataframe(RAW_TUSHARE_DIR / "daily.parquet")
    adj_factor = read_dataframe(RAW_TUSHARE_DIR / "adj_factor.parquet")
    daily_basic = read_dataframe(RAW_TUSHARE_DIR / "daily_basic.parquet")
    market_panel = build_market_panel(daily=daily, adj_factor=adj_factor, daily_basic=daily_basic)
    write_dataframe(market_panel, WAREHOUSE_DIR / "market_panel.parquet")
    return f"市场面板构建完成，shape={market_panel.shape}"


def run_build_factors() -> str:
    """Build factor panel."""
    _bootstrap()
    market_panel = _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "market_panel.parquet"))
    factor_panel = build_factor_panel(market_panel)
    write_dataframe(factor_panel, WAREHOUSE_DIR / "factor_panel.parquet")
    return f"因子面板构建完成，shape={factor_panel.shape}"


def run_strategy(config: PanelConfig) -> str:
    """Run ranking strategy."""
    _bootstrap()
    settings = AppSettings.load()
    factor_panel = _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "factor_panel.parquet"))
    target_positions = build_signals(
        factor_panel=factor_panel,
        factor_weights=settings.strategy.get("factor_weights", {}),
        top_n=config.top_n,
        rebalance_every=config.rebalance_every,
    )
    write_dataframe(target_positions, WAREHOUSE_DIR / "target_positions.parquet")
    return f"策略运行完成，shape={target_positions.shape}"


def run_backtest_step(config: PanelConfig) -> str:
    """Run the backtest."""
    _bootstrap()
    settings = AppSettings.load()
    market_panel = _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "market_panel.parquet"))
    target_positions = _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "target_positions.parquet"))
    result = run_backtest(
        market_panel=market_panel,
        target_positions=target_positions,
        commission=config.commission,
        slippage=config.slippage,
        stamp_tax=float(settings.backtest.get("stamp_tax", 0.001)),
    )
    save_backtest_result(result, WAREHOUSE_DIR / "backtest")
    return f"回测完成，nav期末={result.nav['nav'].iloc[-1]:.4f}"


def run_analysis_step() -> str:
    """Build analysis outputs."""
    _bootstrap()
    nav = read_dataframe(WAREHOUSE_DIR / "backtest" / "nav.parquet")
    if "trade_date" in nav.columns:
        nav = nav.set_index("trade_date")
    trades = read_dataframe(WAREHOUSE_DIR / "backtest" / "trades.parquet")
    metrics = read_json(WAREHOUSE_DIR / "backtest" / "metrics.json")
    market_panel = _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "market_panel.parquet"))
    factor_panel = _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "factor_panel.parquet"))

    yearly = yearly_breakdown(nav["daily_return"])
    rank_ic = compute_rank_ic(factor_panel, market_panel, "mom_20")
    robustness = summarize_turnover(trades)
    merged_metrics = {**metrics, **robustness}
    write_dataframe(yearly, TABLE_DIR / "yearly_breakdown.csv")
    write_dataframe(rank_ic, TABLE_DIR / "rank_ic_mom20.csv")
    write_json(merged_metrics, TABLE_DIR / "analysis_metrics.json")
    return "分析结果生成完成"


def run_report_step() -> str:
    """Generate report assets."""
    _bootstrap()
    settings = AppSettings.load()
    nav = read_dataframe(WAREHOUSE_DIR / "backtest" / "nav.parquet")
    if "trade_date" in nav.columns:
        nav = nav.set_index("trade_date")
    metrics = read_json(TABLE_DIR / "analysis_metrics.json")
    metrics_table = metrics_to_table(metrics)
    figure_path = FIGURE_DIR / "nav.png"
    markdown_path = TABLE_DIR / "metrics.md"
    html_path = HTML_DIR / "report.html"
    plot_nav(nav, figure_path)
    save_markdown_table(metrics_table, markdown_path)
    build_html_report(
        title=settings.report.get("title", "Quant Lab Report"),
        summary=settings.report.get("summary", ""),
        metrics_table=metrics_table,
        nav_figure="../figures/nav.png",
        output_path=html_path,
    )
    return f"报告生成完成：{html_path}"


def run_generate_report() -> list[str]:
    """Run analysis plus report build."""
    return [run_analysis_step(), run_report_step()]


def run_all(config: PanelConfig) -> list[str]:
    """Execute the full pipeline."""
    return [
        run_update_data(config),
        run_build_market_panel(),
        run_build_factors(),
        run_strategy(config),
        run_backtest_step(config),
        run_analysis_step(),
        run_report_step(),
    ]


def artifact_status() -> dict[str, Path]:
    """Return key artifact paths."""
    return {
        "market_panel.parquet": WAREHOUSE_DIR / "market_panel.parquet",
        "factor_panel.parquet": WAREHOUSE_DIR / "factor_panel.parquet",
        "target_positions.parquet": WAREHOUSE_DIR / "target_positions.parquet",
        "report.html": HTML_DIR / "report.html",
        "nav.png": FIGURE_DIR / "nav.png",
    }
