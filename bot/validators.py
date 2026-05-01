"""
Input validation for order parameters.
Raises ValueError with a descriptive message on any invalid input.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}


def validate_symbol(symbol: str) -> str:
    """Return the symbol uppercased, or raise ValueError."""
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string (e.g. BTCUSDT).")
    cleaned = symbol.strip().upper()
    if len(cleaned) < 3:
        raise ValueError(f"Symbol '{symbol}' looks too short. Expected something like BTCUSDT.")
    return cleaned


def validate_side(side: str) -> str:
    """Return the side uppercased, or raise ValueError."""
    cleaned = side.strip().upper()
    if cleaned not in VALID_SIDES:
        raise ValueError(f"Side must be one of {sorted(VALID_SIDES)}. Got '{side}'.")
    return cleaned


def validate_order_type(order_type: str) -> str:
    """Return the order type uppercased, or raise ValueError."""
    cleaned = order_type.strip().upper()
    if cleaned not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Order type must be one of {sorted(VALID_ORDER_TYPES)}. Got '{order_type}'."
        )
    return cleaned


def validate_quantity(quantity: str | float) -> str:
    """Return quantity as a string decimal, or raise ValueError."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be positive. Got {quantity}.")
    return str(qty)


def validate_price(price: Optional[str | float], order_type: str) -> Optional[str]:
    """
    Validate price field.
    - Required for LIMIT orders.
    - Must be positive when provided.
    Returns the price as a string, or None for MARKET orders.
    """
    order_type = order_type.strip().upper()
    if order_type in ("MARKET", "TAKE_PROFIT_MARKET"):
        return None  # price is ignored for market orders

    if price is None or str(price).strip() == "":
        raise ValueError(f"Price is required for {order_type} orders.")

    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Price '{price}' is not a valid number.")
    if p <= 0:
        raise ValueError(f"Price must be positive. Got {price}.")
    return str(p)


def validate_stop_price(stop_price: Optional[str | float], order_type: str) -> Optional[str]:
    """Validate stop_price for STOP_MARKET orders."""
    order_type = order_type.strip().upper()
    if order_type != "TAKE_PROFIT_MARKET":
        return None

    if stop_price is None or str(stop_price).strip() == "":
        raise ValueError("stop_price is required for STOP_MARKET orders.")

    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"stop_price '{stop_price}' is not a valid number.")
    if sp <= 0:
        raise ValueError(f"stop_price must be positive. Got {stop_price}.")
    return str(sp)