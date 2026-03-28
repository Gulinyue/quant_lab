"""Factor metadata definitions."""

from __future__ import annotations

from dataclasses import dataclass, field

VALID_FACTOR_STATUSES = {"draft", "testing", "active", "deprecated", "archived"}


@dataclass(frozen=True, slots=True)
class FactorMetadata:
    """Metadata for one factor."""

    name: str
    group: str
    description: str
    required_columns: tuple[str, ...]
    direction: str
    min_history: int
    status: str = "testing"
    version: str = "1.0"
    category: str = "other"
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.status not in VALID_FACTOR_STATUSES:
            raise ValueError(f"Invalid factor status: {self.status}")

    def to_record(self) -> dict[str, object]:
        """Convert metadata to a flat record."""
        return {
            "name": self.name,
            "group": self.group,
            "category": self.category,
            "status": self.status,
            "version": self.version,
            "direction": self.direction,
            "required_columns": ",".join(self.required_columns),
            "min_history": self.min_history,
            "description": self.description,
            "tags": ",".join(self.tags),
        }
