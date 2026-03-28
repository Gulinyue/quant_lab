"""Project settings and configuration loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from quant_lab.common.paths import CONFIG_DIR, PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")


def load_yaml_config(path: Path) -> dict[str, Any]:
    """Load a YAML configuration file with UTF-8 encoding."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data


@dataclass(slots=True)
class AppSettings:
    """Top-level application settings."""

    data: dict[str, Any]
    factors: dict[str, Any]
    strategy: dict[str, Any]
    backtest: dict[str, Any]
    report: dict[str, Any]

    @classmethod
    def load(cls) -> "AppSettings":
        """Load all project YAML configs."""
        return cls(
            data=load_yaml_config(CONFIG_DIR / "data.yaml"),
            factors=load_yaml_config(CONFIG_DIR / "factors.yaml"),
            strategy=load_yaml_config(CONFIG_DIR / "strategy.yaml"),
            backtest=load_yaml_config(CONFIG_DIR / "backtest.yaml"),
            report=load_yaml_config(CONFIG_DIR / "report.yaml"),
        )
