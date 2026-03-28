"""Path helpers for the project."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_TUSHARE_DIR = RAW_DIR / "tushare"
RAW_AKSHARE_DIR = RAW_DIR / "akshare"
CACHE_DIR = DATA_DIR / "cache"
WAREHOUSE_DIR = DATA_DIR / "warehouse"
TEMP_DIR = DATA_DIR / "temp"
LOG_DIR = PROJECT_ROOT / "logs"
REPORT_DIR = PROJECT_ROOT / "reports"
FIGURE_DIR = REPORT_DIR / "figures"
TABLE_DIR = REPORT_DIR / "tables"
HTML_DIR = REPORT_DIR / "html"

REQUIRED_DIRS = [
    CONFIG_DIR,
    RAW_TUSHARE_DIR,
    RAW_AKSHARE_DIR,
    CACHE_DIR,
    WAREHOUSE_DIR,
    TEMP_DIR,
    LOG_DIR,
    REPORT_DIR,
    FIGURE_DIR,
    TABLE_DIR,
    HTML_DIR,
]


def ensure_directories() -> None:
    """Create project directories if missing."""
    for path in REQUIRED_DIRS:
        path.mkdir(parents=True, exist_ok=True)
