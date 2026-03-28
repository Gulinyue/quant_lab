"""Interactive Streamlit control-panel bridge."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd
import yaml

from quant_lab.analysis_layer.factor_analysis import run_single_factor_research
from quant_lab.analysis_layer.factor_correlation import build_factor_correlation_report
from quant_lab.analysis_layer.factor_screening import build_factor_screening_summary
from quant_lab.backtest_layer.engine import run_backtest
from quant_lab.backtest_layer.recorder import save_backtest_result
from quant_lab.common.io import read_dataframe, write_dataframe, write_json
from quant_lab.common.logger import setup_logger
from quant_lab.common.paths import (
    CONFIG_DIR,
    FIGURE_DIR,
    HTML_DIR,
    RAW_AKSHARE_DIR,
    RAW_TUSHARE_DIR,
    REPORT_DIR,
    RUNS_DIR,
    TABLE_DIR,
    WAREHOUSE_DIR,
    ensure_directories,
)
from quant_lab.data_layer.hybrid_source import HybridSource
from quant_lab.data_layer.market_panel import build_market_panel
from quant_lab.factor_layer.factor_panel import build_factor_panel
from quant_lab.factor_layer.registry import FACTOR_REGISTRY
from quant_lab.pipeline.manifest import save_manifest
from quant_lab.pipeline.run_context import RunContext, generate_run_id
from quant_lab.report_layer.exporter import export_report
from quant_lab.settings import AppSettings, load_yaml_config
from quant_lab.strategy_layer.signal_builder import build_signals

ASSET_PATTERN = re.compile(r"^\d{6}\.(SZ|SH|BJ)$", re.IGNORECASE)


@dataclass(slots=True)
class PanelConfig:
    start_date: str
    end_date: str
    stock_pool_mode: str
    manual_stock_list: str = ""
    selected_assets: list[str] = field(default_factory=list)
    selected_factors: list[str] = field(default_factory=list)
    factor_weights: dict[str, float] = field(default_factory=dict)
    top_n: int = 30
    rebalance: str = "daily"
    weighting: str = "equal"
    score_transform: str = "none"
    max_weight_per_asset: float = 0.05
    min_selected_assets: int = 5
    allow_testing_factors: bool = False
    allow_review_factors: bool = True
    initial_capital: float = 1_000_000.0
    execution_price: str = "next_open"
    commission: float = 0.0003
    slippage: float = 0.0005
    stamp_tax_sell: float = 0.001
    lot_size: int = 100
    long_only: bool = True
    enable_tushare: bool = True
    enable_akshare_fallback: bool = True
    run_label: str = "panel_run"


@dataclass(slots=True)
class ActionResult:
    action: str
    status: str
    messages: list[str]
    warnings: list[str]
    run_id: str
    artifact_root: Path
    summary: dict[str, Any]


def _bootstrap() -> None:
    ensure_directories()
    setup_logger()
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_panel_index(df: pd.DataFrame) -> pd.DataFrame:
    if {"trade_date", "asset"}.issubset(df.columns):
        df = df.copy()
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df["asset"] = df["asset"].astype(str)
        return df.set_index(["trade_date", "asset"]).sort_index()
    if isinstance(df.index, pd.MultiIndex):
        return df.sort_index()
    return df


def _load_market_panel() -> pd.DataFrame:
    return _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "market_panel.parquet"))


def _load_factor_panel() -> pd.DataFrame:
    return _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "factor_panel.parquet"))


def get_available_assets() -> list[str]:
    for loader in (_load_market_panel, _load_factor_panel):
        try:
            panel = loader()
            return sorted(panel.index.get_level_values("asset").unique().astype(str).tolist())
        except Exception:
            continue
    return []


def get_configured_universe() -> list[str]:
    settings = AppSettings.load()
    return [str(asset).upper() for asset in settings.data.get("universe", [])]


def get_factor_catalog() -> pd.DataFrame:
    path = WAREHOUSE_DIR / "factor_metadata.csv"
    if path.exists():
        data = read_dataframe(path)
        if "enabled_in_config" not in data.columns:
            data["enabled_in_config"] = False
        return data
    rows: list[dict[str, Any]] = []
    for spec in FACTOR_REGISTRY.list_specs():
        rows.append(
            {
                "name": spec.name,
                "group": spec.group,
                "category": spec.category,
                "status": spec.status,
                "description": spec.description,
                "enabled_in_config": False,
            }
        )
    return pd.DataFrame(rows)


def parse_manual_stock_list(text: str) -> list[str]:
    items = [item.strip().upper() for item in text.replace("\n", ",").split(",") if item.strip()]
    result: list[str] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def analyze_stock_pool(config: PanelConfig, available_assets: list[str] | None = None) -> dict[str, Any]:
    available_assets = available_assets or get_available_assets()
    available_set = {asset.upper() for asset in available_assets}
    if config.stock_pool_mode == "manual":
        requested = parse_manual_stock_list(config.manual_stock_list)
    elif config.stock_pool_mode == "select":
        requested = [asset.upper() for asset in config.selected_assets]
    elif config.stock_pool_mode == "index":
        requested = []
    else:
        requested = available_assets

    invalid_format = [asset for asset in requested if not ASSET_PATTERN.match(asset)]
    format_valid = [asset for asset in requested if ASSET_PATTERN.match(asset)]
    valid_in_panel = [asset for asset in format_valid if asset in available_set]
    not_in_panel = [asset for asset in format_valid if asset not in available_set]
    warnings: list[str] = []
    if config.stock_pool_mode == "index":
        warnings.append("指数成分股模式当前仅为占位，运行时会退回到当前可用股票池。")

    runnable = True
    if config.stock_pool_mode in {"manual", "select"}:
        runnable = bool(valid_in_panel) and not invalid_format and not not_in_panel
    elif config.stock_pool_mode == "all":
        runnable = bool(available_assets)

    return {
        "mode": config.stock_pool_mode,
        "requested": requested,
        "valid_in_panel": valid_in_panel,
        "invalid_format": invalid_format,
        "not_in_panel": not_in_panel,
        "available_count": len(available_assets),
        "runnable": runnable,
        "warnings": warnings,
    }


def resolve_asset_whitelist(config: PanelConfig, available_assets: list[str]) -> tuple[list[str], list[str]]:
    analysis = analyze_stock_pool(config, available_assets)
    warnings = list(analysis["warnings"])
    if analysis["invalid_format"]:
        warnings.append(f"Invalid asset codes: {', '.join(analysis['invalid_format'])}")
    if analysis["not_in_panel"]:
        warnings.append(f"Assets not covered by the current data panel: {', '.join(analysis['not_in_panel'])}")
    if config.stock_pool_mode in {"all", "index"}:
        return available_assets, warnings
    return analysis["valid_in_panel"], warnings


def _filter_panel(df: pd.DataFrame, config: PanelConfig, whitelist: list[str]) -> pd.DataFrame:
    if df.empty:
        return df
    idx_dates = pd.to_datetime(df.index.get_level_values("trade_date"))
    idx_assets = df.index.get_level_values("asset").astype(str)
    mask = (idx_dates >= pd.Timestamp(config.start_date)) & (idx_dates <= pd.Timestamp(config.end_date))
    if whitelist:
        mask &= idx_assets.isin(whitelist)
    return df[mask].sort_index()


def _runtime_configs(config: PanelConfig) -> dict[str, Any]:
    settings = AppSettings.load()
    factor_cfg = deepcopy(settings.factors)
    catalog_names = get_factor_catalog()["name"].tolist()
    factor_cfg["factors"] = [{"name": name, "enabled": name in config.selected_factors} for name in catalog_names]

    strategy_cfg = deepcopy(settings.strategy)
    strategy_cfg.setdefault("strategy", {})
    strategy_cfg.setdefault("factors", {})
    strategy_cfg["strategy"]["rebalance"] = config.rebalance
    strategy_cfg["strategy"]["top_n"] = int(config.top_n)
    strategy_cfg["strategy"]["weighting"] = config.weighting
    strategy_cfg["strategy"]["allow_testing_factors"] = bool(config.allow_testing_factors)
    strategy_cfg["strategy"]["allow_review_factors"] = bool(config.allow_review_factors)
    strategy_cfg["factors"]["selected"] = list(config.selected_factors)
    strategy_cfg["factors"]["weights"] = {name: float(config.factor_weights.get(name, 0.0)) for name in config.selected_factors}
    strategy_cfg["factors"]["score_transform"] = config.score_transform
    strategy_cfg.setdefault("constraints", {})
    strategy_cfg["constraints"]["max_weight_per_asset"] = float(config.max_weight_per_asset)
    strategy_cfg["constraints"]["min_selected_assets"] = int(config.min_selected_assets)

    backtest_cfg = deepcopy(settings.backtest)
    backtest_cfg.setdefault("execution", {})
    backtest_cfg.setdefault("cost", {})
    backtest_cfg.setdefault("portfolio", {})
    backtest_cfg.setdefault("constraints", {})
    backtest_cfg["execution"]["price"] = config.execution_price
    backtest_cfg["execution"]["lot_size"] = int(config.lot_size)
    backtest_cfg["cost"]["commission"] = float(config.commission)
    backtest_cfg["cost"]["slippage"] = float(config.slippage)
    backtest_cfg["cost"]["stamp_tax_sell"] = float(config.stamp_tax_sell)
    backtest_cfg["portfolio"]["initial_capital"] = float(config.initial_capital)
    backtest_cfg["constraints"]["long_only"] = bool(config.long_only)

    data_cfg = deepcopy(settings.data)
    data_cfg["start_date"] = config.start_date
    data_cfg["end_date"] = config.end_date

    return {
        "data": data_cfg,
        "factors": factor_cfg,
        "strategy": strategy_cfg,
        "backtest": backtest_cfg,
        "report": deepcopy(settings.report),
    }


def _make_context(action: str, label: str) -> RunContext:
    return RunContext.create(run_id=generate_run_id(label or action))


def _save_configs(context: RunContext, runtime_configs: dict[str, Any]) -> None:
    config_dir = context.artifact_root / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    snapshot_paths: dict[str, str] = {}
    for name, payload in runtime_configs.items():
        path = config_dir / f"{name}.yaml"
        path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
        snapshot_paths[name] = str(path)
    context.config_snapshot = snapshot_paths


def _copy_outputs(context: RunContext) -> None:
    warehouse_targets = [
        "factor_panel.parquet",
        "factor_diagnostics.csv",
        "factor_metadata.csv",
        "factor_research_summary.csv",
        "factor_screening_summary.csv",
        "factor_correlation_matrix.csv",
        "high_correlation_pairs.csv",
        "target_positions.parquet",
        "strategy_diagnostics.csv",
        "daily_positions.parquet",
        "trades.parquet",
        "nav.parquet",
        "performance_summary.csv",
        "custom_factor_research_summary.csv",
    ]
    snapshot_dir = context.artifact_root / "warehouse_snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for name in warehouse_targets:
        src = WAREHOUSE_DIR / name
        if src.exists():
            dst = snapshot_dir / name
            dst.write_bytes(src.read_bytes())
            context.output_files.append(str(dst))

    for src in FIGURE_DIR.glob("*.png"):
        dst = context.artifact_root / "figures" / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        context.output_files.append(str(dst))

    for src in TABLE_DIR.glob("*.csv"):
        dst = context.artifact_root / "tables" / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        context.output_files.append(str(dst))

    html = HTML_DIR / "backtest_report.html"
    if html.exists():
        dst = context.artifact_root / "html" / html.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(html.read_bytes())
        context.output_files.append(str(dst))


def _finish(
    context: RunContext,
    runtime_configs: dict[str, Any],
    summary: dict[str, Any],
    warnings: list[str],
    error: str | None = None,
) -> ActionResult:
    context.warnings.extend(warnings)
    if error:
        context.errors.append(error)
        context.mark_finished("failed")
        status = "failed"
    else:
        perf_path = WAREHOUSE_DIR / "performance_summary.csv"
        if perf_path.exists():
            perf = read_dataframe(perf_path)
            if not perf.empty:
                message = str(perf.iloc[0].get("message", ""))
                trading_days = int(perf.iloc[0].get("trading_days", 0) or 0)
                if message == "short_sample" or trading_days < 20:
                    context.warnings.append("short_sample")
        _copy_outputs(context)
        context.mark_finished("success")
        status = "success"
    save_manifest(context, {"runtime_configs": runtime_configs, "summary": summary})
    return ActionResult(
        action=summary.get("action", ""),
        status=status,
        messages=summary.get("messages", []),
        warnings=warnings,
        run_id=context.run_id,
        artifact_root=context.artifact_root,
        summary={key: value for key, value in summary.items() if key != "messages"},
    )


def _prepare_market(config: PanelConfig) -> tuple[pd.DataFrame, list[str], list[str]]:
    market = _load_market_panel()
    whitelist, warnings = resolve_asset_whitelist(config, get_available_assets())
    if not whitelist:
        raise ValueError("The stock pool is empty after filtering. Check manual input or update the data coverage first.")
    filtered = _filter_panel(market, config, whitelist)
    if filtered.empty:
        raise ValueError("market_panel is empty after applying the selected date range and stock pool.")
    return filtered, whitelist, warnings


def _run_research_suite(market_panel: pd.DataFrame, factor_panel: pd.DataFrame) -> list[str]:
    rows: list[dict[str, Any]] = []
    for factor_name in factor_panel.columns:
        result = run_single_factor_research(
            market_panel=market_panel,
            factor_panel=factor_panel,
            factor_name=factor_name,
            output_dir=REPORT_DIR / "factor_research" / factor_name,
        )
        rows.append(result.summary)
    research = pd.DataFrame(rows)
    research.to_csv(WAREHOUSE_DIR / "factor_research_summary.csv", index=False, encoding="utf-8")
    corr, pairs = build_factor_correlation_report(factor_panel, threshold=0.8)
    corr.to_csv(WAREHOUSE_DIR / "factor_correlation_matrix.csv", encoding="utf-8")
    pairs.to_csv(WAREHOUSE_DIR / "high_correlation_pairs.csv", index=False, encoding="utf-8")
    diagnostics = read_dataframe(WAREHOUSE_DIR / "factor_diagnostics.csv")
    metadata = read_dataframe(WAREHOUSE_DIR / "factor_metadata.csv")
    screening = build_factor_screening_summary(
        diagnostics=diagnostics,
        research_summary=research,
        high_corr_pairs=pairs,
        metadata=metadata,
    )
    screening.to_csv(WAREHOUSE_DIR / "factor_screening_summary.csv", index=False, encoding="utf-8")
    return [
        f"单因子研究完成，因子数={len(research)}",
        f"因子相关性分析完成，矩阵 shape={corr.shape}",
        f"因子筛选完成，记录数={len(screening)}",
    ]


def _run_single_factor_only(market_panel: pd.DataFrame, factor_panel: pd.DataFrame) -> list[str]:
    rows: list[dict[str, Any]] = []
    for factor_name in factor_panel.columns:
        result = run_single_factor_research(
            market_panel=market_panel,
            factor_panel=factor_panel,
            factor_name=factor_name,
            output_dir=REPORT_DIR / "factor_research" / factor_name,
        )
        rows.append(result.summary)
    research = pd.DataFrame(rows)
    research.to_csv(WAREHOUSE_DIR / "factor_research_summary.csv", index=False, encoding="utf-8")
    return [f"单因子研究完成，因子数={len(research)}"]


def _run_screening_only() -> list[str]:
    factor_panel = _load_factor_panel()
    corr, pairs = build_factor_correlation_report(factor_panel, threshold=0.8)
    corr.to_csv(WAREHOUSE_DIR / "factor_correlation_matrix.csv", encoding="utf-8")
    pairs.to_csv(WAREHOUSE_DIR / "high_correlation_pairs.csv", index=False, encoding="utf-8")
    diagnostics = read_dataframe(WAREHOUSE_DIR / "factor_diagnostics.csv")
    metadata = read_dataframe(WAREHOUSE_DIR / "factor_metadata.csv")
    research = read_dataframe(WAREHOUSE_DIR / "factor_research_summary.csv")
    screening = build_factor_screening_summary(
        diagnostics=diagnostics,
        research_summary=research,
        high_corr_pairs=pairs,
        metadata=metadata,
    )
    screening.to_csv(WAREHOUSE_DIR / "factor_screening_summary.csv", index=False, encoding="utf-8")
    return [
        f"因子相关性分析完成，矩阵 shape={corr.shape}",
        f"因子筛选完成，记录数={len(screening)}",
    ]


def _safe_group(series: pd.Series):
    return series.groupby(level="asset", group_keys=False)


def evaluate_custom_factor_expression(market_panel: pd.DataFrame, factor_name: str, expression: str) -> pd.Series:
    if not expression.strip():
        raise ValueError("Custom factor expression cannot be empty.")

    def shift(series: pd.Series, periods: int) -> pd.Series:
        return _safe_group(series).shift(periods)

    def pct_change(series: pd.Series, periods: int = 1) -> pd.Series:
        return _safe_group(series).pct_change(periods)

    def rolling_mean(series: pd.Series, window: int) -> pd.Series:
        return _safe_group(series).rolling(window).mean().reset_index(level=0, drop=True)

    def rolling_std(series: pd.Series, window: int) -> pd.Series:
        return _safe_group(series).rolling(window).std().reset_index(level=0, drop=True)

    def rolling_corr(left: pd.Series, right: pd.Series, window: int) -> pd.Series:
        frame = pd.DataFrame({"left": left, "right": right})
        return (
            frame.groupby(level="asset")[["left", "right"]]
            .apply(lambda sub: sub["left"].rolling(window).corr(sub["right"]))
            .reset_index(level=0, drop=True)
        )

    def cs_rank(series: pd.Series) -> pd.Series:
        return series.groupby(level="trade_date").rank(pct=True)

    namespace: dict[str, Any] = {
        "np": np,
        "pd": pd,
        "abs": abs,
        "log": np.log,
        "shift": shift,
        "pct_change": pct_change,
        "rolling_mean": rolling_mean,
        "rolling_std": rolling_std,
        "rolling_corr": rolling_corr,
        "cs_rank": cs_rank,
    }
    for column in market_panel.columns:
        namespace[column] = market_panel[column]

    result = eval(expression, {"__builtins__": {}}, namespace)  # noqa: S307
    if not isinstance(result, pd.Series):
        raise ValueError("Custom factor expression must evaluate to a pandas Series.")
    result = result.replace([np.inf, -np.inf], np.nan)
    result = result.reindex(market_panel.index)
    result.name = factor_name
    return result


def parse_uploaded_custom_factor(upload_df: pd.DataFrame, factor_name: str) -> pd.Series:
    if upload_df.empty:
        raise ValueError("Uploaded custom factor file is empty.")
    frame = upload_df.copy()
    frame.columns = [str(column).strip() for column in frame.columns]
    required = {"trade_date", "asset"}
    if not required.issubset(frame.columns):
        raise ValueError("Uploaded factor CSV must contain trade_date and asset columns.")
    value_columns = [col for col in frame.columns if col not in {"trade_date", "asset"}]
    if not value_columns:
        raise ValueError("Uploaded factor CSV must contain one numeric factor value column.")
    value_column = value_columns[0]
    frame["trade_date"] = pd.to_datetime(frame["trade_date"])
    frame["asset"] = frame["asset"].astype(str).str.upper()
    series = frame.set_index(["trade_date", "asset"])[value_column]
    series.name = factor_name
    return series.sort_index().replace([np.inf, -np.inf], np.nan)


def _append_custom_factor_summary(summary: dict[str, Any]) -> None:
    path = WAREHOUSE_DIR / "custom_factor_research_summary.csv"
    incoming = pd.DataFrame([summary])
    if path.exists():
        existing = read_dataframe(path)
        existing = existing[existing["factor_name"] != summary["factor_name"]]
        merged = pd.concat([existing, incoming], ignore_index=True)
    else:
        merged = incoming
    merged.to_csv(path, index=False, encoding="utf-8")


def update_universe_config(asset_codes: list[str]) -> tuple[list[str], list[str]]:
    normalized = [asset.upper() for asset in asset_codes]
    invalid = [asset for asset in normalized if not ASSET_PATTERN.match(asset)]
    valid = [asset for asset in normalized if ASSET_PATTERN.match(asset)]
    if invalid:
        return [], invalid
    current = load_yaml_config(CONFIG_DIR / "data.yaml")
    universe = [str(asset).upper() for asset in current.get("universe", [])]
    merged = sorted(set(universe).union(valid))
    current["universe"] = merged
    (CONFIG_DIR / "data.yaml").write_text(
        yaml.safe_dump(current, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    added = [asset for asset in valid if asset not in universe]
    return added, []


def run_update_data(config: PanelConfig) -> ActionResult:
    _bootstrap()
    context = _make_context("update_data", config.run_label)
    runtime = _runtime_configs(config)
    _save_configs(context, runtime)
    try:
        source = HybridSource(
            enable_tushare=config.enable_tushare,
            enable_akshare_fallback=config.enable_akshare_fallback,
        )
        bundle = source.fetch_bundle(
            symbols=runtime["data"].get("universe", []),
            start_date=config.start_date.replace("-", ""),
            end_date=config.end_date.replace("-", ""),
        )
        write_dataframe(bundle.stock_basic, RAW_TUSHARE_DIR / "stock_basic.parquet")
        write_dataframe(bundle.trade_calendar, RAW_TUSHARE_DIR / "trade_cal.parquet")
        write_dataframe(bundle.daily, RAW_TUSHARE_DIR / "daily.parquet")
        write_dataframe(bundle.adj_factor, RAW_TUSHARE_DIR / "adj_factor.parquet")
        write_dataframe(bundle.daily_basic, RAW_TUSHARE_DIR / "daily_basic.parquet")
        if not bundle.daily.empty:
            write_dataframe(bundle.daily.iloc[0:0], RAW_AKSHARE_DIR / "daily.parquet")
        context.stage_statuses["update_data"] = "success"
        return _finish(context, runtime, {"action": "update_data", "messages": ["Raw data update completed."]}, [])
    except Exception as exc:  # noqa: BLE001
        context.stage_statuses["update_data"] = "failed"
        return _finish(context, runtime, {"action": "update_data", "messages": []}, [], str(exc))


def run_build_market_panel(config: PanelConfig) -> ActionResult:
    _bootstrap()
    context = _make_context("build_market_panel", config.run_label)
    runtime = _runtime_configs(config)
    _save_configs(context, runtime)
    try:
        market = build_market_panel(
            daily=read_dataframe(RAW_TUSHARE_DIR / "daily.parquet"),
            adj_factor=read_dataframe(RAW_TUSHARE_DIR / "adj_factor.parquet"),
            daily_basic=read_dataframe(RAW_TUSHARE_DIR / "daily_basic.parquet"),
        )
        write_dataframe(market, WAREHOUSE_DIR / "market_panel.parquet")
        context.stage_statuses["build_market_panel"] = "success"
        return _finish(
            context,
            runtime,
            {"action": "build_market_panel", "messages": [f"Market panel built successfully. shape={market.shape}"]},
            [],
        )
    except Exception as exc:  # noqa: BLE001
        context.stage_statuses["build_market_panel"] = "failed"
        return _finish(context, runtime, {"action": "build_market_panel", "messages": []}, [], str(exc))


def add_assets_to_universe_and_update(config: PanelConfig, asset_codes: list[str]) -> ActionResult:
    _bootstrap()
    context = _make_context("extend_universe", config.run_label)
    runtime = _runtime_configs(config)
    _save_configs(context, runtime)
    try:
        added, invalid = update_universe_config(asset_codes)
        if invalid:
            raise ValueError(f"Invalid asset code format: {', '.join(invalid)}")
        messages = (
            [f"Added assets to universe: {', '.join(added)}"]
            if added
            else ["No new assets were added. All requested assets already exist in universe."]
        )
        update_result = run_update_data(config)
        market_result = run_build_market_panel(config)
        warnings = list(update_result.warnings) + list(market_result.warnings)
        messages.extend(update_result.messages)
        messages.extend(market_result.messages)
        context.stage_statuses["extend_universe"] = "success"
        return _finish(
            context,
            _runtime_configs(config),
            {"action": "extend_universe", "messages": messages, "added_assets": added},
            warnings,
        )
    except Exception as exc:  # noqa: BLE001
        context.stage_statuses["extend_universe"] = "failed"
        return _finish(context, runtime, {"action": "extend_universe", "messages": []}, [], str(exc))


def run_build_factors(config: PanelConfig) -> ActionResult:
    _bootstrap()
    context = _make_context("build_factors", config.run_label)
    runtime = _runtime_configs(config)
    _save_configs(context, runtime)
    try:
        market, whitelist, warnings = _prepare_market(config)
        result = build_factor_panel(market, factor_config=runtime["factors"])
        write_dataframe(result.factor_panel, WAREHOUSE_DIR / "factor_panel.parquet")
        result.diagnostics.to_csv(WAREHOUSE_DIR / "factor_diagnostics.csv", index=False, encoding="utf-8")
        result.metadata.to_csv(WAREHOUSE_DIR / "factor_metadata.csv", index=False, encoding="utf-8")
        context.stage_statuses["build_factors"] = "success"
        return _finish(
            context,
            runtime,
            {"action": "build_factors", "messages": [f"Factor panel built successfully. shape={result.factor_panel.shape}"], "selected_factors": config.selected_factors, "asset_count": len(whitelist)},
            warnings,
        )
    except Exception as exc:  # noqa: BLE001
        context.stage_statuses["build_factors"] = "failed"
        return _finish(context, runtime, {"action": "build_factors", "messages": []}, [], str(exc))


def run_factor_research(config: PanelConfig) -> ActionResult:
    _bootstrap()
    context = _make_context("run_factor_research", config.run_label)
    runtime = _runtime_configs(config)
    _save_configs(context, runtime)
    try:
        market, whitelist, warnings = _prepare_market(config)
        factor_panel = _filter_panel(_load_factor_panel(), config, whitelist)
        if factor_panel.empty:
            raise ValueError("Filtered factor_panel is empty. Build factors first or adjust filters.")
        messages = _run_research_suite(market, factor_panel)
        context.stage_statuses["run_factor_research"] = "success"
        return _finish(context, runtime, {"action": "run_factor_research", "messages": messages, "selected_factors": list(factor_panel.columns), "asset_count": len(whitelist)}, warnings)
    except Exception as exc:  # noqa: BLE001
        context.stage_statuses["run_factor_research"] = "failed"
        return _finish(context, runtime, {"action": "run_factor_research", "messages": []}, [], str(exc))


def run_single_factor_analysis(config: PanelConfig) -> ActionResult:
    _bootstrap()
    context = _make_context("run_single_factor_analysis", config.run_label)
    runtime = _runtime_configs(config)
    _save_configs(context, runtime)
    try:
        market, whitelist, warnings = _prepare_market(config)
        factor_panel = _filter_panel(_load_factor_panel(), config, whitelist)
        if factor_panel.empty:
            raise ValueError("Filtered factor_panel is empty. Build factors first or adjust filters.")
        messages = _run_single_factor_only(market, factor_panel)
        context.stage_statuses["run_single_factor_analysis"] = "success"
        return _finish(context, runtime, {"action": "run_single_factor_analysis", "messages": messages, "selected_factors": list(factor_panel.columns), "asset_count": len(whitelist)}, warnings)
    except Exception as exc:  # noqa: BLE001
        context.stage_statuses["run_single_factor_analysis"] = "failed"
        return _finish(context, runtime, {"action": "run_single_factor_analysis", "messages": []}, [], str(exc))


def run_factor_screening(config: PanelConfig) -> ActionResult:
    _bootstrap()
    context = _make_context("run_factor_screening", config.run_label)
    runtime = _runtime_configs(config)
    _save_configs(context, runtime)
    try:
        messages = _run_screening_only()
        context.stage_statuses["run_factor_screening"] = "success"
        return _finish(context, runtime, {"action": "run_factor_screening", "messages": messages}, [])
    except Exception as exc:  # noqa: BLE001
        context.stage_statuses["run_factor_screening"] = "failed"
        return _finish(context, runtime, {"action": "run_factor_screening", "messages": []}, [], str(exc))


def run_strategy(config: PanelConfig) -> ActionResult:
    _bootstrap()
    context = _make_context("run_strategy", config.run_label)
    runtime = _runtime_configs(config)
    _save_configs(context, runtime)
    try:
        whitelist, warnings = resolve_asset_whitelist(config, get_available_assets())
        if not whitelist:
            raise ValueError("The stock pool is empty after filtering. Check the asset list or update data coverage first.")
        factor_panel = _filter_panel(_load_factor_panel(), config, whitelist)
        if factor_panel.empty:
            raise ValueError("Filtered factor_panel is empty. Build factors first or adjust filters.")
        result = build_signals(
            factor_panel=factor_panel,
            metadata=read_dataframe(WAREHOUSE_DIR / "factor_metadata.csv"),
            screening=read_dataframe(WAREHOUSE_DIR / "factor_screening_summary.csv") if (WAREHOUSE_DIR / "factor_screening_summary.csv").exists() else None,
            strategy_config=runtime["strategy"],
        )
        write_dataframe(result.target_positions, WAREHOUSE_DIR / "target_positions.parquet")
        result.diagnostics.to_csv(WAREHOUSE_DIR / "strategy_diagnostics.csv", index=False, encoding="utf-8")
        context.stage_statuses["run_strategy"] = "success"
        return _finish(context, runtime, {"action": "run_strategy", "messages": [f"Strategy finished successfully. target_positions shape={result.target_positions.shape}"], "selected_factors": result.selected_factors, "asset_count": len(whitelist)}, warnings)
    except Exception as exc:  # noqa: BLE001
        context.stage_statuses["run_strategy"] = "failed"
        return _finish(context, runtime, {"action": "run_strategy", "messages": []}, [], str(exc))


def run_backtest_step(config: PanelConfig) -> ActionResult:
    _bootstrap()
    context = _make_context("run_backtest", config.run_label)
    runtime = _runtime_configs(config)
    _save_configs(context, runtime)
    try:
        market, whitelist, warnings = _prepare_market(config)
        target = _filter_panel(_ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "target_positions.parquet")), config, whitelist)
        if target.empty:
            raise ValueError("Filtered target_positions is empty. Run strategy first for the selected stock pool.")
        result = run_backtest(market_panel=market, target_positions=target, backtest_config=runtime["backtest"])
        save_backtest_result(result, WAREHOUSE_DIR)
        context.stage_statuses["run_backtest"] = "success"
        perf = result.performance_summary.iloc[0].to_dict() if not result.performance_summary.empty else {}
        final_nav = float(result.nav["nav"].iloc[-1]) if not result.nav.empty else 0.0
        return _finish(context, runtime, {"action": "run_backtest", "messages": [f"Backtest finished successfully. final_nav={final_nav:.4f}"], "performance_summary": perf, "asset_count": len(whitelist)}, warnings)
    except Exception as exc:  # noqa: BLE001
        context.stage_statuses["run_backtest"] = "failed"
        return _finish(context, runtime, {"action": "run_backtest", "messages": []}, [], str(exc))


def run_generate_report(config: PanelConfig) -> ActionResult:
    _bootstrap()
    context = _make_context("build_report", config.run_label)
    runtime = _runtime_configs(config)
    _save_configs(context, runtime)
    try:
        result = export_report(runtime["report"])
        context.stage_statuses["build_report"] = "success"
        return _finish(context, runtime, {"action": "build_report", "messages": [f"Report generated successfully: {result['html_path']}"], "report_path": result["html_path"]}, result["inputs"].get("optional_skipped", []))
    except Exception as exc:  # noqa: BLE001
        context.stage_statuses["build_report"] = "failed"
        return _finish(context, runtime, {"action": "build_report", "messages": []}, [], str(exc))


def run_all(config: PanelConfig) -> ActionResult:
    _bootstrap()
    context = _make_context("pipeline", config.run_label)
    runtime = _runtime_configs(config)
    _save_configs(context, runtime)
    warnings: list[str] = []
    messages: list[str] = []
    try:
        market, whitelist, pool_warnings = _prepare_market(config)
        warnings.extend(pool_warnings)
        factor_result = build_factor_panel(market, factor_config=runtime["factors"])
        write_dataframe(factor_result.factor_panel, WAREHOUSE_DIR / "factor_panel.parquet")
        factor_result.diagnostics.to_csv(WAREHOUSE_DIR / "factor_diagnostics.csv", index=False, encoding="utf-8")
        factor_result.metadata.to_csv(WAREHOUSE_DIR / "factor_metadata.csv", index=False, encoding="utf-8")
        context.stage_statuses["build_factors"] = "success"
        messages.append(f"Factor panel built successfully. shape={factor_result.factor_panel.shape}")
        messages.extend(_run_research_suite(market, factor_result.factor_panel))
        context.stage_statuses["run_factor_research"] = "success"
        strategy_result = build_signals(
            factor_panel=factor_result.factor_panel,
            metadata=read_dataframe(WAREHOUSE_DIR / "factor_metadata.csv"),
            screening=read_dataframe(WAREHOUSE_DIR / "factor_screening_summary.csv"),
            strategy_config=runtime["strategy"],
        )
        write_dataframe(strategy_result.target_positions, WAREHOUSE_DIR / "target_positions.parquet")
        strategy_result.diagnostics.to_csv(WAREHOUSE_DIR / "strategy_diagnostics.csv", index=False, encoding="utf-8")
        context.stage_statuses["run_strategy"] = "success"
        messages.append(f"Strategy finished successfully. target_positions shape={strategy_result.target_positions.shape}")
        backtest_result = run_backtest(market_panel=market, target_positions=strategy_result.target_positions, backtest_config=runtime["backtest"])
        save_backtest_result(backtest_result, WAREHOUSE_DIR)
        context.stage_statuses["run_backtest"] = "success"
        final_nav = float(backtest_result.nav["nav"].iloc[-1]) if not backtest_result.nav.empty else 0.0
        messages.append(f"Backtest finished successfully. final_nav={final_nav:.4f}")
        report_result = export_report(runtime["report"])
        context.stage_statuses["build_report"] = "success"
        messages.append(f"Report generated successfully: {report_result['html_path']}")
        perf = backtest_result.performance_summary.iloc[0].to_dict() if not backtest_result.performance_summary.empty else {}
        return _finish(context, runtime, {"action": "pipeline", "messages": messages, "selected_factors": strategy_result.selected_factors, "asset_count": len(whitelist), "performance_summary": perf, "report_path": report_result["html_path"]}, warnings)
    except Exception as exc:  # noqa: BLE001
        return _finish(context, runtime, {"action": "pipeline", "messages": messages}, warnings, str(exc))


def run_custom_factor_experiment(config: PanelConfig, *, factor_name: str, expression: str = "", uploaded_factor_df: pd.DataFrame | None = None) -> ActionResult:
    _bootstrap()
    context = _make_context("custom_factor_experiment", config.run_label)
    runtime = _runtime_configs(config)
    _save_configs(context, runtime)
    try:
        market, whitelist, warnings = _prepare_market(config)
        if uploaded_factor_df is not None:
            factor_series = parse_uploaded_custom_factor(uploaded_factor_df, factor_name=factor_name)
        else:
            factor_series = evaluate_custom_factor_expression(market, factor_name=factor_name, expression=expression)
        factor_series = factor_series.reindex(market.index)
        factor_panel = pd.DataFrame({factor_name: factor_series})
        output_dir = REPORT_DIR / "factor_research" / "custom" / factor_name
        result = run_single_factor_research(market_panel=market, factor_panel=factor_panel, factor_name=factor_name, output_dir=output_dir)
        _append_custom_factor_summary(result.summary)
        write_json(result.summary, output_dir / "summary.json")
        context.stage_statuses["custom_factor_experiment"] = "success"
        return _finish(context, runtime, {"action": "custom_factor_experiment", "messages": [f"Custom factor experiment finished: {factor_name}"], "factor_name": factor_name, "asset_count": len(whitelist), "research_summary": result.summary}, warnings)
    except Exception as exc:  # noqa: BLE001
        context.stage_statuses["custom_factor_experiment"] = "failed"
        return _finish(context, runtime, {"action": "custom_factor_experiment", "messages": []}, [], str(exc))


def artifact_status() -> dict[str, Path]:
    return {
        "factor_panel.parquet": WAREHOUSE_DIR / "factor_panel.parquet",
        "factor_screening_summary.csv": WAREHOUSE_DIR / "factor_screening_summary.csv",
        "target_positions.parquet": WAREHOUSE_DIR / "target_positions.parquet",
        "nav.parquet": WAREHOUSE_DIR / "nav.parquet",
        "performance_summary.csv": WAREHOUSE_DIR / "performance_summary.csv",
        "backtest_report.html": HTML_DIR / "backtest_report.html",
        "nav_curve.png": FIGURE_DIR / "nav_curve.png",
        "custom_factor_research_summary.csv": WAREHOUSE_DIR / "custom_factor_research_summary.csv",
    }


def latest_result_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {"performance_summary": pd.DataFrame(), "latest_positions": pd.DataFrame(), "report_path": str(HTML_DIR / "backtest_report.html") if (HTML_DIR / "backtest_report.html").exists() else ""}
    if (WAREHOUSE_DIR / "performance_summary.csv").exists():
        snapshot["performance_summary"] = read_dataframe(WAREHOUSE_DIR / "performance_summary.csv")
    if (WAREHOUSE_DIR / "daily_positions.parquet").exists():
        positions = _ensure_panel_index(read_dataframe(WAREHOUSE_DIR / "daily_positions.parquet"))
        if not positions.empty:
            latest_date = positions.index.get_level_values("trade_date").max()
            snapshot["latest_positions"] = positions.xs(latest_date, level="trade_date").reset_index().head(20)
    if (WAREHOUSE_DIR / "custom_factor_research_summary.csv").exists():
        snapshot["custom_factor_research_summary"] = read_dataframe(WAREHOUSE_DIR / "custom_factor_research_summary.csv")
    return snapshot


def current_runtime_preview(config: PanelConfig) -> dict[str, Any]:
    analysis = analyze_stock_pool(config, get_available_assets())
    return {
        "run_label": config.run_label,
        "date_range": {"start": config.start_date, "end": config.end_date},
        "stock_pool_mode": config.stock_pool_mode,
        "requested_assets": analysis["requested"],
        "selected_asset_count": len(analysis["valid_in_panel"]),
        "valid_assets": analysis["valid_in_panel"][:20],
        "invalid_format": analysis["invalid_format"],
        "not_in_panel": analysis["not_in_panel"],
        "selected_factors": config.selected_factors,
        "factor_weights": {name: config.factor_weights.get(name, 0.0) for name in config.selected_factors},
        "strategy": {"rebalance": config.rebalance, "top_n": config.top_n, "weighting": config.weighting, "score_transform": config.score_transform, "allow_testing_factors": config.allow_testing_factors, "allow_review_factors": config.allow_review_factors},
        "strategy_constraints": {"max_weight_per_asset": config.max_weight_per_asset, "min_selected_assets": config.min_selected_assets},
        "backtest": {"initial_capital": config.initial_capital, "execution_price": config.execution_price, "commission": config.commission, "slippage": config.slippage, "stamp_tax_sell": config.stamp_tax_sell, "lot_size": config.lot_size, "long_only": config.long_only},
        "warnings": analysis["warnings"],
    }
