"""Factor panel construction."""

from __future__ import annotations

import pandas as pd

from quant_lab.factor_layer.preprocess import winsorize_by_date, zscore_by_date
from quant_lab.factor_layer.registry import FACTOR_BUILDERS


def build_factor_panel(market_panel: pd.DataFrame, apply_standardize: bool = True) -> pd.DataFrame:
    """Build a standardized factor panel from the market panel."""
    frames = [builder(market_panel) for builder in FACTOR_BUILDERS.values()]
    factor_panel = pd.concat(frames, axis=1).sort_index()
    if apply_standardize:
        factor_panel = winsorize_by_date(factor_panel)
        factor_panel = zscore_by_date(factor_panel)
    return factor_panel
