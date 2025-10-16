from __future__ import annotations

import argparse
import sys
from typing import Optional

from .config import Config, build_instrument_key
from .strategy import run_threshold_strategy
from .upstox_client import UpstoxClient


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple Upstox Threshold Trading Bot")
    g_instrument = parser.add_mutually_exclusive_group(required=False)
    g_instrument.add_argument("--instrument-key", help="Instrument key like NSE_EQ|RELIANCE")

    parser.add_argument("--exchange", default="NSE_EQ", help="Exchange segment, e.g., NSE_EQ")
    parser.add_argument("--symbol", help="Trading symbol, e.g., RELIANCE")

    parser.add_argument("--buy-below", type=float, help="Buy when LTP <= value")
    parser.add_argument("--sell-above", type=float, help="Sell when LTP >= value")
    parser.add_argument("--quantity", type=int, default=1, help="Order quantity")
    parser.add_argument("--interval", type=float, default=2.0, help="Polling interval seconds")
    parser.add_argument("--cooldown", type=float, default=5.0, help="Cooldown seconds between trades")
    parser.add_argument("--max-trades", type=int, help="Stop after N trades")
    parser.add_argument("--dry-run", action="store_true", help="Do not place live orders")

    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    cfg = Config.from_env()

    instrument_key = args.instrument_key
    if not instrument_key:
        if not args.symbol:
            print("Either --instrument-key or --symbol is required", file=sys.stderr)
            return 2
        instrument_key = build_instrument_key(args.exchange, args.symbol)

    client = UpstoxClient(config=cfg, dry_run=args.dry_run)

    if not cfg.access_token and not args.dry_run:
        print("UPSTOX_ACCESS_TOKEN not found. Running in dry-run. Add --dry-run to silence.")
        client.dry_run = True

    run_threshold_strategy(
        client=client,
        instrument_key=instrument_key,
        buy_below=args.buy_below,
        sell_above=args.sell_above,
        quantity=args.quantity,
        poll_interval_sec=args.interval,
        max_trades=args.max_trades,
        cooldown_sec=args.cooldown,
    )

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
