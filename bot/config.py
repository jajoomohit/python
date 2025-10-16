from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    api_key: Optional[str]
    api_secret: Optional[str]
    access_token: Optional[str]
    redirect_uri: Optional[str]
    base_url: str

    @staticmethod
    def from_env() -> "Config":
        load_dotenv(override=False)
        return Config(
            api_key=os.getenv("UPSTOX_API_KEY"),
            api_secret=os.getenv("UPSTOX_API_SECRET"),
            access_token=os.getenv("UPSTOX_ACCESS_TOKEN"),
            redirect_uri=os.getenv("UPSTOX_REDIRECT_URI"),
            base_url=os.getenv("UPSTOX_BASE_URL", "https://api.upstox.com/v2"),
        )


def build_instrument_key(exchange: str, symbol: str, delimiter: str = "|") -> str:
    exchange = exchange.strip()
    symbol = symbol.strip()
    return f"{exchange}{delimiter}{symbol}"
