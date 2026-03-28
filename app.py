"""Streamlit quant experiment control panel."""

from __future__ import annotations

import os
import sys
from datetime import date
from io import StringIO
from typing import Callable

import pandas as pd
import streamlit as st

from quant_lab.control_panel import (
    ActionResult,
    PanelConfig,
    add_assets_to_universe_and_update,
    analyze_stock_pool,
    artifact_status,
    current_runtime_preview,
    get_available_assets,
    get_configured_universe,
    get_factor_catalog,
    latest_result_snapshot,
    run_all,
    run_backtest_step,
    run_build_factors,
    run_custom_factor_experiment,
    run_factor_screening,
    run_generate_report,
    run_single_factor_analysis,
    run_strategy,
)

FIXED_PYTHON = r"D:\anaconda\envs\alpha_lab\python.exe"
STATUS_IDLE = "未运行"

STATUS_LABELS = {
    "active": "活跃",
    "testing": "测试中",
    "deprecated": "待弃用",
    "draft": "草稿",
    "archived": "已归档",
}

FACTOR_STATUS_MEANINGS = {
    "活跃": "默认可进入正式实验和策略打分。",
    "测试中": "允许研究，但默认不直接进入正式策略。",
    "待弃用": "保留代码和历史研究，不建议再纳入新实验。",
    "草稿": "还在定义或验证阶段，通常只用于开发测试。",
    "已归档": "仅保留历史参考，不再参与新实验。",
}

FACTOR_DIRECTION_MEANINGS = {
    "higher_is_better": "值越大通常越偏正向。",
    "lower_is_better": "值越小通常越偏正向。",
    "explicit_sign": "方向依赖具体经济含义，需要单独判断。",
}

DISPLAY_COLUMN_MAP = {
    "factor_name": "因子名",
    "group": "分组",
    "category": "分类",
    "status": "状态",
    "description": "说明",
    "required_columns": "依赖字段",
    "direction": "方向",
    "name": "名称",
    "trade_date": "交易日期",
    "asset": "资产代码",
    "weight": "权重",
    "shares": "股数",
    "close": "收盘价",
    "market_value": "市值",
    "target_weight": "目标权重",
    "score": "综合得分",
    "rank": "排序",
    "selected_by_strategy": "是否入选",
    "factor_count_used": "使用因子数",
    "total_return": "总收益",
    "annualized_return": "年化收益",
    "annualized_volatility": "年化波动",
    "sharpe": "夏普",
    "max_drawdown": "最大回撤",
    "avg_turnover": "平均换手",
    "win_rate": "胜率",
    "trading_days": "交易日数",
    "message": "备注",
    "horizon": "预测周期",
    "rank_ic_mean": "RankIC均值",
    "rank_ic_std": "RankIC波动",
    "icir": "ICIR",
    "valid_rank_ic_dates": "有效IC日期数",
    "quantile_dates": "分层日期数",
    "long_short_mean": "多空均值",
    "research_status": "研究状态",
}

MESSAGE_MAP = {
    "short_sample": "样本过短，仅供结构验证",
    "ok": "正常",
    "empty_nav": "净值为空",
    "failed_all_nan": "因子全为空或无有效横截面",
    "insufficient_sample": "样本不足",
    "weak": "预测性偏弱",
    "valid": "研究结果有效",
}


def init_state() -> None:
    defaults = {
        "logs": [],
        "status": STATUS_IDLE,
        "last_run": {},
        "run_label": "panel_run",
        "start_date": date(2024, 1, 1),
        "end_date": date(2025, 12, 31),
        "stock_pool_mode": "all",
        "manual_stock_list": "",
        "selected_assets": [],
        "top_n": 30,
        "rebalance": "daily",
        "weighting": "equal",
        "score_transform": "none",
        "max_weight_per_asset": 0.05,
        "min_selected_assets": 5,
        "allow_testing_factors": False,
        "allow_review_factors": True,
        "initial_capital": 1_000_000.0,
        "execution_price": "next_open",
        "commission": 0.0003,
        "slippage": 0.0005,
        "stamp_tax_sell": 0.001,
        "lot_size": 100,
        "long_only": True,
        "enable_tushare": True,
        "enable_akshare_fallback": True,
        "custom_factor_name": "custom_factor_v1",
        "custom_factor_mode": "表达式",
        "custom_factor_expression": "(close_adj / shift(close_adj, 20)) - 1",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    catalog = get_factor_catalog()
    enabled_mask = catalog["enabled_in_config"] if "enabled_in_config" in catalog.columns else pd.Series(False, index=catalog.index)
    selected = catalog.loc[enabled_mask.fillna(False), "name"].tolist() if not catalog.empty else []
    st.session_state.setdefault("selected_factors", selected)
    for factor_name in st.session_state["selected_factors"]:
        st.session_state.setdefault(f"weight_{factor_name}", 0.0)


def append_log(message: str) -> None:
    st.session_state["logs"].append(message)


def translate_message(text: str) -> str:
    result = text
    for src, dst in MESSAGE_MAP.items():
        result = result.replace(src, dst)
    return result


def to_display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    output = frame.copy()
    output.columns = [DISPLAY_COLUMN_MAP.get(str(col), str(col)) for col in output.columns]
    for column in output.columns:
        if "状态" in str(column) or column == "备注":
            output[column] = output[column].astype(str).map(lambda value: MESSAGE_MAP.get(value, STATUS_LABELS.get(value, value)))
    return output


def build_panel_config() -> PanelConfig:
    selected_factors = list(st.session_state["selected_factors"])
    weights = {name: float(st.session_state.get(f"weight_{name}", 0.0)) for name in selected_factors}
    return PanelConfig(
        start_date=str(st.session_state["start_date"]),
        end_date=str(st.session_state["end_date"]),
        stock_pool_mode=str(st.session_state["stock_pool_mode"]),
        manual_stock_list=str(st.session_state["manual_stock_list"]),
        selected_assets=list(st.session_state["selected_assets"]),
        selected_factors=selected_factors,
        factor_weights=weights,
        top_n=int(st.session_state["top_n"]),
        rebalance=str(st.session_state["rebalance"]),
        weighting=str(st.session_state["weighting"]),
        score_transform=str(st.session_state["score_transform"]),
        max_weight_per_asset=float(st.session_state["max_weight_per_asset"]),
        min_selected_assets=int(st.session_state["min_selected_assets"]),
        allow_testing_factors=bool(st.session_state["allow_testing_factors"]),
        allow_review_factors=bool(st.session_state["allow_review_factors"]),
        initial_capital=float(st.session_state["initial_capital"]),
        execution_price=str(st.session_state["execution_price"]),
        commission=float(st.session_state["commission"]),
        slippage=float(st.session_state["slippage"]),
        stamp_tax_sell=float(st.session_state["stamp_tax_sell"]),
        lot_size=int(st.session_state["lot_size"]),
        long_only=bool(st.session_state["long_only"]),
        enable_tushare=bool(st.session_state["enable_tushare"]),
        enable_akshare_fallback=bool(st.session_state["enable_akshare_fallback"]),
        run_label=str(st.session_state["run_label"]).strip() or "panel_run",
    )


def validate_config(config: PanelConfig) -> None:
    if config.top_n <= 0:
        raise ValueError("top_n 必须大于 0。")
    if not config.selected_factors:
        raise ValueError("至少需要选择 1 个因子。")
    if config.max_weight_per_asset <= 0:
        raise ValueError("单票最大权重必须大于 0。")
    if config.min_selected_assets <= 0:
        raise ValueError("最小入选股票数必须大于 0。")
    for weight in config.factor_weights.values():
        float(weight)
    if config.stock_pool_mode == "manual" and not config.manual_stock_list.strip():
        raise ValueError("手动股票列表不能为空。")
    if config.stock_pool_mode == "select" and not config.selected_assets:
        raise ValueError("多选股票池模式下至少需要选择 1 只股票。")


def handle_result(label: str, result: ActionResult) -> None:
    for message in result.messages:
        append_log(f"[成功] {translate_message(message)}")
    for warning in result.warnings:
        append_log(f"[警告] {translate_message(warning)}")
    st.session_state["status"] = f"{'成功' if result.status == 'success' else '失败'}: {label}"
    st.session_state["last_run"] = {
        "动作": label,
        "run_id": result.run_id,
        "artifact_root": str(result.artifact_root),
        "summary": result.summary,
        "warnings": result.warnings,
        "status": result.status,
    }


def execute_action(label: str, action: Callable[[PanelConfig], ActionResult]) -> None:
    try:
        config = build_panel_config()
        validate_config(config)
        st.session_state["status"] = f"运行中: {label}"
        append_log(f"[开始] {label}")
        result = action(config)
        handle_result(label, result)
    except Exception as exc:  # noqa: BLE001
        append_log(f"[失败] {label}: {exc}")
        st.session_state["status"] = f"失败: {label}"


def render_data_section(available_assets: list[str]) -> dict[str, object]:
    config = build_panel_config()
    analysis = analyze_stock_pool(config, available_assets)
    configured_universe = get_configured_universe()

    with st.expander("一、数据与股票池配置", expanded=True):
        row = st.columns(3)
        row[0].date_input("起始日期", key="start_date")
        row[1].date_input("结束日期", key="end_date")
        row[2].text_input("运行标签", key="run_label")

        mode_map = {
            "全部可用股票": "all",
            "手动输入股票列表": "manual",
            "从现有资产中多选": "select",
            "指数成分股模式（占位）": "index",
        }
        labels = list(mode_map.keys())
        values = list(mode_map.values())
        selected_label = st.selectbox("股票池模式", options=labels, index=values.index(st.session_state["stock_pool_mode"]))
        st.session_state["stock_pool_mode"] = mode_map[selected_label]

        if st.session_state["stock_pool_mode"] == "manual":
            st.text_area(
                "手动股票列表",
                key="manual_stock_list",
                placeholder="000001.SZ, 000002.SZ, 600000.SH",
                help="支持逗号或换行分隔。面板会立即检查代码格式和当前数据是否覆盖。",
            )
        elif st.session_state["stock_pool_mode"] == "select":
            st.multiselect("从当前可用资产中选择", options=available_assets, key="selected_assets")
        elif st.session_state["stock_pool_mode"] == "index":
            st.info("指数成分股模式当前仅为占位，运行时会退回到当前可用股票池。")

        config = build_panel_config()
        analysis = analyze_stock_pool(config, available_assets)
        st.caption(f"当前面板可用资产数: {len(available_assets)}")
        st.caption(f"当前 data.yaml universe 数量: {len(configured_universe)}")

        if config.stock_pool_mode == "manual":
            col1, col2, col3 = st.columns(3)
            col1.markdown("**有效代码**")
            col1.write(", ".join(analysis["valid_in_panel"]) or "无")
            col2.markdown("**无效代码**")
            col2.write(", ".join(analysis["invalid_format"]) or "无")
            col3.markdown("**未覆盖代码**")
            col3.write(", ".join(analysis["not_in_panel"]) or "无")

            if analysis["invalid_format"]:
                st.error("存在格式无效的股票代码，已禁用策略 / 回测 / 全流程运行按钮。")
            elif analysis["not_in_panel"]:
                st.warning("存在数据尚未覆盖的股票代码。可先加入 universe 并刷新数据。")
            else:
                st.success("当前手动股票列表可直接进入策略与回测。")

            if analysis["not_in_panel"] and st.button("加入 universe 并刷新数据", use_container_width=True):
                execute_action("加入 universe 并刷新数据", lambda cfg: add_assets_to_universe_and_update(cfg, analysis["not_in_panel"]))

    return analysis


def render_factor_section(catalog: pd.DataFrame) -> None:
    with st.expander("二、因子配置", expanded=True):
        st.markdown("**因子是什么**：因子是从市场数据里抽取出来、用于描述股票特征的研究信号，比如估值、动量、波动率、流动性。")
        st.markdown("**状态说明**：")
        for label, meaning in FACTOR_STATUS_MEANINGS.items():
            st.write(f"- `{label}`：{meaning}")
        st.markdown("**方向说明**：")
        for code, meaning in FACTOR_DIRECTION_MEANINGS.items():
            st.write(f"- `{code}`：{meaning}")

        display = catalog.copy()
        if "status" in display.columns:
            display["status"] = display["status"].map(lambda value: STATUS_LABELS.get(str(value), str(value)))
        if "direction" in display.columns:
            display["direction"] = display["direction"].map(lambda value: FACTOR_DIRECTION_MEANINGS.get(str(value), str(value)))
        display_cols = [name for name in ["name", "status", "group", "category", "direction", "description"] if name in display.columns]
        if display_cols:
            st.dataframe(to_display_frame(display[display_cols]), use_container_width=True, hide_index=True)

        options = catalog["name"].tolist() if not catalog.empty else []
        st.multiselect("启用因子", options=options, key="selected_factors")
        st.write(f"当前选中因子数量: {len(st.session_state['selected_factors'])}")
        st.checkbox("允许使用测试中因子", key="allow_testing_factors")
        st.checkbox("允许使用需复核因子", key="allow_review_factors")

        if st.session_state["selected_factors"]:
            st.markdown("**因子权重**")
            cols = st.columns(2)
            for idx, factor_name in enumerate(st.session_state["selected_factors"]):
                st.session_state.setdefault(f"weight_{factor_name}", 0.0)
                cols[idx % 2].number_input(f"{factor_name} 权重", key=f"weight_{factor_name}", step=0.1, format="%.4f")


def render_strategy_section() -> None:
    with st.expander("三、策略配置", expanded=True):
        st.markdown("**当前策略口径**：多因子线性加权打分，按排名选前 `N` 只股票，long-only，等权持仓。")
        row = st.columns(4)
        row[0].text_input("策略名称", value="ranking_v1", disabled=True)
        row[1].selectbox("调仓频率", options=["daily", "weekly"], key="rebalance")
        row[2].number_input("top_n", min_value=1, max_value=500, key="top_n")
        row[3].selectbox("权重方式", options=["equal"], key="weighting")
        row2 = st.columns(3)
        row2[0].selectbox("评分变换", options=["none", "rank", "zscore"], key="score_transform")
        row2[1].number_input("单票最大权重", min_value=0.001, max_value=1.0, step=0.01, format="%.3f", key="max_weight_per_asset")
        row2[2].number_input("最少入选股票数", min_value=1, max_value=500, step=1, key="min_selected_assets")
        st.caption("说明：单票最大权重和最少入选股票数会直接进入本次策略运行配置。")


def render_backtest_section() -> None:
    with st.expander("四、回测配置", expanded=True):
        st.markdown("**当前回测口径**：信号在当日收盘后已知，下一交易日 `next_open` 执行，A 股现货 long-only。")
        row = st.columns(3)
        row[0].number_input("初始资金", key="initial_capital", min_value=10000.0, step=10000.0)
        row[1].selectbox("执行价格口径", options=["next_open"], key="execution_price")
        row[2].number_input("最小交易单位 lot_size", key="lot_size", min_value=1, step=1)
        row2 = st.columns(3)
        row2[0].number_input("佣金 commission", key="commission", min_value=0.0, max_value=0.01, step=0.0001, format="%.4f")
        row2[1].number_input("滑点 slippage", key="slippage", min_value=0.0, max_value=0.01, step=0.0001, format="%.4f")
        row2[2].number_input("卖出印花税 stamp_tax_sell", key="stamp_tax_sell", min_value=0.0, max_value=0.02, step=0.0001, format="%.4f")
        st.checkbox("A股长仓限制（long_only）", key="long_only", disabled=True)
        st.info("当前更接近 A 股研究环境的配置包括：100 股整数 lot、卖出印花税、买卖佣金、滑点、初始资金。")
        st.warning("当前仍未建模：停牌、涨跌停、成交量约束、真实撮合深度。")


def render_custom_factor_section() -> None:
    with st.expander("五、自定义因子实验区", expanded=False):
        st.markdown("**用途**：这里用于快速测试你自己的因子，不会自动注册进主因子库。")
        st.markdown("**两种方式**：")
        st.write("- 表达式：直接基于现有 `market_panel` 列计算。")
        st.write("- CSV 上传：上传你自己准备好的因子值文件。")
        st.markdown("**表达式可用字段示例**：`close_adj`, `turnover_rate`, `volume`, `pb`, `pe`, `total_mv`。")
        st.markdown("**表达式 helper**：`shift`, `pct_change`, `rolling_mean`, `rolling_std`, `rolling_corr`, `cs_rank`, `log`, `abs`。")
        st.markdown("**CSV 格式要求**：必须包含 `trade_date`, `asset`，以及一列因子值。")
        st.text_input("自定义因子名", key="custom_factor_name")
        st.selectbox("因子来源", options=["表达式", "上传CSV"], key="custom_factor_mode")
        upload_df: pd.DataFrame | None = None
        if st.session_state["custom_factor_mode"] == "表达式":
            st.text_area(
                "表达式",
                key="custom_factor_expression",
                height=120,
                help="示例： (close_adj / shift(close_adj, 20)) - 1",
            )
        else:
            uploaded = st.file_uploader("上传自定义因子 CSV", type=["csv"])
            if uploaded is not None:
                upload_df = pd.read_csv(StringIO(uploaded.getvalue().decode("utf-8")))
                st.dataframe(upload_df.head(10), use_container_width=True, hide_index=True)
        if st.button("测试自定义因子", use_container_width=True):
            factor_name = st.session_state["custom_factor_name"].strip()
            if not factor_name:
                append_log("[失败] 测试自定义因子：因子名不能为空。")
                st.session_state["status"] = "失败: 测试自定义因子"
            else:
                execute_action(
                    "测试自定义因子",
                    lambda cfg: run_custom_factor_experiment(
                        cfg,
                        factor_name=factor_name,
                        expression=st.session_state["custom_factor_expression"],
                        uploaded_factor_df=upload_df if st.session_state["custom_factor_mode"] == "上传CSV" else None,
                    ),
                )


def render_run_section(stock_analysis: dict[str, object]) -> None:
    disable_pool_dependent = bool(stock_analysis["invalid_format"] or stock_analysis["not_in_panel"])
    st.subheader("六、运行控制")
    row1 = st.columns(4)
    with row1[0]:
        if st.button("构建因子", use_container_width=True):
            execute_action("构建因子", run_build_factors)
    with row1[1]:
        if st.button("运行单因子研究", use_container_width=True):
            execute_action("运行单因子研究", run_single_factor_analysis)
    with row1[2]:
        if st.button("运行因子筛选", use_container_width=True):
            execute_action("运行因子筛选", run_factor_screening)
    with row1[3]:
        if st.button("运行策略", disabled=disable_pool_dependent, use_container_width=True):
            execute_action("运行策略", run_strategy)

    row2 = st.columns(3)
    with row2[0]:
        if st.button("运行回测", disabled=disable_pool_dependent, use_container_width=True):
            execute_action("运行回测", run_backtest_step)
    with row2[1]:
        if st.button("生成报告", use_container_width=True):
            execute_action("生成报告", run_generate_report)
    with row2[2]:
        if st.button("全流程运行", type="primary", disabled=disable_pool_dependent, use_container_width=True):
            execute_action("全流程运行", run_all)


def render_status_and_results(config: PanelConfig) -> None:
    preview = current_runtime_preview(config)
    snapshot = latest_result_snapshot()
    last_run = st.session_state.get("last_run", {})

    left, right = st.columns([1.2, 1.0])
    with left:
        st.subheader("七、运行状态与日志")
        st.info(st.session_state["status"])
        st.text_area("运行日志", value="\n".join(st.session_state["logs"]), height=260)
        if last_run:
            st.json(last_run, expanded=False)

    with right:
        st.subheader("八、本次运行配置预览")
        st.json(preview, expanded=False)

    st.subheader("九、关键结果")
    summary_cols = st.columns(4)
    summary_cols[0].metric("因子数量", len(config.selected_factors))
    summary_cols[1].metric("股票池模式", {"all": "全部", "manual": "手动", "select": "多选", "index": "指数占位"}.get(preview["stock_pool_mode"], preview["stock_pool_mode"]))
    summary_cols[2].metric("股票数量", preview["selected_asset_count"])
    summary_cols[3].metric("报告状态", "已生成" if artifact_status()["backtest_report.html"].exists() else "未生成")

    artifact_col, result_col = st.columns(2)
    with artifact_col:
        st.markdown("**主要产物文件**")
        for name, path in artifact_status().items():
            st.write(f"{DISPLAY_COLUMN_MAP.get(name, name)}: {'存在' if path.exists() else '缺失'}")
        if last_run.get("artifact_root"):
            st.code(f"runs 路径: {last_run['artifact_root']}")
        if snapshot.get("report_path"):
            st.code(f"报告路径: {snapshot['report_path']}")

    with result_col:
        st.markdown("**回测摘要**")
        perf = snapshot.get("performance_summary", pd.DataFrame())
        if isinstance(perf, pd.DataFrame) and not perf.empty:
            st.dataframe(to_display_frame(perf), use_container_width=True, hide_index=True)
        latest_pos = snapshot.get("latest_positions", pd.DataFrame())
        if isinstance(latest_pos, pd.DataFrame) and not latest_pos.empty:
            st.markdown("**最新持仓预览**")
            st.dataframe(to_display_frame(latest_pos), use_container_width=True, hide_index=True)
        custom_summary = snapshot.get("custom_factor_research_summary", pd.DataFrame())
        if isinstance(custom_summary, pd.DataFrame) and not custom_summary.empty:
            st.markdown("**自定义因子研究摘要**")
            st.dataframe(to_display_frame(custom_summary.tail(5)), use_container_width=True, hide_index=True)

    nav_image = artifact_status()["nav_curve.png"]
    if nav_image.exists():
        st.subheader("十、NAV 预览")
        st.image(str(nav_image), caption="净值曲线", use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="Quant Lab 量化实验控制台", layout="wide")
    init_state()

    st.title("Quant Lab 量化实验控制台")
    st.caption("面板里的修改默认只对本次运行生效，不会自动覆盖仓库 YAML 配置。")

    env_col1, env_col2 = st.columns(2)
    env_col1.code(f"Python executable: {sys.executable}")
    env_col2.code(f"Python version: {sys.version}")

    if sys.executable.lower() != FIXED_PYTHON.lower():
        st.error(f"当前解释器与项目固定解释器不一致: {FIXED_PYTHON}")
    else:
        st.success("当前解释器与项目固定解释器一致。")

    if not os.getenv("TUSHARE_TOKEN"):
        st.warning("未检测到 TUSHARE_TOKEN。面板仍可运行，但真实 TuShare 数据链路尚未完全验证。")

    available_assets = get_available_assets()
    catalog = get_factor_catalog()
    stock_analysis = render_data_section(available_assets)
    render_factor_section(catalog)
    render_strategy_section()
    render_backtest_section()
    render_custom_factor_section()
    render_run_section(stock_analysis)
    render_status_and_results(build_panel_config())


if __name__ == "__main__":
    main()
