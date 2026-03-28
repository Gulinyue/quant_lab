"""Fundamental factor definitions."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_lab.factor_layer.registry import register_factor


def _finalize_series(series: pd.Series, name: str) -> pd.Series:
    series = series.replace([np.inf, -np.inf], np.nan)
    series.name = name
    return series


@register_factor(
    name="bp",
    group="fundamental",
    description="Book-to-price proxy using inverse PB.",
    required_columns=("pb",),
    direction="higher_is_better",
    min_history=1,
    status="active",
    version="1.0",
    category="valuation",
    tags=("valuation_family", "bp"),
)
def factor_bp(market_panel: pd.DataFrame) -> pd.Series:
    """Book-to-price proxy."""
    return _finalize_series(1.0 / market_panel["pb"].replace(0, np.nan), "bp")


@register_factor(
    name="ep",
    group="fundamental",
    description="Earnings-to-price proxy using inverse PE.",
    required_columns=("pe",),
    direction="higher_is_better",
    min_history=1,
    status="active",
    version="1.0",
    category="valuation",
    tags=("valuation_family", "ep"),
)
def factor_ep(market_panel: pd.DataFrame) -> pd.Series:
    """Earnings-to-price proxy."""
    return _finalize_series(1.0 / market_panel["pe"].replace(0, np.nan), "ep")


@register_factor(
    name="size",
    group="fundamental",
    description="Log total market value.",
    required_columns=("total_mv",),
    direction="lower_is_better",
    min_history=1,
    status="active",
    version="1.0",
    category="size",
    tags=("size_family", "size"),
)
def factor_size(market_panel: pd.DataFrame) -> pd.Series:
    """Log market capitalization."""
    return _finalize_series(np.log(market_panel["total_mv"].replace(0, np.nan)), "size")
