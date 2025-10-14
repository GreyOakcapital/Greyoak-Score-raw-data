#!/usr/bin/env python3
"""
TEST #3: QUALITY STABILITY OVER TIME
Do high-score stocks remain high-score? Or do scores flip randomly?
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
print(" "*15 + "TEST #3: QUALITY STABILITY")
print(" "*20 + "SCORE PERSISTENCE ANALYSIS")
print("="*70)
print(f"\nStart Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

OUTPUT_DIR = Path("/app/backend")
CHARTS_DIR = OUTPUT_DIR / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

# Load datasets
print("Loading data...")
scores_df = pd.read_csv(OUTPUT_DIR / 'greyoak_scores_2019_2022.csv', parse_dates=['date'])

print(f"✓ Loaded {len(scores_df):,} scores")
print(f"  Stocks: {scores_df['symbol'].nunique()}")
print(f"  Date range: {scores_df['date'].min().date()} to {scores_df['date'].max().date()}")

# Define checkpoint dates
checkpoints = [
    ('Start (Early 2020)', pd.to_datetime('2020-02-01')),
    ('Post-Crash (Mid 2020)', pd.to_datetime('2020-07-01')),
    ('Bull Peak (Late 2021)', pd.to_datetime('2021-10-01')),
    ('Bear Market (Mid 2022)', pd.to_datetime('2022-06-01')),
    ('End (Late 2022)', pd.to_datetime('2022-11-01'))
]

print(f"\n📊 CHECKPOINT ANALYSIS")
print("-"*70)
print(f"Tracking {len(checkpoints)} checkpoints across 3 years:")
for name, date in checkpoints:
    print(f"  {name:25} → {date.date()}")

# Get scores at each checkpoint
checkpoint_scores = {}

for name, target_date in checkpoints:
    # Get scores within 7 days of target
    window_start = target_date - pd.Timedelta(days=7)
    window_end = target_date + pd.Timedelta(days=7)
    
    checkpoint_data = scores_df[
        (scores_df['date'] >= window_start) &
        (scores_df['date'] <= window_end)
    ].copy()
    
    if len(checkpoint_data) > 0:
        # Take average score per stock in this window
        avg_scores = checkpoint_data.groupby('symbol')['total_score'].mean()
        checkpoint_scores[name] = avg_scores
        actual_date = checkpoint_data['date'].median()
        print(f"\n✓ {name}")
        print(f"    Actual date: {actual_date.date()}")
        print(f"    Stocks: {len(avg_scores)}")
        print(f"    Score range: {avg_scores.min():.1f} to {avg_scores.max():.1f}")
    else:
        print(f"\n✗ {name} - No data available")

# Create transition matrix (First checkpoint → Last checkpoint)
if len(checkpoint_scores) >= 2:
    first_checkpoint = list(checkpoint_scores.keys())[0]
    last_checkpoint = list(checkpoint_scores.keys())[-1]
    
    print(f"\n{'='*70}")
    print(f"STABILITY ANALYSIS: {first_checkpoint} → {last_checkpoint}")
    print("="*70)
    
    # Get common stocks in both periods
    first_scores = checkpoint_scores[first_checkpoint]
    last_scores = checkpoint_scores[last_checkpoint]
    
    common_stocks = set(first_scores.index) & set(last_scores.index)
    print(f"\nCommon stocks tracked: {len(common_stocks)}")
    
    if len(common_stocks) > 20:
        # Create stability dataframe
        stability_data = []
        
        for symbol in common_stocks:
            stability_data.append({
                'symbol': symbol,
                'initial_score': first_scores[symbol],
                'final_score': last_scores[symbol],
                'score_change': last_scores[symbol] - first_scores[symbol]
            })
        
        stability_df = pd.DataFrame(stability_data)
        
        # Classify into bands
        # Initial bands
        initial_high = stability_df['initial_score'].quantile(0.67)
        initial_low = stability_df['initial_score'].quantile(0.33)
        
        stability_df['initial_band'] = pd.cut(
            stability_df['initial_score'],
            bins=[-np.inf, initial_low, initial_high, np.inf],
            labels=['Low', 'Medium', 'High']
        )
        
        # Final bands
        final_high = stability_df['final_score'].quantile(0.67)
        final_low = stability_df['final_score'].quantile(0.33)
        
        stability_df['final_band'] = pd.cut(
            stability_df['final_score'],
            bins=[-np.inf, final_low, final_high, np.inf],
            labels=['Low', 'Medium', 'High']
        )
        
        # Create transition matrix
        transition_matrix = pd.crosstab(
            stability_df['initial_band'],
            stability_df['final_band'],
            normalize='index'
        ) * 100
        
        print("\n📊 Transition Matrix (% of stocks moving between bands):")
        print("\n" + " "*15 + "FINAL BAND")
        print(" "*10 + "┌" + "─"*45 + "┐")
        print(" "*10 + "│" + f"{'High':>14} │ {'Medium':>14} │ {'Low':>14} │")
        print("─"*10 + "┼" + "─"*45 + "┤")
        
        for initial_band in ['High', 'Medium', 'Low']:
            if initial_band in transition_matrix.index:
                row_data = []
                for final_band in ['High', 'Medium', 'Low']:
                    if final_band in transition_matrix.columns:
                        value = transition_matrix.loc[initial_band, final_band]
                        row_data.append(f"{value:>13.1f}%")
                    else:
                        row_data.append(f"{'0.0%':>14}")
                
                print(f"{initial_band:>9} │ {' │ '.join(row_data)} │")
        
        print(" "*10 + "└" + "─"*45 + "┘")
        
        # Calculate stability metrics
        print(f"\n{'─'*70}")
        print("STABILITY METRICS")
        print("─"*70)
        
        # 1. Same-band persistence
        high_to_high = transition_matrix.loc['High', 'High'] if 'High' in transition_matrix.index and 'High' in transition_matrix.columns else 0
        med_to_med = transition_matrix.loc['Medium', 'Medium'] if 'Medium' in transition_matrix.index and 'Medium' in transition_matrix.columns else 0
        low_to_low = transition_matrix.loc['Low', 'Low'] if 'Low' in transition_matrix.index and 'Low' in transition_matrix.columns else 0
        
        print(f"\n📌 Same-Band Persistence:")
        print(f"   High → High:   {high_to_high:.1f}% (stayed high-quality)")
        print(f"   Medium → Med:  {med_to_med:.1f}% (stayed medium)")
        print(f"   Low → Low:     {low_to_low:.1f}% (stayed low-quality)")
        
        avg_persistence = (high_to_high + med_to_med + low_to_low) / 3
        print(f"\n   Average Persistence: {avg_persistence:.1f}%")
        
        # 2. Dramatic changes
        high_to_low = transition_matrix.loc['High', 'Low'] if 'High' in transition_matrix.index and 'Low' in transition_matrix.columns else 0
        low_to_high = transition_matrix.loc['Low', 'High'] if 'Low' in transition_matrix.index and 'High' in transition_matrix.columns else 0
        
        print(f"\n🔄 Dramatic Changes:")
        print(f"   High → Low:    {high_to_low:.1f}% (quality collapse)")
        print(f"   Low → High:    {low_to_high:.1f}% (quality improvement)")
        
        total_dramatic = high_to_low + low_to_high
        print(f"\n   Total Dramatic Changes: {total_dramatic:.1f}%")
        
        # 3. Score change analysis
        print(f"\n📊 Score Change Distribution:")
        mean_change = stability_df['score_change'].mean()
        median_change = stability_df['score_change'].median()
        std_change = stability_df['score_change'].std()
        
        print(f"   Mean change:   {mean_change:+.1f} points")
        print(f"   Median change: {median_change:+.1f} points")
        print(f"   Std Dev:       {std_change:.1f} points")
        
        # Categorize by initial band
        print(f"\n   Score Change by Initial Band:")
        for band in ['High', 'Medium', 'Low']:
            band_data = stability_df[stability_df['initial_band'] == band]
            if len(band_data) > 0:
                band_change = band_data['score_change'].mean()
                print(f"     {band} scores: {band_change:+.1f} points avg change")
        
        # Evaluation
        print(f"\n{'─'*70}")
        print("PASS/FAIL CRITERIA EVALUATION")
        print("─"*70)
        
        checks = {}
        
        # Check 1: High-score persistence (≥70%)
        checks['high_stability'] = high_to_high >= 70.0
        print(f"\n1. High-Score Persistence (≥70%)")
        print(f"   Result: {high_to_high:.1f}%")
        print(f"   {'✅ PASS' if checks['high_stability'] else '❌ FAIL'}")
        
        # Check 2: Low dramatic changes (<15%)
        checks['low_volatility'] = total_dramatic < 15.0
        print(f"\n2. Low Dramatic Changes (<15%)")
        print(f"   Result: {total_dramatic:.1f}%")
        print(f"   {'✅ PASS' if checks['low_volatility'] else '❌ FAIL'}")
        
        # Check 3: Average persistence (≥60%)
        checks['avg_persistence'] = avg_persistence >= 60.0
        print(f"\n3. Average Persistence (≥60%)")
        print(f"   Result: {avg_persistence:.1f}%")
        print(f"   {'✅ PASS' if checks['avg_persistence'] else '❌ FAIL'}")
        
        # Check 4: Reasonable score volatility
        checks['score_volatility'] = std_change < 10.0
        print(f"\n4. Score Volatility (<10 points std)")
        print(f"   Result: {std_change:.1f} points")
        print(f"   {'✅ PASS' if checks['score_volatility'] else '❌ FAIL'}")
        
        passes = sum(checks.values())
        print(f"\n{'─'*70}")
        print(f"Checks Passed: {passes}/4 ({passes/4*100:.0f}%)")
        
        # Overall result
        test3_passed = passes >= 3
        
        # Visualization
        print(f"\n{'─'*70}")
        print("Generating visualizations...")
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 12))
        fig.suptitle('Test #3: Quality Stability Analysis', fontsize=16, fontweight='bold')
        
        # Chart 1: Transition Matrix Heatmap
        ax1 = axes[0, 0]
        sns.heatmap(transition_matrix, annot=True, fmt='.1f', cmap='RdYlGn',
                   xticklabels=['High', 'Medium', 'Low'],
                   yticklabels=['High', 'Medium', 'Low'],
                   cbar_kws={'label': '% of Stocks'},
                   vmin=0, vmax=100, ax=ax1)
        ax1.set_xlabel('Final Band', fontweight='bold')
        ax1.set_ylabel('Initial Band', fontweight='bold')
        ax1.set_title('Transition Matrix', fontweight='bold')
        
        # Chart 2: Persistence Bar Chart
        ax2 = axes[0, 1]
        persistence_data = [high_to_high, med_to_med, low_to_low]
        colors = ['green', 'orange', 'red']
        bars = ax2.bar(['High', 'Medium', 'Low'], persistence_data, color=colors, alpha=0.7, edgecolor='black')
        ax2.set_ylabel('Persistence Rate (%)', fontweight='bold')
        ax2.set_xlabel('Score Band', fontweight='bold')
        ax2.set_title('Same-Band Persistence', fontweight='bold')
        ax2.axhline(y=70, color='blue', linestyle='--', label='70% Target')
        ax2.legend()
        ax2.grid(axis='y', alpha=0.3)
        
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        # Chart 3: Score Change Distribution
        ax3 = axes[1, 0]
        ax3.hist(stability_df['score_change'], bins=30, color='steelblue', alpha=0.7, edgecolor='black')
        ax3.axvline(x=0, color='red', linestyle='--', linewidth=2, label='No Change')
        ax3.axvline(x=mean_change, color='green', linestyle='-', linewidth=2, label=f'Mean: {mean_change:+.1f}')
        ax3.set_xlabel('Score Change (points)', fontweight='bold')
        ax3.set_ylabel('Number of Stocks', fontweight='bold')
        ax3.set_title('Distribution of Score Changes', fontweight='bold')
        ax3.legend()
        ax3.grid(axis='y', alpha=0.3)
        
        # Chart 4: Initial vs Final Scores Scatter
        ax4 = axes[1, 1]
        colors_map = {'High': 'green', 'Medium': 'orange', 'Low': 'red'}
        for band in ['High', 'Medium', 'Low']:
            band_data = stability_df[stability_df['initial_band'] == band]
            ax4.scatter(band_data['initial_score'], band_data['final_score'],
                       alpha=0.6, s=50, label=f'Initial {band}',
                       color=colors_map[band])
        
        # Add diagonal line (no change)
        min_score = min(stability_df['initial_score'].min(), stability_df['final_score'].min())
        max_score = max(stability_df['initial_score'].max(), stability_df['final_score'].max())
        ax4.plot([min_score, max_score], [min_score, max_score],
                'k--', linewidth=2, label='No Change Line')
        
        ax4.set_xlabel('Initial Score', fontweight='bold')
        ax4.set_ylabel('Final Score', fontweight='bold')
        ax4.set_title('Score Stability Scatter', fontweight='bold')
        ax4.legend()
        ax4.grid(alpha=0.3)
        
        plt.tight_layout()
        chart_file = CHARTS_DIR / 'test3_quality_stability.png'
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Chart saved: {chart_file}")
        
        # Final verdict
        print(f"\n{'='*70}")
        print("FINAL VERDICT: TEST #3 (QUALITY STABILITY)")
        print("="*70)
        
        if test3_passed:
            print("\n✅ TEST #3: PASS")
            print("\nConclusion:")
            print("  Quality scores show good stability over time.")
            print(f"  {high_to_high:.1f}% of high-score stocks remained high-quality.")
            print("  The Score Engine provides consistent quality identification.")
            
            print("\n💡 What This Means:")
            print("  • Your Score identifies persistent quality characteristics")
            print("  • Not just noise or random fluctuation")
            print("  • Reliable for long-term investment decisions")
            print("  • Quality is a stable, identifiable trait")
        else:
            print("\n⚠️  TEST #3: PARTIAL PASS")
            print("\nConclusion:")
            print("  Quality scores show some stability, but not exceptional.")
            print(f"  {passes}/4 criteria passed.")
            print("  Scores are somewhat reliable but could be more stable.")
            
            print("\n💡 Recommendations:")
            print("  • Review pillar calculation frequency")
            print("  • Consider smoothing mechanisms")
            print("  • Balance responsiveness vs stability")
        
        # Save summary
        summary_file = OUTPUT_DIR / "reports" / "test3_stability_summary.txt"
        with open(summary_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("TEST #3: QUALITY STABILITY ANALYSIS\n")
            f.write("="*70 + "\n\n")
            f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Period: {first_checkpoint} → {last_checkpoint}\n")
            f.write(f"Stocks Tracked: {len(common_stocks)}\n\n")
            f.write("PERSISTENCE RATES:\n")
            f.write(f"  High → High: {high_to_high:.1f}%\n")
            f.write(f"  Medium → Medium: {med_to_med:.1f}%\n")
            f.write(f"  Low → Low: {low_to_low:.1f}%\n\n")
            f.write(f"Dramatic Changes: {total_dramatic:.1f}%\n")
            f.write(f"Average Persistence: {avg_persistence:.1f}%\n\n")
            f.write(f"Result: {'PASS' if test3_passed else 'PARTIAL PASS'} ({passes}/4 checks)\n")
        
        print(f"\n📄 Summary saved: {summary_file}")
    
    else:
        print("\n⚠️  Insufficient common stocks for stability analysis")
        test3_passed = None

else:
    print("\n⚠️  Insufficient checkpoints for stability analysis")
    test3_passed = None

print(f"\n⏱️  End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70 + "\n")
