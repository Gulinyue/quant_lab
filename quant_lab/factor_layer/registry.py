"""Single-factor registry and metadata."""

from __future__ import annotations

from typing import Callable

import pandas as pd

from quant_lab.factor_layer.factor_metadata import FactorMetadata
from quant_lab.factor_layer.lifecycle import (
    is_active_status,
    is_deprecated_status,
    is_testing_status,
    validate_metadata,
)

FactorFunc = Callable[[pd.DataFrame], pd.Series]


class FactorSpec:
    """Definition of one factor and its metadata."""

    def __init__(self, metadata: FactorMetadata, func: FactorFunc) -> None:
        self.metadata = metadata
        self.func = func

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def group(self) -> str:
        return self.metadata.group

    @property
    def description(self) -> str:
        return self.metadata.description

    @property
    def required_columns(self) -> tuple[str, ...]:
        return self.metadata.required_columns

    @property
    def direction(self) -> str:
        return self.metadata.direction

    @property
    def min_history(self) -> int:
        return self.metadata.min_history

    @property
    def status(self) -> str:
        return self.metadata.status

    @property
    def version(self) -> str:
        return self.metadata.version

    @property
    def category(self) -> str:
        return self.metadata.category

    @property
    def tags(self) -> tuple[str, ...]:
        return self.metadata.tags


class FactorRegistry:
    """Registry for single-factor definitions."""

    def __init__(self) -> None:
        self._factors: dict[str, FactorSpec] = {}

    def register(self, spec: FactorSpec) -> None:
        """Register one factor spec."""
        if spec.name in self._factors:
            raise ValueError(f"Duplicate factor registration: {spec.name}")
        validate_metadata(spec.metadata)
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

    def list_by_status(self, status: str) -> list[FactorSpec]:
        """List factor specs by lifecycle status."""
        return [spec for spec in self.list_specs() if spec.status == status]

    def list_active(self) -> list[FactorSpec]:
        """List active factors."""
        return [spec for spec in self.list_specs() if is_active_status(spec.status)]

    def list_testing(self) -> list[FactorSpec]:
        """List testing factors."""
        return [spec for spec in self.list_specs() if is_testing_status(spec.status)]

    def list_deprecated(self) -> list[FactorSpec]:
        """List deprecated factors."""
        return [spec for spec in self.list_specs() if is_deprecated_status(spec.status)]


FACTOR_REGISTRY = FactorRegistry()


def register_factor(
    *,
    name: str,
    group: str,
    description: str,
    required_columns: tuple[str, ...],
    direction: str,
    min_history: int,
    status: str = "testing",
    version: str = "1.0",
    category: str = "other",
    tags: tuple[str, ...] = (),
) -> Callable[[FactorFunc], FactorFunc]:
    """Decorator for registering a factor function."""

    def _decorator(func: FactorFunc) -> FactorFunc:
        metadata = FactorMetadata(
            name=name,
            group=group,
            description=description,
            required_columns=required_columns,
            direction=direction,
            min_history=min_history,
            status=status,
            version=version,
            category=category,
            tags=tags,
        )
        spec = FactorSpec(metadata=metadata, func=func)
        FACTOR_REGISTRY.register(spec)
        return func

    return _decorator
