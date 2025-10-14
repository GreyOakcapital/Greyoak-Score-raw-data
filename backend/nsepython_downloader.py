#!/usr/bin/env python3
"""
Real Data Downloader using nsepython
Downloads actual NSE India stock data for Phase 1 validation
"""

import time
import pandas as pd
from nsepython import *
from pathlib import Path
from datetime import datetime

# Configuration
VALIDATION_DATA_DIR = Path("/app/backend/validation_data")
VALIDATION_DATA_DIR.mkdir(exist_ok=True)

# Phase 1: 10 liquid stocks (no .NS suffix for nsepython)
PHASE1_STOCKS = [
    'RELIANCE', 'TCS', 'HDFCBANK', 'INFY',
    'ICICIBANK', 'ITC', 'SBIN', 'BHARTIARTL',
    'KOTAKBANK', 'LT'
]

# Date range: 2020-2022 (format: "01-01-2020")
START_DATE = "01-01-2020"
END_DATE = "31-12-2022"

def download_stock_data_nsepython(ticker, start_date, end_date, cache_dir, delay=2.0):
    """
    Download historical data using nsepython with caching
    
    Args:
        ticker: Stock ticker (e.g., 'RELIANCE')
        start_date: Start date string (DD-MM-YYYY)
        end_date: End date string (DD-MM-YYYY)
        cache_dir: Directory to cache CSV files
        delay: Delay in seconds between requests
    
    Returns:
        pd.DataFrame: Historical OHLCV data
    """
    cache_file = cache_dir / f"{ticker}_price_data.csv"
    
    # Check cache
    if cache_file.exists():
        print(f"✓ Loading cached data for {ticker}")
        try:
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return df
        except Exception as e:
            print(f"  Warning: Cache read failed ({e}), re-downloading...")
    
    # Download fresh data
    print(f"↓ Downloading {ticker} from NSE...")
    try:
        # equity_history(symbol, series, start, end)
        # Series "EQ" = Equity
        df = equity_history(ticker, "EQ", start_date, end_date)
        
        if df is None or (hasattr(df, 'empty') and df.empty):
            print(f"  ✗ No data returned for {ticker}")
            return None
        
        # Save to cache
        df.to_csv(cache_file)
        print(f"  ✓ Downloaded {len(df)} rows, saved to cache")
        
        # Rate limiting
        time.sleep(delay)
        
        return df
        
    except Exception as e:
        print(f"  ✗ Download failed for {ticker}: {e}")
        return None

def download_nifty_benchmark(start_date, end_date, cache_dir):
    """
    Download Nifty 50 index data
    
    Args:
        start_date: Start date string (DD-MM-YYYY)
        end_date: End date string (DD-MM-YYYY)
        cache_dir: Cache directory
    
    Returns:
        pd.DataFrame: Nifty 50 historical data
    """
    cache_file = cache_dir / "NIFTY50_index_data.csv"
    
    # Check cache
    if cache_file.exists():
        print(f"✓ Loading cached Nifty 50 data")
        try:
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return df
        except Exception as e:
            print(f"  Warning: Cache read failed ({e}), re-downloading...")
    
    print(f"↓ Downloading Nifty 50 index...")
    try:
        # index_history(indexName, start, end)
        df = index_history("NIFTY 50", start_date, end_date)
        
        if df is None or (hasattr(df, 'empty') and df.empty):
            print(f"  ✗ No data returned for Nifty 50")
            return None
        
        # Save to cache
        df.to_csv(cache_file)
        print(f"  ✓ Downloaded {len(df)} rows, saved to cache")
        
        time.sleep(2.0)
        
        return df
        
    except Exception as e:
        print(f"  ✗ Download failed for Nifty 50: {e}")
        return None

def main():
    """Main execution: Download Phase 1 real data"""
    
    print("=" * 70)
    print("PHASE 1: REAL DATA DOWNLOADER (NSEpython)")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Stocks: {len(PHASE1_STOCKS)} liquid stocks")
    print(f"  Period: {START_DATE} to {END_DATE}")
    print(f"  Rate Limit: 2s between requests")
    print(f"  Cache Dir: {VALIDATION_DATA_DIR}")
    print()
    
    # Download Nifty benchmark first
    print("Step 1: Downloading Nifty 50 Benchmark")
    print("-" * 70)
    nifty_data = download_nifty_benchmark(START_DATE, END_DATE, VALIDATION_DATA_DIR)
    if nifty_data is not None:
        print(f"✓ Nifty 50 data: {len(nifty_data)} rows")
        print(f"  Date range: {nifty_data.index[0]} to {nifty_data.index[-1]}")
    else:
        print("✗ Failed to download Nifty 50 data")
    print()
    
    # Download stock price data
    print("Step 2: Downloading Stock Price Data")
    print("-" * 70)
    successful_downloads = []
    failed_downloads = []
    
    for i, ticker in enumerate(PHASE1_STOCKS, 1):
        print(f"[{i}/{len(PHASE1_STOCKS)}] {ticker}")
        data = download_stock_data_nsepython(ticker, START_DATE, END_DATE, VALIDATION_DATA_DIR, 2.0)
        
        if data is not None:
            successful_downloads.append(ticker)
            print(f"  Date range: {data.index[0]} to {data.index[-1]}")
        else:
            failed_downloads.append(ticker)
        print()
    
    # Summary
    print("=" * 70)
    print("DOWNLOAD SUMMARY")
    print("=" * 70)
    print(f"Price Data:")
    print(f"  ✓ Successful: {len(successful_downloads)}/{len(PHASE1_STOCKS)}")
    print(f"  ✗ Failed: {len(failed_downloads)}/{len(PHASE1_STOCKS)}")
    if failed_downloads:
        print(f"    Failed tickers: {', '.join(failed_downloads)}")
    
    print(f"\nBenchmark:")
    print(f"  Nifty 50: {'✓ Downloaded' if nifty_data is not None else '✗ Failed'}")
    
    print(f"\nCache Location: {VALIDATION_DATA_DIR}")
    print(f"Total files: {len(list(VALIDATION_DATA_DIR.glob('*.csv')))}")
    print()
    
    if len(successful_downloads) >= 8:
        print("✓ SUCCESS: Sufficient data downloaded for Phase 1 validation!")
        print("\n🎉 REAL DATA READY! Proceed with score calculation.")
    elif len(successful_downloads) >= 5:
        print("⚠️  WARNING: Partial success - some stocks failed")
        print("   Validation possible but with limited coverage.")
    else:
        print("✗ ERROR: Insufficient data for validation")
    
    print()
    print("Next step: Run phase1_score_calculator.py")
    print("=" * 70)

if __name__ == "__main__":
    main()
