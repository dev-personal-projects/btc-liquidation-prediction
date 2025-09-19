#!/usr/bin/env python3
"""
Clean visualization script for liquidation analysis
Generates comprehensive charts mapping liquidations against BTC price movements
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

def load_and_process_data():
    """Load and merge price and liquidation data"""
    
    # Load price data
    price_path = Path("data/raw/btc_price.csv")
    if not price_path.exists():
        print("❌ Price data not found. Run binance_fetch_price.py first.")
        return None
    
    price_df = pd.read_csv(price_path, parse_dates=["timestamp_utc"])
    print(f"📊 Loaded {len(price_df)} price records")
    
    # Load messages
    msg_path = Path("data/raw/telegram_messages.csv")
    if not msg_path.exists():
        print("❌ Message data not found. Run fetch_telegram.py first.")
        return None
    
    msg_df = pd.read_csv(msg_path, parse_dates=["timestamp_utc"])
    print(f"📊 Loaded {len(msg_df)} messages")
    
    # Parse liquidations
    from parse_aggregate import parse_row
    
    parsed = msg_df["text"].apply(parse_row)
    msg_df["side"] = parsed.apply(lambda x: x[0])
    msg_df["amount_usd"] = parsed.apply(lambda x: x[1])
    
    # Filter valid liquidations
    liq_df = msg_df.dropna(subset=["side", "amount_usd"]).copy()
    btc_liq = liq_df[liq_df["text"].str.contains("BTC", case=False, na=False)]
    
    if len(btc_liq) == 0:
        print("⚠️  No BTC liquidations found, using all liquidations")
        btc_liq = liq_df
    
    print(f"📊 Found {len(btc_liq)} liquidations ({len(btc_liq[btc_liq['side']=='long'])} long, {len(btc_liq[btc_liq['side']=='short'])} short)")
    
    # Aggregate by hour
    btc_liq = btc_liq.set_index("timestamp_utc").sort_index()
    
    agg_data = pd.DataFrame({
        "long_liq_usd": btc_liq[btc_liq["side"] == "long"].resample("1H")["amount_usd"].sum(),
        "short_liq_usd": btc_liq[btc_liq["side"] == "short"].resample("1H")["amount_usd"].sum(),
        "long_count": btc_liq[btc_liq["side"] == "long"].resample("1H")["side"].count(),
        "short_count": btc_liq[btc_liq["side"] == "short"].resample("1H")["side"].count(),
    }).fillna(0.0).reset_index()
    
    # Merge with price data
    from pandas import merge_asof
    
    dataset = merge_asof(
        agg_data.sort_values("timestamp_utc"),
        price_df[["timestamp_utc", "close", "volume"]].sort_values("timestamp_utc"),
        on="timestamp_utc",
        direction="nearest",
        tolerance=pd.Timedelta(minutes=30)
    )
    
    dataset = dataset.dropna(subset=["close"])
    
    if len(dataset) == 0:
        print("❌ No matching timestamps found")
        return None
    
    # Engineer features
    dataset["net_liq_usd"] = dataset["short_liq_usd"] - dataset["long_liq_usd"]
    dataset["total_liq_usd"] = dataset["short_liq_usd"] + dataset["long_liq_usd"]
    dataset["price_change"] = dataset["close"].pct_change()
    dataset["price_change_next"] = dataset["close"].pct_change().shift(-1)
    
    print(f"✅ Created dataset with {len(dataset)} records")
    return dataset

def create_timeline_chart(data, save_path):
    """Create price vs liquidations timeline"""
    
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), sharex=True)
    
    # 1. BTC Price
    ax1.plot(data['timestamp_utc'], data['close'], color='#FF6B35', linewidth=2, alpha=0.8)
    ax1.set_ylabel('BTC Price ($)', fontsize=12, color='#FF6B35')
    ax1.tick_params(axis='y', labelcolor='#FF6B35')
    ax1.set_title('BTC Price vs Liquidations Analysis', fontsize=16, fontweight='bold', pad=20)
    ax1.grid(True, alpha=0.3)
    
    # Price range annotations
    price_min, price_max = data['close'].min(), data['close'].max()
    ax1.axhline(y=price_min, color='red', linestyle='--', alpha=0.5, linewidth=1)
    ax1.axhline(y=price_max, color='green', linestyle='--', alpha=0.5, linewidth=1)
    
    # 2. Liquidations
    width = pd.Timedelta(minutes=30)
    ax2.bar(data['timestamp_utc'], data['long_liq_usd'], width=width, 
            alpha=0.7, color='#FF4444', label='Long Liquidations', edgecolor='darkred', linewidth=0.5)
    ax2.bar(data['timestamp_utc'], -data['short_liq_usd'], width=width, 
            alpha=0.7, color='#44AA44', label='Short Liquidations', edgecolor='darkgreen', linewidth=0.5)
    
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.5, linewidth=1)
    ax2.set_ylabel('Liquidation Volume ($)', fontsize=12)
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e6:.1f}M' if abs(x) >= 1e6 else f'${x/1e3:.0f}K'))
    
    # 3. Net Liquidations
    colors = ['#44AA44' if x > 0 else '#FF4444' for x in data['net_liq_usd']]
    ax3.bar(data['timestamp_utc'], data['net_liq_usd'], width=width, 
            alpha=0.7, color=colors, edgecolor='black', linewidth=0.5)
    
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.8, linewidth=1)
    ax3.set_ylabel('Net Liquidations ($)\n(Short - Long)', fontsize=12)
    ax3.set_xlabel('Time (UTC)', fontsize=12)
    ax3.grid(True, alpha=0.3)
    ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e6:.1f}M' if abs(x) >= 1e6 else f'${x/1e3:.0f}K'))
    
    plt.tight_layout()
    plt.xticks(rotation=45)
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()
    print(f"💾 Saved timeline chart: {save_path}")

def create_correlation_chart(data, save_path):
    """Create correlation analysis charts"""
    
    # Calculate correlations
    correlations = {
        'Long Liquidations': data['long_liq_usd'].corr(data['price_change_next']),
        'Short Liquidations': data['short_liq_usd'].corr(data['price_change_next']),
        'Net Liquidations': data['net_liq_usd'].corr(data['price_change_next']),
        'Total Liquidations': data['total_liq_usd'].corr(data['price_change_next'])
    }
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Correlation bars
    corr_names = list(correlations.keys())
    corr_values = [correlations[k] for k in corr_names]
    colors = ['#FF4444', '#44AA44', '#4444FF', '#FF8800']
    
    bars = ax1.bar(range(len(corr_names)), corr_values, color=colors, alpha=0.7, edgecolor='black')
    ax1.set_xticks(range(len(corr_names)))
    ax1.set_xticklabels([name.replace(' ', '\n') for name in corr_names])
    ax1.set_ylabel('Correlation with Next Price Change')
    ax1.set_title('Liquidation-Price Correlations', fontweight='bold')
    ax1.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax1.grid(True, alpha=0.3)
    
    # Add values on bars
    for bar, val in zip(bars, corr_values):
        if not pd.isna(val):
            ax1.text(bar.get_x() + bar.get_width()/2, val + (0.01 if val >= 0 else -0.02),
                    f'{val:.3f}', ha='center', va='bottom' if val >= 0 else 'top', fontweight='bold')
    
    # 2. Scatter plot
    valid_data = data.dropna(subset=['net_liq_usd', 'price_change_next'])
    if len(valid_data) > 0:
        scatter = ax2.scatter(valid_data['net_liq_usd'], valid_data['price_change_next']*100, 
                             c=valid_data['total_liq_usd'], cmap='viridis', alpha=0.7, s=60, 
                             edgecolors='black', linewidth=0.5)
        ax2.set_xlabel('Net Liquidations ($)')
        ax2.set_ylabel('Next Price Change (%)')
        ax2.set_title('Net Liquidations vs Future Price Movement', fontweight='bold')
        ax2.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax2.axvline(x=0, color='red', linestyle='--', alpha=0.5)
        ax2.grid(True, alpha=0.3)
        
        cbar = plt.colorbar(scatter, ax=ax2)
        cbar.set_label('Total Liquidations ($)', rotation=270, labelpad=15)
        ax2.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e6:.1f}M' if abs(x) >= 1e6 else f'${x/1e3:.0f}K'))
    
    # 3. Distribution pie chart
    long_total = data['long_liq_usd'].sum()
    short_total = data['short_liq_usd'].sum()
    
    ax3.pie([long_total, short_total], labels=['Long Liquidations', 'Short Liquidations'], 
            colors=['#FF4444', '#44AA44'], autopct='%1.1f%%', startangle=90, 
            explode=(0.05, 0.05), shadow=True)
    ax3.set_title(f'Total Liquidation Distribution\n${(long_total + short_total):,.0f}', fontweight='bold')
    
    # 4. Cumulative liquidations
    data_sorted = data.sort_values('timestamp_utc')
    ax4.plot(data_sorted['timestamp_utc'], data_sorted['long_liq_usd'].cumsum(), 
             color='#FF4444', linewidth=2, label='Cumulative Long')
    ax4.plot(data_sorted['timestamp_utc'], data_sorted['short_liq_usd'].cumsum(), 
             color='#44AA44', linewidth=2, label='Cumulative Short')
    
    ax4.set_xlabel('Time (UTC)')
    ax4.set_ylabel('Cumulative Liquidations ($)')
    ax4.set_title('Cumulative Liquidation Trends', fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.tick_params(axis='x', rotation=45)
    ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e6:.1f}M' if x >= 1e6 else f'${x/1e3:.0f}K'))
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()
    print(f"💾 Saved correlation chart: {save_path}")

def print_summary(data):
    """Print analysis summary"""
    
    total_liq = data['total_liq_usd'].sum()
    long_liq = data['long_liq_usd'].sum()
    short_liq = data['short_liq_usd'].sum()
    
    print("\n" + "="*60)
    print("📊 LIQUIDATION ANALYSIS SUMMARY")
    print("="*60)
    
    print(f"\n📅 Analysis Period:")
    print(f"   From: {data['timestamp_utc'].min()}")
    print(f"   To:   {data['timestamp_utc'].max()}")
    print(f"   Duration: {len(data)} hours")
    
    print(f"\n💰 Liquidation Summary:")
    print(f"   Total Liquidations: ${total_liq:,.0f}")
    print(f"   Long Liquidations:  ${long_liq:,.0f} ({long_liq/total_liq*100:.1f}%)")
    print(f"   Short Liquidations: ${short_liq:,.0f} ({short_liq/total_liq*100:.1f}%)")
    
    print(f"\n📈 BTC Price Summary:")
    print(f"   Price Range: ${data['close'].min():,.0f} - ${data['close'].max():,.0f}")
    print(f"   Volatility: {data['price_change'].std()*100:.2f}%")
    
    print(f"\n🔍 Key Correlations:")
    correlations = {
        'Net → Future Price': data['net_liq_usd'].corr(data['price_change_next']),
        'Long → Future Price': data['long_liq_usd'].corr(data['price_change_next']),
        'Short → Future Price': data['short_liq_usd'].corr(data['price_change_next'])
    }
    
    for name, corr in correlations.items():
        if not pd.isna(corr):
            strength = "Strong" if abs(corr) > 0.3 else "Moderate" if abs(corr) > 0.1 else "Weak"
            direction = "Positive" if corr > 0 else "Negative"
            print(f"   {name}: {corr:.4f} ({strength} {direction})")
    
    print("\n✅ Analysis Complete!")
    print("="*60)

def main():
    """Main analysis function"""
    
    print("🚀 Starting Liquidation Visualization Analysis")
    print("="*50)
    
    # Load and process data
    data = load_and_process_data()
    if data is None:
        print("❌ Failed to load data")
        return
    
    # Create output directory
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate visualizations
    if len(data) > 0:
        create_timeline_chart(data, output_dir / "liquidation_timeline.png")
        create_correlation_chart(data, output_dir / "correlation_analysis.png")
        print_summary(data)
    else:
        print("❌ No data available for visualization")

if __name__ == "__main__":
    main()