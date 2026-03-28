"""Single-factor registry and metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

FactorFunc = Callable[[pd.DataFrame], pd.Series]


@dataclass(frozen=True, slots=True)
class FactorSpec:
    """Definition of one factor and its metadata."""

    name: str
    group: str
    description: str
    required_columns: tuple[str, ...]
    direction: str
    min_history: int
    func: FactorFunc


class FactorRegistry:
    """Registry for single-factor definitions."""

    def __init__(self) -> None:
        self._factors: dict[str, FactorSpec] = {}

    def register(self, spec: FactorSpec) -> None:
        """Register one factor spec."""
        if spec.name in self._factors:
            raise ValueError(f"Duplicate factor registration: {spec.name}")
        self._factors[spec.name] = spec

    def get(self, name: str) -> FactorSpec:
        """Get one factor spec by name."""
        if name not in self._factors:
            raise KeyError(f"Factor not registered: {name}")
        return self._factors[name]

    def list_names(self) -> list[str]:
        """List all registered factor names."""
        return sorted(self._factors.keys())

    def list_specs(self) -> list[FactorSpec]:
        """List all registered factor specs in stable order."""
        return [self._factors[name] for name in self.list_names()]

    def has(self, name: str) -> bool:
        """Check whether the registry contains a factor."""
        return name in self._factors


FACTOR_REGISTRY = FactorRegistry()


def register_factor(
    *,
    name: str,
    group: str,
    description: str,
    required_columns: tuple[str, ...],
    direction: str,
    min_history: int,
) -> Callable[[FactorFunc], FactorFunc]:
    """Decorator for registering a factor function."""

    def _decorator(func: FactorFunc) -> FactorFunc:
        spec = FactorSpec(
            name=name,
            group=group,
            description=description,
            required_columns=required_columns,
            direction=direction,
            min_history=min_history,
            func=func,
        )
        FACTOR_REGISTRY.register(spec)
        return func

    return _decorator
