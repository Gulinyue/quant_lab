"""Fundamental factor definitions."""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_fundamental_factors(market_panel: pd.DataFrame) -> pd.DataFrame:
    """Calculate core fundamental factors."""
    frame = market_panel.copy()
    result = pd.DataFrame(index=frame.index)
    result["bp"] = 1.0 / frame["pb"].replace(0, np.nan)
    result["ep"] = 1.0 / frame["pe"].replace(0, np.nan)
    result["size"] = np.log(frame["total_mv"].replace(0, np.nan))
    return result.replace([np.inf, -np.inf], np.nan)
