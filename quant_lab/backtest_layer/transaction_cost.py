"""Transaction cost helpers."""

from __future__ import annotations


def estimate_trade_cost(amount: float, side: str, commission: float, slippage: float, stamp_tax_sell: float) -> float:
    """Estimate transaction cost for one trade amount."""
    base_cost = amount * (commission + slippage)
    if side.upper() == "SELL":
        base_cost += amount * stamp_tax_sell
    return float(base_cost)
