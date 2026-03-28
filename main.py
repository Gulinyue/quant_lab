"""Entry point for the end-to-end v0.1 pipeline."""

from __future__ import annotations

import argparse

from quant_lab.common.logger import setup_logger
from quant_lab.common.paths import ensure_directories


def main() -> None:
    """Prepare project directories and logger."""
    ensure_directories()
    setup_logger()


def cli() -> None:
    """Minimal top-level CLI forwarding."""
    parser = argparse.ArgumentParser(description="Quant Lab bootstrap or pipeline runner.")
    parser.add_argument("command", nargs="?", default="bootstrap", choices=["bootstrap", "pipeline"])
    args, _ = parser.parse_known_args()
    if args.command == "pipeline":
        from scripts.run_pipeline import run as run_pipeline

        run_pipeline()
        return
    main()


if __name__ == "__main__":
    cli()
