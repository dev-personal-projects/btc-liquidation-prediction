#!/usr/bin/env python3
"""
Parse WhaleBot-style Telegram messages into structured liquidation events,
then aggregate per time interval.
"""

import os
import re
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

RAW_PATH = Path("data/raw/telegram_messages.csv")
OUT_DIR = Path("data/processed")
INTERVAL = os.getenv("AGG_INTERVAL", "1H").upper()
SYMBOL_FILTER = os.getenv("SYMBOL_FILTER", "BTC") 

SIDE_RE   = re.compile(r"\bLiquidated\s+(Long|Short)\b", re.I)
AMOUNT_RE = re.compile(r":\s*(?:Buy|Sell)\s*\$([\d,]+(?:\.\d+)?)")
SYMBOL_RE = re.compile(r"\bon\s+([A-Z0-9_\-/:]+)\s+at\b", re.I) 


def parse_row(text: str) -> tuple[str | None, float | None, str | None]:
    """
    Return (side, amount_usd, symbol) or (None, None, None) if not a liquidation.
    side: 'long' | 'short'
    """
    if not text:
        return None, None, None

    side_m = SIDE_RE.search(text)
    if not side_m:
        return None, None, None
    side = side_m.group(1).lower()

    amt_m = AMOUNT_RE.search(text)
    if not amt_m:
        return None, None, None
    amount_usd = float(amt_m.group(1).replace(",", ""))

    sym_m = SYMBOL_RE.search(text)
    symbol = sym_m.group(1) if sym_m else None
    return side, amount_usd, symbol


def main() -> None:
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Missing input: {RAW_PATH}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(RAW_PATH)
    if "timestamp_utc" not in df.columns or "text" not in df.columns:
        raise ValueError("Input must contain 'timestamp_utc' and 'text' columns")

    # Parse
    parsed = df["text"].apply(parse_row)
    df["side"] = parsed.apply(lambda x: x[0])
    df["amount_usd"] = parsed.apply(lambda x: x[1])
    df["symbol"] = parsed.apply(lambda x: x[2])

    df = df.dropna(subset=["side", "amount_usd"])

    if SYMBOL_FILTER:
        df = df[df["text"].str.contains(SYMBOL_FILTER, case=False, na=False)]

    if df.empty:
        out_path = OUT_DIR / f"liqs_{INTERVAL}.csv"
        pd.DataFrame(
            columns=["timestamp_utc", "long_liq_usd", "short_liq_usd", "long_count", "short_count"]
        ).to_csv(out_path, index=False)
        print(f"saved {out_path} (rows=0)")
        return

    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp_utc"]).set_index("timestamp_utc").sort_index()

    rule = "1H" if INTERVAL == "1H" else "1D" if INTERVAL == "1D" else None
    if rule is None:
        raise ValueError("AGG_INTERVAL must be 1H or 1D")

    longs_usd = df[df["side"] == "long"].resample(rule)["amount_usd"].sum()
    shorts_usd = df[df["side"] == "short"].resample(rule)["amount_usd"].sum()

    longs_cnt = df[df["side"] == "long"].resample(rule)["side"].count()
    shorts_cnt = df[df["side"] == "short"].resample(rule)["side"].count()

    out = pd.DataFrame({
        "long_liq_usd": longs_usd,
        "short_liq_usd": shorts_usd,
        "long_count": longs_cnt,
        "short_count": shorts_cnt,
    }).fillna(0.0).reset_index()

    out.rename(columns={"timestamp_utc": "timestamp_utc"}, inplace=True)

    out_path = OUT_DIR / f"liqs_{rule}.csv"
    out.to_csv(out_path, index=False)
    print(f"saved {out_path} (rows={len(out)})")


if __name__ == "__main__":
    main()
