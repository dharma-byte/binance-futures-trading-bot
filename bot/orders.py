"""
Order placement logic.

This layer sits between the CLI and the raw HTTP client.
It builds validated order payloads, calls the client, and returns
a normalised result dict that the CLI can print.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from bot.client import BinanceFuturesClient, BinanceClientError
from bot import validators

logger = logging.getLogger("trading_bot.orders")


class OrderResult:
    """Lightweight wrapper around a Binance order response."""

    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.order_id: int = raw.get("orderId", 0)
        self.client_order_id: str = raw.get("clientOrderId", "")
        self.symbol: str = raw.get("symbol", "")
        self.side: str = raw.get("side", "")
        self.order_type: str = raw.get("type", "")
        self.status: str = raw.get("status", "")
        self.orig_qty: str = raw.get("origQty", "0")
        self.executed_qty: str = raw.get("executedQty", "0")
        self.avg_price: str = raw.get("avgPrice", "0")
        self.price: str = raw.get("price", "0")
        self.stop_price: str = raw.get("stopPrice", "0")
        self.time_in_force: str = raw.get("timeInForce", "")
        self.update_time: int = raw.get("updateTime", 0)

    def summary(self) -> str:
        lines = [
            "─" * 50,
            "  ORDER RESULT",
            "─" * 50,
            f"  Order ID       : {self.order_id}",
            f"  Client OID     : {self.client_order_id}",
            f"  Symbol         : {self.symbol}",
            f"  Side           : {self.side}",
            f"  Type           : {self.order_type}",
            f"  Status         : {self.status}",
            f"  Orig Qty       : {self.orig_qty}",
            f"  Executed Qty   : {self.executed_qty}",
            f"  Avg Price      : {self.avg_price}",
        ]
        if self.price and self.price != "0":
            lines.append(f"  Limit Price    : {self.price}")
        if self.stop_price and self.stop_price != "0":
            lines.append(f"  Stop Price     : {self.stop_price}")
        if self.time_in_force:
            lines.append(f"  Time In Force  : {self.time_in_force}")
        lines.append("─" * 50)
        return "\n".join(lines)


def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str] = None,
    stop_price: Optional[str] = None,
    time_in_force: str = "GTC",
) -> OrderResult:
    """
    Validate inputs, build the Binance payload, submit, and return an OrderResult.

    Parameters
    ----------
    client       : authenticated BinanceFuturesClient
    symbol       : e.g. "BTCUSDT"
    side         : "BUY" or "SELL"
    order_type   : "MARKET", "LIMIT", or "STOP_MARKET"
    quantity     : order quantity as string/number
    price        : required for LIMIT orders
    stop_price   : required for STOP_MARKET orders
    time_in_force: GTC / IOC / FOK (used for LIMIT)
    """
    # --- validate ---
    symbol = validators.validate_symbol(symbol)
    side = validators.validate_side(side)
    order_type = validators.validate_order_type(order_type)
    quantity = validators.validate_quantity(quantity)
    price = validators.validate_price(price, order_type)
    stop_price = validators.validate_stop_price(stop_price, order_type)

    # --- build payload ---
    payload: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": quantity,
    }

    if order_type == "LIMIT":
        payload["price"] = price
        payload["timeInForce"] = time_in_force

    if order_type == "TAKE_PROFIT_MARKET":
        payload["stopPrice"] = stop_price
        payload["workingType"] = "CONTRACT_PRICE"
        payload["reduceOnly"] = "false"
    # --- log request summary ---
    logger.info(
        "Submitting %s %s order | symbol=%s qty=%s price=%s stop=%s",
        side,
        order_type,
        symbol,
        quantity,
        price or "N/A",
        stop_price or "N/A",
    )

    # --- execute ---
    try:
        response = client.place_order(payload)
    except BinanceClientError:
        raise  # let CLI handle presentation
    except Exception as exc:
        logger.exception("Unexpected error during order placement: %s", exc)
        raise

    result = OrderResult(response)
    logger.info(
        "Order accepted | orderId=%s status=%s executedQty=%s avgPrice=%s",
        result.order_id,
        result.status,
        result.executed_qty,
        result.avg_price,
    )
    return result