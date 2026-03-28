"""Factor lifecycle helpers."""

from __future__ import annotations

from quant_lab.factor_layer.factor_metadata import FactorMetadata


def validate_metadata(metadata: FactorMetadata) -> None:
    """Validate required lifecycle metadata."""
    if not metadata.name:
        raise ValueError("Factor metadata requires a non-empty name.")
    if not metadata.group:
        raise ValueError(f"Factor {metadata.name} requires group metadata.")
    if not metadata.description:
        raise ValueError(f"Factor {metadata.name} requires description metadata.")
    if not metadata.required_columns:
        raise ValueError(f"Factor {metadata.name} requires at least one dependency column.")


def is_active_status(status: str) -> bool:
    """Check whether a factor is active."""
    return status == "active"


def is_testing_status(status: str) -> bool:
    """Check whether a factor is in testing."""
    return status == "testing"


def is_deprecated_status(status: str) -> bool:
    """Check whether a factor is deprecated."""
    return status == "deprecated"
