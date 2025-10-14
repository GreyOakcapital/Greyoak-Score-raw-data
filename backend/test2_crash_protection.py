#!/usr/bin/env python3
"""
TEST #2: DEFENSIVE QUALITY - MARCH 2020 CRASH
Does GreyOak Score protect capital during market crashes?
"""

import sys
sys.path.insert(0, '/app/backend')

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
plt.style.use('seaborn-v0_8-darkgrid')

# Load data
print("="*70)
print(" "*15 + "TEST #2: DEFENSIVE QUALITY")
print(" "*20 + "MARCH 2020 CRASH TEST")
print("="*70)
print(f"\nStart Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

OUTPUT_DIR = Path("/app/backend")
CHARTS_DIR = OUTPUT_DIR / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

# Load datasets
print("Loading data...")
scores_df = pd.read_csv(OUTPUT_DIR / 'greyoak_scores_2019_2022.csv', parse_dates=['date'])
prices_df = pd.read_csv(OUTPUT_DIR / 'stock_prices_2019_2022.csv', parse_dates=['date'])

print(f"✓ Loaded {len(scores_df):,} scores")
print(f"✓ Loaded {len(prices_df):,} price records")

# Define crash period
crash_start = pd.to_datetime('2020-02-24')  # Start of COVID crash
crash_end = pd.to_datetime('2020-03-24')    # Bottom of crash (~1 month)
pre_crash = pd.to_datetime('2020-02-14')    # 10 days before to classify stocks

print(f"\n📊 CRASH PERIOD ANALYSIS")
print("-"*70)
print(f"Pre-crash classification: {pre_crash.date()}")
print(f"Crash period: {crash_start.date()} to {crash_end.date()}")
print(f"Duration: ~1 month")

# Get pre-crash scores to classify stocks
pre_crash_scores = scores_df[
    (scores_df['date'] >= pre_crash - pd.Timedelta(days=7)) &
    (scores_df['date'] <= pre_crash + pd.Timedelta(days=7))
].copy()

# Average score per stock in pre-crash period
stock_avg_scores = pre_crash_scores.groupby('symbol')['total_score'].mean()

# Classify into bands
high_threshold = stock_avg_scores.quantile(0.67)
low_threshold = stock_avg_scores.quantile(0.33)

high_stocks = stock_avg_scores[stock_avg_scores >= high_threshold].index.tolist()
medium_stocks = stock_avg_scores[
    (stock_avg_scores < high_threshold) & (stock_avg_scores >= low_threshold)
].index.tolist()
low_stocks = stock_avg_scores[stock_avg_scores < low_threshold].index.tolist()

print(f"\n📊 Stock Classification (based on pre-crash scores):")
print(f"   High Score:   {len(high_stocks)} stocks (≥{high_threshold:.1f})")
print(f"   Medium Score: {len(medium_stocks)} stocks")
print(f"   Low Score:    {len(low_stocks)} stocks (≤{low_threshold:.1f})")

# Calculate drawdowns for each stock
print(f"\n📉 CALCULATING CRASH DRAWDOWNS")
print("-"*70)

def calculate_stock_drawdown(symbol, start_date, end_date):
    """Calculate drawdown for a single stock"""
    stock_prices = prices_df[
        (prices_df['symbol'] == symbol) &
        (prices_df['date'] >= start_date) &
        (prices_df['date'] <= end_date)
    ].copy()
    
    if len(stock_prices) < 5:
        return None
    
    # Get peak and trough
    peak_price = stock_prices['close'].max()
    trough_price = stock_prices['close'].min()
    
    # Calculate drawdown
    drawdown = ((trough_price - peak_price) / peak_price) * 100
    
    # Also calculate entry to exit
    if len(stock_prices) > 0:
        entry_price = stock_prices.iloc[0]['close']
        exit_price = stock_prices.iloc[-1]['close']
        period_return = ((exit_price - entry_price) / entry_price) * 100
    else:
        period_return = None
    
    return {
        'max_drawdown': drawdown,
        'period_return': period_return,
        'peak_price': peak_price,
        'trough_price': trough_price
    }

# Calculate for all stocks
drawdowns_data = []

for stocks_list, band_name in [(high_stocks, 'High'), (medium_stocks, 'Medium'), (low_stocks, 'Low')]:
    print(f"\nProcessing {band_name} Score stocks...")
    
    for symbol in stocks_list:
        dd = calculate_stock_drawdown(symbol, crash_start, crash_end)
        if dd:
            drawdowns_data.append({
                'symbol': symbol,
                'band': band_name,
                'max_drawdown': dd['max_drawdown'],
                'period_return': dd['period_return']
            })
            print(f"  {symbol}: {dd['max_drawdown']:.1f}%")

drawdowns_df = pd.DataFrame(drawdowns_data)

# Calculate band statistics
print(f"\n{'='*70}")
print("CRASH PROTECTION RESULTS")
print("="*70)

band_stats = drawdowns_df.groupby('band').agg({
    'max_drawdown': ['mean', 'median', 'std', 'min', 'max'],
    'period_return': ['mean', 'median'],
    'symbol': 'count'
}).round(2)

print("\n📊 Drawdown Statistics by Score Band:")
print("┌────────────┬───────────────┬─────────────┬────────────┬──────────┬──────────┬───────┐")
print("│ Score Band │ Avg Drawdown  │ Med Drawdown│ Std Dev    │ Best     │ Worst    │ Count │")
print("├────────────┼───────────────┼─────────────┼────────────┼──────────┼──────────┼───────┤")

results = {}
for band in ['High', 'Medium', 'Low']:
    if band in drawdowns_df['band'].values:
        band_data = drawdowns_df[drawdowns_df['band'] == band]
        avg_dd = band_data['max_drawdown'].mean()
        med_dd = band_data['max_drawdown'].median()
        std_dd = band_data['max_drawdown'].std()
        best_dd = band_data['max_drawdown'].max()  # Least negative
        worst_dd = band_data['max_drawdown'].min()  # Most negative
        count = len(band_data)
        
        results[band] = {
            'avg': avg_dd,
            'median': med_dd,
            'std': std_dd,
            'best': best_dd,
            'worst': worst_dd,
            'count': count
        }
        
        print(f"│ {band:10} │ {avg_dd:>12.1f}% │ {med_dd:>11.1f}% │ {std_dd:>9.1f}% │ {best_dd:>7.1f}% │ {worst_dd:>7.1f}% │ {count:>5} │")

print("└────────────┴───────────────┴─────────────┴────────────┴──────────┴──────────┴───────┘")

# Calculate protection value
if 'High' in results and 'Low' in results:
    protection = results['Low']['avg'] - results['High']['avg']
    protection_pct = (protection / abs(results['Low']['avg'])) * 100
    
    print(f"\n{'─'*70}")
    print("💡 CRASH PROTECTION ANALYSIS")
    print("─"*70)
    print(f"\nHigh Score Drawdown:  {results['High']['avg']:.1f}%")
    print(f"Low Score Drawdown:   {results['Low']['avg']:.1f}%")
    print(f"\n🛡️  PROTECTION VALUE:   {protection:.1f} percentage points")
    print(f"                       (High-score stocks fell {abs(protection):.1f}% LESS)")
    print(f"\n📊 Relative Protection: {protection_pct:.1f}% better than low-score")
    
    # Interpret results
    print(f"\n{'─'*70}")
    print("INTERPRETATION:")
    print("─"*70)
    
    if protection >= 5.0:
        print("✅ EXCELLENT PROTECTION")
        print(f"   High-score stocks provided {protection:.1f}pp downside protection.")
        print("   This is MATERIAL and VALUABLE for risk management.")
        interpretation = "PASS"
    elif protection >= 3.0:
        print("✅ GOOD PROTECTION")
        print(f"   High-score stocks provided {protection:.1f}pp downside protection.")
        print("   This is meaningful, though not exceptional.")
        interpretation = "PASS"
    elif protection >= 1.0:
        print("⚠️  MODEST PROTECTION")
        print(f"   High-score stocks provided only {protection:.1f}pp protection.")
        print("   Better than nothing, but not a strong defensive edge.")
        interpretation = "MARGINAL"
    else:
        print("❌ NO MEANINGFUL PROTECTION")
        print(f"   High-score stocks fell only {protection:.1f}pp less.")
        print("   Quality did not provide significant crash protection.")
        interpretation = "FAIL"
    
    # Volatility check
    if 'High' in results and 'Low' in results:
        vol_diff = results['Low']['std'] - results['High']['std']
        print(f"\n📊 Volatility Analysis:")
        print(f"   High Score Std Dev: {results['High']['std']:.1f}%")
        print(f"   Low Score Std Dev:  {results['Low']['std']:.1f}%")
        if vol_diff > 2.0:
            print(f"   ✅ High-score stocks were more stable (lower volatility)")
        else:
            print(f"   ⚠️  Similar volatility across bands")

# Visualization
print(f"\n{'─'*70}")
print("Generating visualization...")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('March 2020 Crash: Defensive Quality Test', fontsize=16, fontweight='bold')

# Chart 1: Average Drawdown by Band
bands = ['High', 'Medium', 'Low']
avg_drawdowns = [results[b]['avg'] for b in bands if b in results]
colors = ['green', 'orange', 'red']

bars = ax1.bar(bands, avg_drawdowns, color=colors, alpha=0.7, edgecolor='black')
ax1.set_ylabel('Average Drawdown (%)', fontweight='bold')
ax1.set_xlabel('Score Band', fontweight='bold')
ax1.set_title('Average Drawdown by Score Band', fontweight='bold')
ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax1.grid(axis='y', alpha=0.3)

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.1f}%', ha='center', va='top' if height < 0 else 'bottom',
            fontweight='bold', fontsize=12)

# Add protection annotation
if len(avg_drawdowns) >= 2:
    ax1.annotate('', xy=(2, avg_drawdowns[2]), xytext=(0, avg_drawdowns[0]),
                arrowprops=dict(arrowstyle='<->', color='blue', lw=2))
    mid_y = (avg_drawdowns[0] + avg_drawdowns[2]) / 2
    ax1.text(1, mid_y, f'{protection:.1f}pp\nprotection', 
            ha='center', va='center', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

# Chart 2: Distribution (Box plot)
ax2.boxplot([drawdowns_df[drawdowns_df['band'] == b]['max_drawdown'].values 
             for b in bands if b in drawdowns_df['band'].values],
            labels=bands,
            patch_artist=True,
            boxprops=dict(facecolor='lightblue', alpha=0.7))

ax2.set_ylabel('Drawdown (%)', fontweight='bold')
ax2.set_xlabel('Score Band', fontweight='bold')
ax2.set_title('Drawdown Distribution', fontweight='bold')
ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax2.grid(axis='y', alpha=0.3)

plt.tight_layout()
chart_file = CHARTS_DIR / 'test2_crash_protection.png'
plt.savefig(chart_file, dpi=300, bbox_inches='tight')
plt.close()

print(f"✅ Chart saved: {chart_file}")

# Final verdict
print(f"\n{'='*70}")
print("FINAL VERDICT: TEST #2 (DEFENSIVE QUALITY)")
print("="*70)

if interpretation == "PASS":
    print("\n✅ TEST #2: PASS")
    print("\nConclusion:")
    print("  The GreyOak Score Engine provides MATERIAL crash protection.")
    print(f"  High-score stocks fell {abs(protection):.1f}% less during the March 2020 crash.")
    print("  This is a VALUABLE defensive characteristic for risk management.")
    
    print("\n💡 What This Means:")
    print("  • Your Score identifies safer companies (not just quality)")
    print("  • Risk-adjusted returns should be better")
    print("  • Lower drawdowns = less stress, better sleep")
    print("  • This edge is REAL and MATERIAL")

elif interpretation == "MARGINAL":
    print("\n⚠️  TEST #2: MARGINAL PASS")
    print("\nConclusion:")
    print("  The Score provides some crash protection, but it's modest.")
    print(f"  High-score stocks fell {abs(protection):.1f}% less - not a strong edge.")
    print("  Consider tuning Quality/Risk pillars for better defensive characteristics.")

else:
    print("\n❌ TEST #2: FAIL")
    print("\nConclusion:")
    print("  The Score did NOT provide meaningful crash protection.")
    print("  High-score and low-score stocks fell similarly.")
    print("  Recommendation: Review and strengthen defensive pillars.")

print(f"\n⏱️  End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70 + "\n")

# Save summary to file
summary_file = OUTPUT_DIR / "reports" / "test2_crash_protection_summary.txt"
with open(summary_file, 'w') as f:
    f.write("="*70 + "\n")
    f.write("TEST #2: DEFENSIVE QUALITY - MARCH 2020 CRASH\n")
    f.write("="*70 + "\n\n")
    f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Crash Period: {crash_start.date()} to {crash_end.date()}\n")
    f.write(f"Stocks Tested: {len(drawdowns_df)}\n\n")
    f.write("RESULTS:\n")
    f.write("-"*70 + "\n")
    for band in ['High', 'Medium', 'Low']:
        if band in results:
            f.write(f"{band} Score: {results[band]['avg']:.1f}% average drawdown\n")
    f.write(f"\nProtection Value: {protection:.1f} percentage points\n")
    f.write(f"Result: {interpretation}\n")

print(f"📄 Summary saved: {summary_file}\n")
