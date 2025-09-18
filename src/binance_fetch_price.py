#!/usr/bin/env python3
"""
Fetch BTC prices from Binance public API and save them to CSV.
"""

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
import pandas as pd

try:
    from dotenv import load_dotenv  # optional, only used if installed
    load_dotenv()
except Exception:
    pass

API_URL = "https://api.binance.com/api/v3/klines"

def _parse_dt(s: str | None, fallback: datetime) -> datetime:
    if not s:
        return fallback
    # Accept naive or tz-aware; normalize to UTC
    dt = datetime.fromisoformat(s)
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def _interval_binance(agg: str) -> str:
    agg = (agg or "1H").upper()
    if agg == "1H":
        return "1h"
    if agg == "1D":
        return "1d"
    raise ValueError("AGG_INTERVAL must be 1H or 1D")

def fetch_binance_klines(
    symbol: str,
    start_utc: datetime,
    end_utc: datetime,
    interval: str,
) -> pd.DataFrame:
    """
    Stream klines from Binance between start_utc and end_utc (UTC, inclusive of start).
    Returns DataFrame with timestamp_utc (close time), open, high, low, close, volume.
    """
    start_ms = int(start_utc.timestamp() * 1000)
    end_ms = int(end_utc.timestamp() * 1000)

    all_chunks: list[pd.DataFrame] = []
    params_base = {"symbol": symbol, "interval": interval, "limit": 1000}

    while start_ms < end_ms:
        params = dict(params_base, startTime=start_ms, endTime=end_ms)
        # Simple retry loop for transient errors / rate limit
        for attempt in range(3):
            try:
                r = requests.get(API_URL, params=params, timeout=30)
                r.raise_for_status()
                rows = r.json()
                break
            except requests.RequestException as e:
                if attempt == 2:
                    raise
                time.sleep(0.5 + attempt)
        if not rows:
            break

        df = pd.DataFrame(
            rows,
            columns=[
                "open_time","open","high","low","close","volume",
                "close_time","quote_asset_volume","number_of_trades",
                "taker_buy_base","taker_buy_quote","ignore",
            ],
        )
        df = df.astype({"open":"float64","high":"float64","low":"float64","close":"float64","volume":"float64"})
        df["timestamp_utc"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
        all_chunks.append(df[["timestamp_utc","open","high","low","close","volume"]])

        # Advance cursor to just after the last close_time returned
        start_ms = int(rows[-1][6]) + 1
        # Be polite to API
        time.sleep(0.2)

    if not all_chunks:
        return pd.DataFrame(columns=["timestamp_utc","open","high","low","close","volume"])

    out = pd.concat(all_chunks, ignore_index=True).drop_duplicates(subset=["timestamp_utc"])
    out.sort_values("timestamp_utc", inplace=True)
    return out

def main():
    symbol = os.getenv("BINANCE_SYMBOL", "BTCUSDT").upper()
    agg_interval = os.getenv("AGG_INTERVAL", "1H").upper()
    interval = _interval_binance(agg_interval)

    # Defaults: last 90 days window
    now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    default_start = now_utc - timedelta(days=300)
    start_utc = _parse_dt(os.getenv("START_DATETIME"), default_start)
    end_utc = _parse_dt(os.getenv("END_DATETIME"), now_utc)

    df = fetch_binance_klines(symbol, start_utc, end_utc, interval)

    out_dir = Path("data/raw")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "btc_price.csv"
    df.to_csv(out_path, index=False)
    print(f"saved {out_path} (rows={len(df)}, symbol={symbol}, interval={agg_interval})")

if __name__ == "__main__":
    main()
