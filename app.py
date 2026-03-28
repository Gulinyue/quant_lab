"""Single-page Streamlit control panel for Quant Lab."""

from __future__ import annotations

import os
import sys
from datetime import date

import streamlit as st

from quant_lab.control_panel import (
    PanelConfig,
    artifact_status,
    run_all,
    run_backtest_step,
    run_build_factors,
    run_build_market_panel,
    run_generate_report,
    run_strategy,
    run_update_data,
)

FIXED_PYTHON = r"D:\anaconda\envs\alpha_lab\python.exe"


def init_state() -> None:
    """Initialize session state defaults."""
    defaults = {
        "logs": [],
        "status": "Idle",
        "start_date": date(2024, 1, 1),
        "end_date": date(2025, 12, 31),
        "top_n": 3,
        "rebalance_every": 5,
        "commission": 0.0003,
        "slippage": 0.0005,
        "enable_tushare": True,
        "enable_akshare_fallback": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def append_log(message: str) -> None:
    """Append a message to the session log."""
    st.session_state["logs"].append(message)


def build_config() -> PanelConfig:
    """Build runtime config from sidebar controls."""
    return PanelConfig(
        start_date=str(st.session_state["start_date"]),
        end_date=str(st.session_state["end_date"]),
        top_n=int(st.session_state["top_n"]),
        rebalance_every=int(st.session_state["rebalance_every"]),
        commission=float(st.session_state["commission"]),
        slippage=float(st.session_state["slippage"]),
        enable_tushare=bool(st.session_state["enable_tushare"]),
        enable_akshare_fallback=bool(st.session_state["enable_akshare_fallback"]),
    )


def execute_step(label: str, runner) -> None:
    """Execute a step with UI-safe status handling."""
    try:
        st.session_state["status"] = f"Running: {label}"
        result = runner()
        if isinstance(result, list):
            for item in result:
                append_log(f"[OK] {item}")
        else:
            append_log(f"[OK] {result}")
        st.session_state["status"] = f"Done: {label}"
    except Exception as exc:
        append_log(f"[ERROR] {label}: {exc}")
        st.session_state["status"] = f"Failed: {label}"


def main() -> None:
    """Render the Streamlit control panel."""
    st.set_page_config(page_title="Quant Lab Control Panel", layout="wide")
    init_state()

    with st.sidebar:
        st.header("Run Config")
        st.date_input("Start Date", key="start_date", value=date(2024, 1, 1))
        st.date_input("End Date", key="end_date", value=date(2025, 12, 31))
        st.number_input("top_n", key="top_n", min_value=1, max_value=100, value=3, step=1)
        st.number_input("Rebalance Frequency", key="rebalance_every", min_value=1, max_value=60, value=5, step=1)
        st.number_input("commission", key="commission", min_value=0.0, max_value=0.01, value=0.0003, step=0.0001, format="%.4f")
        st.number_input("slippage", key="slippage", min_value=0.0, max_value=0.01, value=0.0005, step=0.0001, format="%.4f")
        st.checkbox("Enable TuShare", key="enable_tushare", value=True)
        st.checkbox("Enable AkShare Fallback", key="enable_akshare_fallback", value=True)

    st.title("Quant Lab Control Panel")

    env_col1, env_col2 = st.columns(2)
    env_col1.code(f"Python executable: {sys.executable}")
    env_col2.code(f"Python version: {sys.version}")

    if sys.executable.lower() != FIXED_PYTHON.lower():
        st.error(f"Current interpreter does not match the required interpreter: {FIXED_PYTHON}")
    else:
        st.success("Current interpreter matches the fixed project interpreter.")

    if not os.getenv("TUSHARE_TOKEN"):
        st.warning(
            "TUSHARE_TOKEN is missing. Data update will fall back to sample data, so the panel stays usable but the real TuShare chain is not verified."
        )

    config = build_config()

    row1 = st.columns(3)
    with row1[0]:
        if st.button("更新数据", width="stretch"):
            execute_step("Update Data", lambda: run_update_data(config))
    with row1[1]:
        if st.button("构建市场面板", width="stretch"):
            execute_step("Build Market Panel", run_build_market_panel)
    with row1[2]:
        if st.button("构建因子", width="stretch"):
            execute_step("Build Factors", run_build_factors)

    row2 = st.columns(3)
    with row2[0]:
        if st.button("运行策略", width="stretch"):
            execute_step("Run Strategy", lambda: run_strategy(config))
    with row2[1]:
        if st.button("运行回测", width="stretch"):
            execute_step("Run Backtest", lambda: run_backtest_step(config))
    with row2[2]:
        if st.button("生成报告", width="stretch"):
            execute_step("Generate Report", run_generate_report)

    if st.button("全流程运行 Run All", type="primary", width="stretch"):
        execute_step("Run All", lambda: run_all(config))

    status_col, artifact_col = st.columns(2)
    with status_col:
        st.subheader("Run Status")
        st.info(st.session_state["status"])
        st.subheader("Logs")
        st.text_area("Log Output", value="\n".join(st.session_state["logs"]), height=280)

    with artifact_col:
        st.subheader("Artifacts")
        for name, path in artifact_status().items():
            if name == "nav.png":
                continue
            st.write(f"{name}: {'exists' if path.exists() else 'missing'}")

    st.subheader("Preview")
    nav_image = artifact_status()["nav.png"]
    if nav_image.exists():
        st.image(str(nav_image), caption="NAV Figure", width="stretch")
    else:
        st.caption("NAV figure has not been generated yet.")


if __name__ == "__main__":
    main()
