"""Factor registry."""

from __future__ import annotations

from typing import Callable

import pandas as pd

from quant_lab.factor_layer.fundamental import build_fundamental_factors
from quant_lab.factor_layer.technical import build_technical_factors

FactorBuilder = Callable[[pd.DataFrame], pd.DataFrame]

FACTOR_BUILDERS: dict[str, FactorBuilder] = {
    "technical": build_technical_factors,
    "fundamental": build_fundamental_factors,
}
