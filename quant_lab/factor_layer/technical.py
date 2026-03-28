"""Technical factor definitions."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_lab.factor_layer.registry import register_factor


def _sorted_frame(market_panel: pd.DataFrame) -> pd.DataFrame:
    return market_panel.reset_index().sort_values(["asset", "trade_date"]).copy()


def _grouped(frame: pd.DataFrame):
    return frame.groupby("asset", group_keys=False)


def _finalize_series(frame: pd.DataFrame, column_name: str) -> pd.Series:
    series = frame.set_index(["trade_date", "asset"])[column_name]
    series.name = column_name
    return series.replace([np.inf, -np.inf], np.nan)


@register_factor(
    name="mom_20",
    group="technical",
    description="20-day adjusted-price momentum.",
    required_columns=("close_adj",),
    direction="higher_is_better",
    min_history=20,
)
def factor_mom_20(market_panel: pd.DataFrame) -> pd.Series:
    """20-day momentum."""
    frame = _sorted_frame(market_panel)
    frame["mom_20"] = _grouped(frame)["close_adj"].pct_change(20)
    return _finalize_series(frame, "mom_20")


@register_factor(
    name="rev_5",
    group="technical",
    description="5-day reversal computed as negative short-term return.",
    required_columns=("close_adj",),
    direction="higher_is_better",
    min_history=5,
)
def factor_rev_5(market_panel: pd.DataFrame) -> pd.Series:
    """5-day reversal."""
    frame = _sorted_frame(market_panel)
    frame["rev_5"] = -_grouped(frame)["close_adj"].pct_change(5)
    return _finalize_series(frame, "rev_5")


@register_factor(
    name="vol_20",
    group="technical",
    description="20-day realized volatility of adjusted returns.",
    required_columns=("close_adj",),
    direction="lower_is_better",
    min_history=20,
)
def factor_vol_20(market_panel: pd.DataFrame) -> pd.Series:
    """20-day volatility."""
    frame = _sorted_frame(market_panel)
    frame["ret_1d"] = _grouped(frame)["close_adj"].pct_change()
    frame["vol_20"] = _grouped(frame)["ret_1d"].rolling(20).std().reset_index(level=0, drop=True)
    return _finalize_series(frame, "vol_20")


@register_factor(
    name="turnover_20",
    group="technical",
    description="20-day average turnover rate.",
    required_columns=("turnover_rate",),
    direction="higher_is_better",
    min_history=20,
)
def factor_turnover_20(market_panel: pd.DataFrame) -> pd.Series:
    """20-day average turnover."""
    frame = _sorted_frame(market_panel)
    frame["turnover_20"] = _grouped(frame)["turnover_rate"].rolling(20).mean().reset_index(level=0, drop=True)
    return _finalize_series(frame, "turnover_20")


@register_factor(
    name="price_volume_corr_20",
    group="technical",
    description="20-day rolling correlation between price returns and volume changes.",
    required_columns=("close_adj", "volume"),
    direction="explicit_sign",
    min_history=20,
)
def factor_price_volume_corr_20(market_panel: pd.DataFrame) -> pd.Series:
    """20-day price-volume correlation."""
    frame = _sorted_frame(market_panel)
    price_ret = _grouped(frame)["close_adj"].pct_change()
    volume_chg = _grouped(frame)["volume"].pct_change()
    corr_input = pd.DataFrame({"asset": frame["asset"], "price_ret": price_ret, "volume_chg": volume_chg})
    frame["price_volume_corr_20"] = (
        corr_input.groupby("asset")[["price_ret", "volume_chg"]]
        .apply(lambda sub: sub["price_ret"].rolling(20).corr(sub["volume_chg"]))
        .reset_index(level=0, drop=True)
    )
    return _finalize_series(frame, "price_volume_corr_20")
