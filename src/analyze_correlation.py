#!/usr/bin/env python3
"""
Computational analysis of liquidation-price correlations.
Correlates liquidation metrics with BTC price movements.
"""

import os
from pathlib import Path
import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DATASET_PATH = Path("data/processed/dataset.csv")
OUT_DIR = Path("data/processed")
INTERVAL = os.getenv("AGG_INTERVAL", "1H").upper()

def forward_return(close: pd.Series, k: int) -> pd.Series:
    """Forward k-period simple return from time t: (close[t+k] - close[t]) / close[t]."""
    return (close.shift(-k) - close) / close

def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Missing input: {DATASET_PATH}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATASET_PATH, parse_dates=["timestamp_utc"]).sort_values("timestamp_utc")
    needed = {
        "close", "ret_next", "long_liq_usd", "short_liq_usd",
        "net_liq_usd", "liq_total_usd", "long_count", "short_count"
    }
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"dataset missing columns: {sorted(missing)}")

    # === 1) Correlation summary ===
    target = "ret_next"
    predictors = [
        "long_liq_usd", "short_liq_usd", "net_liq_usd", "liq_total_usd",
        "long_count", "short_count"
    ]

    rows = []
    for col in predictors:
        s1, s2 = df[col], df[target]
        # drop rows with NaN in either
        mask = s1.notna() & s2.notna()
        if mask.sum() == 0:
            pearson = np.nan
            spearman = np.nan
        else:
            pearson = s1[mask].corr(s2[mask], method="pearson")
            spearman = s1[mask].corr(s2[mask], method="spearman")
        rows.append({"predictor": col, "pearson": pearson, "spearman": spearman, "n": int(mask.sum())})

    corr_df = pd.DataFrame(rows).sort_values("predictor")
    corr_out = OUT_DIR / "correlation_summary.csv"
    corr_df.to_csv(corr_out, index=False)

    # === 2) Event study (spikes) ===
    # Define horizons based on interval
    horizons = [1, 3, 6, 12, 24] if INTERVAL == "1H" else [1, 2, 3, 5, 10]

    # Spike thresholds (95th percentile of non-zero volumes)
    def q95_nonzero(x: pd.Series) -> float:
        x = x.fillna(0.0)
        x = x[x > 0]
        return float(x.quantile(0.95)) if len(x) else float("inf")

    long_thr = q95_nonzero(df["long_liq_usd"])
    short_thr = q95_nonzero(df["short_liq_usd"])

    df["evt_long_spike"] = df["long_liq_usd"] >= long_thr if np.isfinite(long_thr) else False
    df["evt_short_spike"] = df["short_liq_usd"] >= short_thr if np.isfinite(short_thr) else False

    # For each event set, compute forward returns over horizons
    def summarize_events(flag_col: str, label: str) -> list[dict]:
        idx = df.index[df[flag_col].fillna(False)]
        results = []
        for k in horizons:
            fwd = forward_return(df["close"], k)
            vals = fwd.loc[idx].dropna()
            if len(vals) == 0:
                stats = {"label": label, "horizon_k": k, "n_events": 0,
                         "mean": np.nan, "median": np.nan, "hit_rate_pos": np.nan}
            else:
                stats = {"label": label, "horizon_k": k, "n_events": int(len(vals)),
                         "mean": float(vals.mean()), "median": float(vals.median()),
                         "hit_rate_pos": float((vals > 0).mean())}
            results.append(stats)
        return results

    ev_rows = []
    ev_rows += summarize_events("evt_long_spike", "LONG_SPIKE")
    ev_rows += summarize_events("evt_short_spike", "SHORT_SPIKE")

    events_df = pd.DataFrame(ev_rows).sort_values(["label", "horizon_k"])

    events_out = OUT_DIR / "event_study_summary.csv"
    events_df.to_csv(events_out, index=False)

    # Console summary
    print(f"Saved: {corr_out} and {events_out}")
    print("\nCorrelation (ret_next):")
    print(corr_df.to_string(index=False))
    print("\nEvent study (mean forward returns):")
    print(events_df.pivot(index="horizon_k", columns="label", values="mean").round(4).fillna("—"))

if __name__ == "__main__":
    main()
