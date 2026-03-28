"""Entry point for the end-to-end v0.1 pipeline."""

from __future__ import annotations

from quant_lab.common.logger import setup_logger
from quant_lab.common.paths import ensure_directories


def main() -> None:
    """Prepare project directories and logger."""
    ensure_directories()
    setup_logger()


if __name__ == "__main__":
    main()
