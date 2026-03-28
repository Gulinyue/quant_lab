"""Strategy abstractions and result containers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(slots=True)
class StrategyRunResult:
    """Standard strategy-layer outputs."""

    target_positions: pd.DataFrame
    diagnostics: pd.DataFrame
    selected_factors: list[str]
    dropped_factors: dict[str, str]
    config: dict[str, Any]


class Strategy(ABC):
    """Abstract strategy interface."""

    @abstractmethod
    def run(
        self,
        factor_panel: pd.DataFrame,
        metadata: pd.DataFrame,
        screening: pd.DataFrame | None = None,
    ) -> StrategyRunResult:
        """Execute the strategy and return standard outputs."""
