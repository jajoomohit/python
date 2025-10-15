## Simple Upstox Trading Bot

This is a minimal, polling-based trading bot for Upstox with a threshold strategy. It can run in dry-run mode without credentials, simulating prices to test your logic.

### Features
- Threshold strategy: buy when LTP <= buy_below, sell when LTP >= sell_above
- CLI with `.env` configuration
- Dry-run mode that simulates price movement if no token is available
- Uses Upstox HTTP v2 APIs when `UPSTOX_ACCESS_TOKEN` is set; optional fallback to older SDK

### Setup
1. Create and activate a Python 3.10+ environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your credentials if you want to trade live.

### Usage
Dry-run with simulated prices:
```bash
python -m bot --symbol RELIANCE --exchange NSE_EQ --buy-below 2500 --sell-above 2510 --quantity 1 --dry-run
```

Live mode (requires `UPSTOX_ACCESS_TOKEN` in `.env`):
```bash
python -m bot --symbol RELIANCE --exchange NSE_EQ --buy-below 2500 --sell-above 2510 --quantity 1
```

Alternatively, pass an `--instrument-key` like `NSE_EQ|RELIANCE`.

### Notes
- This example is deliberately simple and does not handle risk management, order rejections, or network retries beyond basics.
- Use at your own risk. For education/testing only.