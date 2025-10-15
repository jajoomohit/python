from __future__ import annotations

import json
import time
from dataclasses import dataclass
import math
from typing import Any, Dict, Optional

import requests

from .config import Config

try:
    # Old Upstox SDK (v1). Optional.
    from upstox_api.api import (
        Upstox as UpstoxSDK,
        LiveFeedType,
        OrderType,
        ProductType,
        TransactionType,
    )

    HAS_UPSTOX_SDK = True
except Exception:  # pragma: no cover - optional dependency
    UpstoxSDK = None  # type: ignore
    LiveFeedType = None  # type: ignore
    OrderType = None  # type: ignore
    ProductType = None  # type: ignore
    TransactionType = None  # type: ignore
    HAS_UPSTOX_SDK = False


@dataclass
class LtpQuote:
    instrument_key: str
    last_price: float
    timestamp: Optional[str]


class UpstoxClient:
    def __init__(self, config: Config, dry_run: bool = False) -> None:
        self.config = config
        self.dry_run = dry_run
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        if self.config.access_token:
            self._session.headers["Authorization"] = f"Bearer {self.config.access_token}"

        self._sdk = None
        if HAS_UPSTOX_SDK and self.config.access_token:
            try:
                # SDK expects api_key and access_token
                self._sdk = UpstoxSDK(self.config.api_key, self.config.access_token)
            except Exception:
                self._sdk = None

        # Simple in-memory price simulator for dry-run when no credentials are available
        self._sim_prices: Dict[str, float] = {}

    # ---------------------- HTTP helpers ----------------------
    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        resp = self._session.request(method=method.upper(), url=url, timeout=20, **kwargs)
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        if not resp.ok:
            raise RuntimeError(f"Upstox API error {resp.status_code}: {data}")
        return data if isinstance(data, dict) else {"data": data}

    # ---------------------- Market data -----------------------
    def get_ltp(self, instrument_key: str) -> LtpQuote:
        # Simulated price path for dry-run without credentials
        if self.dry_run and not self.config.access_token:
            # Deterministic pseudo base from key; smooth oscillation over time
            seed = (hash(instrument_key) % 1000) / 1000.0
            base = 100.0 + 50.0 * seed
            t = time.time()
            price = base + 2.0 * math.sin(t / 10.0 + seed * 10.0) + 0.8 * math.sin(t / 3.0 + seed)
            return LtpQuote(instrument_key=instrument_key, last_price=float(round(price, 2)), timestamp=None)

        # Prefer HTTP v2 endpoint if token present
        if self.config.access_token:
            params = {"instrument_key": instrument_key}
            data = self._request("GET", "/market/quotes/ltp", params=params)
            # Try common shapes
            last_price: Optional[float] = None
            timestamp: Optional[str] = None
            if isinstance(data.get("data"), dict):
                node = data["data"].get(instrument_key) or next(iter(data["data"].values()), None)
                if isinstance(node, dict):
                    last_price = (
                        node.get("ltp")
                        or node.get("last_price")
                        or node.get("last_traded_price")
                        or node.get("close")
                    )
                    timestamp = node.get("timestamp") or node.get("exchange_timestamp")
            if last_price is None and isinstance(data.get("ltp"), (int, float)):
                last_price = float(data["ltp"])
            if last_price is None:
                raise RuntimeError(f"Unexpected LTP response shape: {json.dumps(data)[:500]}")
            return LtpQuote(instrument_key=instrument_key, last_price=float(last_price), timestamp=timestamp)

        # Fallback to SDK if available
        if self._sdk is not None and HAS_UPSTOX_SDK:
            # Instrument key format assumed as "EXCHANGE|SYMBOL" or "EXCHANGE:SYMBOL"
            delimiter = "|" if "|" in instrument_key else ":"
            exchange, symbol = instrument_key.split(delimiter, 1)
            instrument = self._sdk.get_instrument_by_symbol(exchange, symbol)
            feed = self._sdk.get_live_feed(instrument, LiveFeedType.LTP)
            ltp_value = feed.get("ltp") or feed.get("last_price")
            if ltp_value is None:
                raise RuntimeError(f"Unexpected SDK LTP response: {feed}")
            return LtpQuote(instrument_key=instrument_key, last_price=float(ltp_value), timestamp=feed.get("timestamp"))

        raise RuntimeError("No Upstox credentials available for LTP. Provide UPSTOX_ACCESS_TOKEN.")

    # ---------------------- Orders ----------------------------
    def place_market_order(
        self,
        *,
        instrument_key: str,
        transaction_type: str,
        quantity: int,
        product: str = "I",  # I=Intraday, D=Delivery (v2 convention)
        validity: str = "DAY",
        tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        transaction_type = transaction_type.upper()
        if transaction_type not in {"BUY", "SELL"}:
            raise ValueError("transaction_type must be BUY or SELL")
        if quantity <= 0:
            raise ValueError("quantity must be positive")

        if self.dry_run:
            return {
                "status": "dry_run",
                "action": transaction_type,
                "instrument_key": instrument_key,
                "quantity": quantity,
                "product": product,
                "validity": validity,
                "tag": tag,
                "timestamp": time.time(),
            }

        # Prefer HTTP v2 endpoint
        if self.config.access_token:
            payload = {
                "instrument_key": instrument_key,
                "quantity": int(quantity),
                "product": product,
                "transaction_type": transaction_type,
                "order_type": "MARKET",
                "validity": validity,
                "tag": tag,
            }
            data = self._request("POST", "/order/place", json=payload)
            return data

        # Fallback to SDK if available
        if self._sdk is not None and HAS_UPSTOX_SDK:
            delimiter = "|" if "|" in instrument_key else ":"
            exchange, symbol = instrument_key.split(delimiter, 1)
            instrument = self._sdk.get_instrument_by_symbol(exchange, symbol)
            sdk_side = TransactionType.Buy if transaction_type == "BUY" else TransactionType.Sell
            response = self._sdk.place_order(
                transaction_type=sdk_side,
                instrument=instrument,
                quantity=int(quantity),
                order_type=OrderType.Market,
                product=ProductType.Intraday if product == "I" else ProductType.Delivery,
                price=0.0,
            )
            return {"data": response}

        raise RuntimeError("No Upstox credentials available for orders. Provide UPSTOX_ACCESS_TOKEN.")
