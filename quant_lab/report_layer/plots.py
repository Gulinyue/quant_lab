"""Plot generation for the minimal report layer."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_nav(nav: pd.DataFrame, output_path: Path) -> None:
    """Plot NAV curve."""
    if nav.empty:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 4))
    nav["nav"].plot(ax=ax, color="#1f77b4", linewidth=2)
    ax.set_title("NAV Curve")
    ax.set_xlabel("Trade Date")
    ax.set_ylabel("NAV")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_drawdown(nav: pd.DataFrame, output_path: Path) -> None:
    """Plot drawdown curve."""
    if nav.empty:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    drawdown = nav["nav"] / nav["nav"].cummax() - 1.0
    fig, ax = plt.subplots(figsize=(10, 4))
    drawdown.plot(ax=ax, color="#d62728", linewidth=2)
    ax.set_title("Drawdown Curve")
    ax.set_xlabel("Trade Date")
    ax.set_ylabel("Drawdown")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_turnover(nav: pd.DataFrame, output_path: Path) -> None:
    """Plot daily turnover curve."""
    if nav.empty or "turnover" not in nav.columns:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 4))
    nav["turnover"].plot(ax=ax, color="#ff7f0e", linewidth=1.8)
    ax.set_title("Daily Turnover")
    ax.set_xlabel("Trade Date")
    ax.set_ylabel("Turnover")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_screening_distribution(screening: pd.DataFrame, output_path: Path) -> None:
    """Plot screening recommendation distribution."""
    if screening.empty or "recommendation" not in screening.columns:
        return
    counts = screening["recommendation"].fillna("unknown").value_counts()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    counts.plot(kind="bar", ax=ax, color="#2ca02c")
    ax.set_title("Screening Recommendation Distribution")
    ax.set_xlabel("Recommendation")
    ax.set_ylabel("Count")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_correlation_heatmap(correlation_matrix: pd.DataFrame, output_path: Path) -> None:
    """Plot factor correlation heatmap."""
    if correlation_matrix.empty:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 6))
    image = ax.imshow(correlation_matrix.fillna(0.0).values, cmap="coolwarm", vmin=-1.0, vmax=1.0)
    ax.set_xticks(range(len(correlation_matrix.columns)))
    ax.set_yticks(range(len(correlation_matrix.index)))
    ax.set_xticklabels(correlation_matrix.columns, rotation=45, ha="right")
    ax.set_yticklabels(correlation_matrix.index)
    ax.set_title("Factor Correlation Heatmap")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
