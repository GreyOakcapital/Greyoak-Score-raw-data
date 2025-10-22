#!/usr/bin/env python3
"""
Calculate GreyOak Scores for all stocks, all dates
Generates comprehensive historical score dataset for 5 years
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, '/app/backend')

from backtest_predictor_owned import load_csv


def calculate_score_proxy(df: pd.DataFrame, idx: int) -> dict:
    """
    Calculate GreyOak Score proxy for a given date
    
    Args:
        df: Full dataframe with indicators
        idx: Index of current date
    
    Returns:
        Dict with score and components
    """
    if idx < 20:
        return None
    
    row = df.iloc[idx]
    
    # Get values
    close = row['Close']
    rsi = row.get('rsi_14', 50.0)
    dma20 = row.get('dma20', close)
    dma50 = row.get('dma50', close)
    dma200 = row.get('dma200', close)
    high_20 = row.get('high_20', close)
    volume = row.get('volume_ma20', 1)
    
    # Calculate score components
    score = 50.0  # baseline
    
    # Trend component (30 points)
    if not pd.isna(dma20) and dma20 > 0:
        price_vs_dma20 = (close - dma20) / dma20
        score += 15 * np.tanh(price_vs_dma20 / 0.03)
    
    if not pd.isna(dma200) and dma200 > 0:
        price_vs_dma200 = (close - dma200) / dma200
        score += 15 * np.tanh(price_vs_dma200 / 0.05)
    
    # Momentum component (20 points)
    if not pd.isna(rsi):
        rsi_factor = (50 - rsi) / 50  # Positive when oversold
        score += 10 * rsi_factor
    
    # Breakout component (20 points)
    if not pd.isna(high_20) and high_20 > 0:
        breakout = (close - high_20) / high_20
        score += 20 * np.tanh(breakout / 0.01)
    
    score = max(0, min(100, score))
    
    return {
        'date': row['Date'].date(),
        'close': round(close, 2),
        'greyoak_score': round(score, 1),
        'rsi_14': round(rsi, 1) if not pd.isna(rsi) else None,
        'dma20': round(dma20, 2) if not pd.isna(dma20) else None,
        'dma50': round(dma50, 2) if not pd.isna(dma50) else None,
        'dma200': round(dma200, 2) if not pd.isna(dma200) else None,
        'high_20d': round(high_20, 2) if not pd.isna(high_20) else None,
        'price_vs_dma20_pct': round((close - dma20) / dma20 * 100, 2) if not pd.isna(dma20) and dma20 > 0 else None,
        'price_vs_dma200_pct': round((close - dma200) / dma200 * 100, 2) if not pd.isna(dma200) and dma200 > 0 else None
    }


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators to dataframe"""
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    # RSI
    delta = close.diff()
    up = np.where(delta > 0, delta, 0.0)
    dn = np.where(delta < 0, -delta, 0.0)
    ru = pd.Series(up).ewm(alpha=1/14, adjust=False).mean()
    rd = pd.Series(dn).ewm(alpha=1/14, adjust=False).mean().replace(0, np.nan)
    rs = ru / rd
    df['rsi_14'] = (100 - (100 / (1 + rs))).fillna(50.0)
    
    # DMAs
    df['dma20'] = close.rolling(20).mean()
    df['dma50'] = close.rolling(50).mean()
    df['dma200'] = close.rolling(200).mean()
    
    # 20-day high
    df['high_20'] = high.rolling(20).max()
    
    # Volume MA
    if 'Volume' in df.columns:
        df['volume_ma20'] = df['Volume'].rolling(20).mean()
    
    return df


def process_stock(csv_file: Path, output_records: list):
    """Process one stock and append scores to output"""
    ticker = csv_file.stem.replace('_price_data', '')
    
    try:
        # Load data
        df = load_csv(str(csv_file))
        
        if len(df) < 200:
            return 0
        
        # Calculate indicators
        df = calculate_indicators(df)
        
        # Calculate scores for each date
        count = 0
        for idx in range(200, len(df)):  # Start after 200 days for DMA200
            score_data = calculate_score_proxy(df, idx)
            
            if score_data:
                score_data['ticker'] = ticker
                output_records.append(score_data)
                count += 1
        
        return count
    
    except Exception as e:
        print(f"❌ {ticker}: {e}")
        return 0


def main():
    """Calculate scores for all stocks"""
    print("="*70)
    print("GREYOAK SCORE CALCULATION - ALL STOCKS, ALL DATES")
    print("="*70)
    print("\nCalculating historical GreyOak Scores for 205 stocks...")
    print("This will take a few minutes...\n")
    
    data_dir = Path('/app/backend/validation_data_large')
    output_dir = Path('/app/backend/greyoak_scores_historical')
    output_dir.mkdir(exist_ok=True)
    
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return
    
    csv_files = sorted(list(data_dir.glob('*_price_data.csv')))
    print(f"📊 Found {len(csv_files)} stocks\n")
    
    all_scores = []
    total_scores = 0
    
    start_time = datetime.now()
    
    for i, csv_file in enumerate(csv_files, 1):
        ticker = csv_file.stem.replace('_price_data', '')
        
        count = process_stock(csv_file, all_scores)
        total_scores += count
        
        if i % 20 == 0 or i == len(csv_files):
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"✓ Progress: {i}/{len(csv_files)} - {ticker}: {count} scores "
                  f"(Total: {total_scores:,} scores in {elapsed:.0f}s)")
    
    # Save to CSV
    if all_scores:
        print(f"\n💾 Saving {len(all_scores):,} score records to CSV...")
        
        df_scores = pd.DataFrame(all_scores)
        
        # Reorder columns
        cols = ['ticker', 'date', 'close', 'greyoak_score', 'rsi_14', 'dma20', 'dma50', 
                'dma200', 'high_20d', 'price_vs_dma20_pct', 'price_vs_dma200_pct']
        df_scores = df_scores[cols]
        
        # Sort by date and ticker
        df_scores = df_scores.sort_values(['date', 'ticker'])
        
        # Save full dataset
        output_file = output_dir / 'greyoak_scores_all_stocks.csv'
        df_scores.to_csv(output_file, index=False)
        
        print(f"✅ Saved to: {output_file}")
        print(f"   File size: {output_file.stat().st_size / 1024 / 1024:.1f} MB")
        print(f"   Records: {len(df_scores):,}")
        print(f"   Date range: {df_scores['date'].min()} to {df_scores['date'].max()}")
        print(f"   Stocks: {df_scores['ticker'].nunique()}")
        
        # Create summary by ticker
        summary = df_scores.groupby('ticker').agg({
            'greyoak_score': ['mean', 'std', 'min', 'max'],
            'date': ['min', 'max', 'count']
        }).round(2)
        
        summary.columns = ['avg_score', 'std_score', 'min_score', 'max_score', 
                          'start_date', 'end_date', 'total_scores']
        
        summary_file = output_dir / 'greyoak_scores_summary.csv'
        summary.to_csv(summary_file)
        print(f"✅ Saved summary to: {summary_file}")
        
        # Sample data preview
        print(f"\n📊 Sample Data (first 10 rows):")
        print(df_scores.head(10).to_string(index=False))
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n⏱️  Total time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"⚡ Processing speed: {len(df_scores) / elapsed:.0f} scores/second")
        
        # Stats
        print(f"\n📈 Statistics:")
        print(f"   Avg GreyOak Score: {df_scores['greyoak_score'].mean():.1f}")
        print(f"   Score Std Dev: {df_scores['greyoak_score'].std():.1f}")
        print(f"   Score Range: {df_scores['greyoak_score'].min():.1f} - {df_scores['greyoak_score'].max():.1f}")
        
        # Distribution
        print(f"\n📊 Score Distribution:")
        bins = [0, 40, 50, 60, 70, 80, 100]
        labels = ['0-40 (Avoid)', '40-50', '50-60 (Hold)', '60-70 (Buy)', '70-80 (Strong Buy)', '80-100']
        df_scores['score_band'] = pd.cut(df_scores['greyoak_score'], bins=bins, labels=labels)
        dist = df_scores['score_band'].value_counts(sort=False)
        for band, count in dist.items():
            pct = count / len(df_scores) * 100
            print(f"   {band:20} - {count:6,} ({pct:5.1f}%)")
        
        print(f"\n✅ Complete! Data ready for GitHub.")
        print(f"\n💡 To save to GitHub:")
        print("   1. Use the 'Save to GitHub' button in the UI")
        print("   2. Files to commit:")
        print(f"      - {output_file}")
        print(f"      - {summary_file}")
        print(f"      - /app/backend/backtest_results/ (trade data)")
    
    else:
        print("❌ No scores calculated")


if __name__ == "__main__":
    main()
