#!/usr/bin/env python3
"""
Consolidate all raw price data into single CSV for developer
Provides clean OHLCV data for manual GreyOak Score calculation
"""

import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, '/app/backend')
from backtest_predictor_owned import load_csv


def main():
    """Consolidate all raw price data"""
    print("="*70)
    print("RAW DATA CONSOLIDATION - All Stocks OHLCV Data")
    print("="*70)
    
    data_dir = Path('/app/backend/validation_data_large')
    output_dir = Path('/app/backend/raw_data_export')
    output_dir.mkdir(exist_ok=True)
    
    csv_files = sorted(list(data_dir.glob('*_price_data.csv')))
    print(f"\n📊 Found {len(csv_files)} stocks")
    print("🔄 Consolidating raw OHLCV data...\n")
    
    all_data = []
    
    for i, csv_file in enumerate(csv_files, 1):
        ticker = csv_file.stem.replace('_price_data', '')
        
        try:
            df = load_csv(str(csv_file))
            df['Ticker'] = ticker
            
            # Reorder columns
            df = df[['Ticker', 'Date', 'Open', 'High', 'Low', 'Close']]
            
            all_data.append(df)
            
            if i % 20 == 0 or i == len(csv_files):
                print(f"✓ Progress: {i}/{len(csv_files)} - {ticker}: {len(df)} bars")
        
        except Exception as e:
            print(f"❌ {ticker}: {e}")
    
    # Combine all
    print(f"\n💾 Combining all data...")
    df_all = pd.concat(all_data, ignore_index=True)
    df_all = df_all.sort_values(['Date', 'Ticker'])
    
    # Save
    output_file = output_dir / 'all_stocks_ohlc_data.csv'
    df_all.to_csv(output_file, index=False)
    
    print(f"\n✅ Raw data consolidated!")
    print(f"   File: {output_file}")
    print(f"   Size: {output_file.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"   Total Records: {len(df_all):,}")
    print(f"   Stocks: {df_all['Ticker'].nunique()}")
    print(f"   Date Range: {df_all['Date'].min()} to {df_all['Date'].max()}")
    
    # Create metadata
    metadata = []
    for ticker in sorted(df_all['Ticker'].unique()):
        ticker_data = df_all[df_all['Ticker'] == ticker]
        metadata.append({
            'ticker': ticker,
            'start_date': ticker_data['Date'].min(),
            'end_date': ticker_data['Date'].max(),
            'total_bars': len(ticker_data),
            'avg_close': round(ticker_data['Close'].mean(), 2),
            'min_close': round(ticker_data['Close'].min(), 2),
            'max_close': round(ticker_data['Close'].max(), 2)
        })
    
    df_meta = pd.DataFrame(metadata)
    meta_file = output_dir / 'data_metadata.csv'
    df_meta.to_csv(meta_file, index=False)
    
    print(f"✅ Metadata saved: {meta_file}")
    
    # Sample preview
    print(f"\n📊 Sample Data (first 10 rows):")
    print(df_all.head(10).to_string(index=False))
    
    print(f"\n📊 Sample Metadata:")
    print(df_meta.head(10).to_string(index=False))
    
    print(f"\n✅ Data ready for your developer!")
    print(f"\nFiles to save to GitHub:")
    print(f"   1. {output_file} - Complete OHLCV data (8.5 MB)")
    print(f"   2. {meta_file} - Metadata summary")


if __name__ == "__main__":
    main()
