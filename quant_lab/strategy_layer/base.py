"""Strategy abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    """Abstract strategy interface."""

    @abstractmethod
    def generate_target_positions(self, factor_panel: pd.DataFrame) -> pd.DataFrame:
        """Return target positions."""
