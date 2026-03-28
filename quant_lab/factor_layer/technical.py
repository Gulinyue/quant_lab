"""Technical factor definitions."""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_technical_factors(market_panel: pd.DataFrame) -> pd.DataFrame:
    """Calculate core technical factors."""
    frame = market_panel.reset_index().sort_values(["asset", "trade_date"]).copy()
    grouped = frame.groupby("asset", group_keys=False)
    frame["mom_20"] = grouped["close_adj"].pct_change(20)
    frame["rev_5"] = -grouped["close_adj"].pct_change(5)
    frame["vol_20"] = grouped["close_adj"].pct_change().rolling(20).std().reset_index(level=0, drop=True)
    frame["turnover_20"] = grouped["turnover_rate"].rolling(20).mean().reset_index(level=0, drop=True)

    def rolling_corr(sub_df: pd.DataFrame) -> pd.Series:
        price_ret = sub_df["close_adj"].pct_change()
        volume_chg = sub_df["volume"].pct_change()
        return price_ret.rolling(20).corr(volume_chg)

    frame["price_volume_corr_20"] = grouped.apply(rolling_corr).reset_index(level=0, drop=True)
    return frame.set_index(["trade_date", "asset"])[["mom_20", "rev_5", "vol_20", "turnover_20", "price_volume_corr_20"]].replace([np.inf, -np.inf], np.nan)
