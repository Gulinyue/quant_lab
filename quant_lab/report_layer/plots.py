"""Plot generation."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_nav(nav: pd.DataFrame, output_path: Path) -> None:
    """Plot strategy NAV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    nav["nav"].plot(ax=ax, color="#1f77b4", linewidth=2)
    ax.set_title("Strategy NAV")
    ax.set_xlabel("Trade Date")
    ax.set_ylabel("NAV")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
