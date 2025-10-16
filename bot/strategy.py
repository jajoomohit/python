from __future__ import annotations

import signal
import sys
import time
from dataclasses import dataclass
from typing import Optional

from .upstox_client import UpstoxClient


@dataclass
class StrategyState:
    instrument_key: str
    position_qty: int = 0
    total_trades: int = 0
    last_trade_time: float = 0.0


def run_threshold_strategy(
    *,
    client: UpstoxClient,
    instrument_key: str,
    buy_below: Optional[float] = None,
    sell_above: Optional[float] = None,
    quantity: int = 1,
    poll_interval_sec: float = 2.0,
    max_trades: Optional[int] = None,
    cooldown_sec: float = 5.0,
) -> None:
    if buy_below is None and sell_above is None:
        raise ValueError("Provide buy_below and/or sell_above threshold")

    state = StrategyState(instrument_key=instrument_key)

    stop = False

    def handle_sigint(_sig, _frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, handle_sigint)

    while not stop:
        if max_trades is not None and state.total_trades >= max_trades:
            print("Reached max_trades; exiting.")
            break

        try:
            quote = client.get_ltp(instrument_key)
            last_price = quote.last_price
        except Exception as exc:  # resilient fetch
            print(f"LTP fetch failed: {exc}")
            time.sleep(poll_interval_sec)
            continue

        now = time.time()
        can_trade = now - state.last_trade_time >= cooldown_sec

        if buy_below is not None and state.position_qty == 0 and last_price <= buy_below and can_trade:
            try:
                resp = client.place_market_order(
                    instrument_key=instrument_key,
                    transaction_type="BUY",
                    quantity=quantity,
                )
                state.position_qty += quantity
                state.total_trades += 1
                state.last_trade_time = now
                print(f"BUY {quantity} @ {last_price} -> {resp}")
            except Exception as exc:
                print(f"BUY failed: {exc}")

        if sell_above is not None and state.position_qty > 0 and last_price >= sell_above and can_trade:
            try:
                resp = client.place_market_order(
                    instrument_key=instrument_key,
                    transaction_type="SELL",
                    quantity=state.position_qty,
                )
                print(f"SELL {state.position_qty} @ {last_price} -> {resp}")
                state.total_trades += 1
                state.position_qty = 0
                state.last_trade_time = now
            except Exception as exc:
                print(f"SELL failed: {exc}")

        time.sleep(poll_interval_sec)

    if state.position_qty > 0:
        print(f"Exiting with open position: {state.position_qty} shares. Manage risk appropriately.")
