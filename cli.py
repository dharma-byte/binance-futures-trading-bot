#!/usr/bin/env python3
"""
cli.py – CLI entry point for the Binance Futures Testnet Trading Bot.

Usage examples:
  python cli.py place --symbol BTCUSDT --side BUY  --type MARKET --qty 0.001
  python cli.py place --symbol BTCUSDT --side SELL --type LIMIT  --qty 0.001 --price 80000
  python cli.py place --symbol BTCUSDT --side BUY  --type STOP_MARKET --qty 0.001 --stop-price 55000
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap

from dotenv import load_dotenv

from bot.client import BinanceFuturesClient, BinanceClientError
from bot.logging_config import setup_logging
from bot import orders, validators

# ── Bootstrap ────────────────────────────────────────────────────────────────
load_dotenv()
logger = setup_logging(log_dir="logs")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_client() -> BinanceFuturesClient:
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        print(
            "\n[ERROR] API credentials not found.\n"
            "  Set BINANCE_API_KEY and BINANCE_API_SECRET in a .env file or as env vars.\n"
            "  See README.md for setup instructions.\n"
        )
        sys.exit(1)
    return BinanceFuturesClient(api_key=api_key, api_secret=api_secret)


def _print_request_summary(args: argparse.Namespace) -> None:
    print()
    print("─" * 50)
    print("  ORDER REQUEST SUMMARY")
    print("─" * 50)
    print(f"  Symbol     : {args.symbol.upper()}")
    print(f"  Side       : {args.side.upper()}")
    print(f"  Type       : {args.type.upper()}")
    print(f"  Quantity   : {args.qty}")
    if args.type.upper() == "LIMIT":
        print(f"  Price      : {args.price}")
    if args.type.upper() == "STOP_MARKET":
        print(f"  Stop Price : {args.stop_price}")
    print("─" * 50)
    print()


# ── Sub-command handlers ──────────────────────────────────────────────────────

def cmd_place(args: argparse.Namespace) -> None:
    """Handle the `place` sub-command."""

    # Early validation (gives friendlier errors than the library layer)
    try:
        validators.validate_symbol(args.symbol)
        validators.validate_side(args.side)
        validators.validate_order_type(args.type)
        validators.validate_quantity(args.qty)
        validators.validate_price(args.price, args.type)
        validators.validate_stop_price(args.stop_price, args.type)
    except ValueError as exc:
        print(f"\n[VALIDATION ERROR] {exc}\n")
        logger.warning("Validation failed: %s", exc)
        sys.exit(1)

    _print_request_summary(args)

    client = _get_client()

    try:
        result = orders.place_order(
            client=client,
            symbol=args.symbol,
            side=args.side,
            order_type=args.type,
            quantity=args.qty,
            price=args.price,
            stop_price=args.stop_price,
            time_in_force=args.tif,
        )
        print(result.summary())
        print(f"\n  ✓  Order placed successfully (orderId={result.order_id})\n")

    except BinanceClientError as exc:
        print(f"\n  ✗  API Error: {exc}\n")
        logger.error("Order failed with API error: %s", exc)
        sys.exit(1)
    except Exception as exc:
        print(f"\n  ✗  Unexpected error: {exc}\n")
        logger.exception("Unexpected error: %s", exc)
        sys.exit(1)


def cmd_ping(args: argparse.Namespace) -> None:
    """Handle the `ping` sub-command (sanity-check connectivity)."""
    client = _get_client()
    try:
        server_time = client.get_server_time()
        print(f"\n  ✓  Connected to Binance Futures Testnet. Server time: {server_time}\n")
    except BinanceClientError as exc:
        print(f"\n  ✗  Could not reach Binance: {exc}\n")
        sys.exit(1)


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description=textwrap.dedent(
            """\
            Binance Futures Testnet Trading Bot
            ------------------------------------
            Place MARKET, LIMIT, or STOP_MARKET orders on the USDT-M testnet.
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ── ping ──────────────────────────────────────────────────────────────────
    sub.add_parser("ping", help="Test connectivity to Binance Testnet.")

    # ── place ─────────────────────────────────────────────────────────────────
    place = sub.add_parser(
        "place",
        help="Place a new futures order.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
            Place a futures order on Binance Testnet.

            Examples:
              Market buy:
                python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001

              Limit sell:
                python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 100000

              Stop-market buy (stop at $55,000):
                python cli.py place --symbol BTCUSDT --side BUY --type STOP_MARKET --qty 0.001 --stop-price 55000
            """
        ),
    )
    place.add_argument(
        "--symbol", "-s", required=True, metavar="SYMBOL",
        help="Trading pair, e.g. BTCUSDT"
    )
    place.add_argument(
        "--side", required=True, choices=["BUY", "SELL", "buy", "sell"],
        metavar="SIDE", help="BUY or SELL"
    )
    place.add_argument(
        "--type", "-t", required=True,
        choices=["MARKET", "LIMIT", "market", "limit"],
        metavar="TYPE", help="MARKET | LIMIT | TAKE_PROFIT_MARKET"
    )
    place.add_argument(
        "--qty", "-q", required=True, metavar="QTY",
        help="Order quantity (e.g. 0.001)"
    )
    place.add_argument(
        "--price", "-p", default=None, metavar="PRICE",
        help="Limit price (required for LIMIT orders)"
    )
    place.add_argument(
        "--stop-price", dest="stop_price", default=None, metavar="STOP_PRICE",
        help="Stop price (required for STOP_MARKET orders)"
    )
    place.add_argument(
        "--tif", default="GTC", choices=["GTC", "IOC", "FOK"],
        metavar="TIF", help="Time-in-force for LIMIT orders (default: GTC)"
    )

    return parser


# ── Entry ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "ping":
        cmd_ping(args)
    elif args.command == "place":
        cmd_place(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()