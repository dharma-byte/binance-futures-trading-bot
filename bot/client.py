"""
Low-level Binance Futures Testnet REST client.

Handles:
- HMAC-SHA256 request signing
- Timestamping
- HTTP execution with retries
- Structured request/response logging
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
import urllib.parse
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW = 5000  # ms

logger = logging.getLogger("trading_bot.client")


class BinanceClientError(Exception):
    """Raised for Binance API-level errors (non-2xx or error code in body)."""

    def __init__(self, message: str, code: Optional[int] = None, raw: Optional[dict] = None):
        super().__init__(message)
        self.code = code
        self.raw = raw


class BinanceFuturesClient:
    """
    Minimal Binance USDT-M Futures REST client.

    Parameters
    ----------
    api_key:    Testnet API key
    api_secret: Testnet API secret
    base_url:   Override the default testnet URL (useful for testing)
    timeout:    HTTP timeout in seconds
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = BASE_URL,
        timeout: int = 10,
    ):
        if not api_key or not api_secret:
            raise ValueError("Both api_key and api_secret are required.")
        self._api_key = api_key
        self._api_secret = api_secret.encode()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = self._build_session()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_server_time(self) -> int:
        """Return the Binance server time in milliseconds."""
        data = self._request("GET", "/fapi/v1/time", signed=False)
        return data["serverTime"]

    def get_exchange_info(self) -> Dict[str, Any]:
        """Return exchange metadata (symbols, filters, etc.)."""
        return self._request("GET", "/fapi/v1/exchangeInfo", signed=False)

    def place_order(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place a new futures order.

        Parameters
        ----------
        params: dict with at minimum:
            symbol, side, type, quantity
            + price for LIMIT orders
            + stopPrice for STOP_MARKET orders
        """
        logger.debug("Placing order with params: %s", params)
        return self._request("POST", "/fapi/v1/order", signed=True, data=params)

    # ------------------------------------------------------------------
    # Internal machinery
    # ------------------------------------------------------------------

    def _sign(self, query_string: str) -> str:
        return hmac.new(
            self._api_secret, query_string.encode(), hashlib.sha256
        ).hexdigest()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({"X-MBX-APIKEY": self._api_key})
        return session

    def _request(
        self,
        method: str,
        path: str,
        signed: bool = False,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        url = self._base_url + path

        # Merge params dict into a flat dict for signing
        payload: Dict[str, Any] = {}
        if params:
            payload.update(params)
        if data:
            payload.update(data)

        if signed:
            payload["timestamp"] = int(time.time() * 1000)
            payload["recvWindow"] = RECV_WINDOW
            qs = urllib.parse.urlencode(payload)
            payload["signature"] = self._sign(qs)

        logger.debug("→ %s %s  payload=%s", method, url, payload)

        try:
            if method == "GET":
                response = self._session.get(url, params=payload, timeout=self._timeout)
            elif method == "POST":
                response = self._session.post(url, data=payload, timeout=self._timeout)
            elif method == "DELETE":
                response = self._session.delete(url, params=payload, timeout=self._timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network error connecting to Binance: %s", exc)
            raise BinanceClientError(f"Network error: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out: %s", exc)
            raise BinanceClientError("Request timed out. Check your network.") from exc

        logger.debug("← %s  body=%s", response.status_code, response.text[:500])

        # Parse JSON
        try:
            body = response.json()
        except ValueError:
            raise BinanceClientError(
                f"Non-JSON response (HTTP {response.status_code}): {response.text[:200]}"
            )

        # Binance returns errors as {"code": -XXXX, "msg": "..."}
        if isinstance(body, dict) and "code" in body and body["code"] != 200:
            code = body.get("code")
            msg = body.get("msg", "Unknown error")
            logger.error("Binance API error %s: %s", code, msg)
            raise BinanceClientError(f"Binance API error {code}: {msg}", code=code, raw=body)

        if not response.ok:
            raise BinanceClientError(
                f"HTTP {response.status_code}: {response.text[:200]}"
            )

        return body