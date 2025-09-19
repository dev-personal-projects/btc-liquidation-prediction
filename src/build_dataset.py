#!/usr/bin/env python3

import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

INTERVAL = os.getenv("AGG_INTERVAL", "1H").upper()
RULE = "1H" if INTERVAL == "1H" else "1D" if INTERVAL == "1D" else None

LIQS_PATH = Path(f"data/processed/liqs_{RULE}.csv") if RULE else None
PRICE_PATH = Path("data/raw/btc_price.csv")
OUT_PATH = Path("data/processed/dataset.csv")


def main() -> None:
    if RULE is None:
        raise ValueError("AGG_INTERVAL must be 1H or 1D")

    if not LIQS_PATH or not LIQS_PATH.exists():
        raise FileNotFoundError(f"Missing input: {LIQS_PATH}")
    if not PRICE_PATH.exists():
        raise FileNotFoundError(f"Missing input: {PRICE_PATH}")


    liq = pd.read_csv(LIQS_PATH, parse_dates=["timestamp_utc"])
    px = pd.read_csv(PRICE_PATH, parse_dates=["timestamp_utc"])


    px = px.sort_values("timestamp_utc")[["timestamp_utc", "close", "volume"]]


    df = pd.merge(liq.sort_values("timestamp_utc"), px, on="timestamp_utc", how="inner")

    if df.empty:
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(OUT_PATH, index=False)
        print(f"saved {OUT_PATH} (rows=0)")
        return


    df = df.sort_values("timestamp_utc").reset_index(drop=True)


    df["net_liq_usd"] = df["short_liq_usd"] - df["long_liq_usd"]
    df["liq_total_usd"] = df["short_liq_usd"] + df["long_liq_usd"]


    df["close_prev"] = df["close"].shift(1)
    df["ret"] = (df["close"] - df["close_prev"]) / df["close_prev"]
    df["close_next"] = df["close"].shift(-1)
    df["ret_next"] = (df["close_next"] - df["close"]) / df["close"]


    df = df.dropna(subset=["ret", "ret_next"]).reset_index(drop=True)


    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"saved {OUT_PATH} (rows={len(df)}, interval={RULE})")


if __name__ == "__main__":
    main()
