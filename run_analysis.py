#!/usr/bin/env python3
"""
Complete liquidation correlation analysis pipeline.
Runs all steps: fetch telegram → parse → fetch prices → build dataset → analyze correlation
"""

import subprocess
import sys
from pathlib import Path

def run_step(script_path: str, description: str) -> bool:
    """Run a script and return success status."""
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([sys.executable, script_path], 
                              cwd=Path(__file__).parent,
                              check=True, 
                              capture_output=True, 
                              text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False

def main():
    steps = [
        ("src/fetch_telegram.py", "Fetching Telegram messages"),
        ("src/parse_aggregate.py", "Parsing and aggregating liquidations"),
        ("src/binance_fetch_price.py", "Fetching BTC price data"),
        ("src/build_dataset.py", "Building combined dataset"),
        ("src/analyze_correlation.py", "Analyzing liquidation-price correlations")
    ]
    
    print("🚀 Starting Liquidation Correlation Analysis Pipeline")
    
    for script, description in steps:
        if not run_step(script, description):
            print(f"\n❌ Pipeline failed at: {description}")
            return False
    
    print(f"\n{'='*60}")
    print("✅ Pipeline completed successfully!")
    print("📊 Check data/processed/ for results:")
    print("   - correlation_summary.csv")
    print("   - event_study_summary.csv")
    print("   - dataset.csv")
    print(f"{'='*60}")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)