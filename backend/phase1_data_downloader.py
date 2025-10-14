#!/usr/bin/env python3
"""
Phase 1: Data Downloader for GreyOak Score Validation
Downloads real market data from yfinance with rate limiting and caching.
"""

import os
import time
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
import json

# Configuration
VALIDATION_DATA_DIR = Path("/app/backend/validation_data")
VALIDATION_DATA_DIR.mkdir(exist_ok=True)

# Phase 1: 10 liquid stocks
PHASE1_STOCKS = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 
    'ICICIBANK.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS',
    'KOTAKBANK.NS', 'LT.NS'
]

# Date range: 2020-2022 (3 years)
START_DATE = '2020-01-01'
END_DATE = '2022-12-31'

# Rate limiting: 2 seconds between requests
DELAY_BETWEEN_REQUESTS = 2.0

def download_stock_data(ticker, start_date, end_date, cache_dir, delay=2.0):
    """
    Download historical data for a single stock with caching and rate limiting.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'RELIANCE.NS')
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
        cache_dir: Directory to cache CSV files
        delay: Delay in seconds between requests (default: 2.0)
    
    Returns:
        pd.DataFrame: Historical data with OHLCV
    """
    cache_file = cache_dir / f"{ticker.replace('.NS', '')}_price_data.csv"
    
    # Check if cached data exists
    if cache_file.exists():
        print(f"✓ Loading cached data for {ticker}")
        try:
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return df
        except Exception as e:
            print(f"  Warning: Cache read failed ({e}), re-downloading...")
    
    # Download fresh data
    print(f"↓ Downloading {ticker} from yfinance...")
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date, auto_adjust=False)
        
        if df.empty:
            print(f"  ✗ No data returned for {ticker}")
            return None
        
        # Save to cache
        df.to_csv(cache_file)
        print(f"  ✓ Downloaded {len(df)} rows, saved to cache")
        
        # Rate limiting delay
        time.sleep(delay)
        
        return df
        
    except Exception as e:
        print(f"  ✗ Download failed for {ticker}: {e}")
        return None

def download_fundamentals(ticker, cache_dir):
    """
    Download fundamental data (quarterly financials, balance sheet, etc.)
    
    Args:
        ticker: Stock ticker symbol
        cache_dir: Directory to cache data
    
    Returns:
        dict: Fundamental data with latest metrics
    """
    cache_file = cache_dir / f"{ticker.replace('.NS', '')}_fundamentals.json"
    
    # Check cache
    if cache_file.exists():
        print(f"✓ Loading cached fundamentals for {ticker}")
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"  Warning: Cache read failed ({e}), re-downloading...")
    
    # Download fresh data
    print(f"↓ Downloading fundamentals for {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        
        info = stock.info
        fundamentals = {
            'ticker': ticker,
            'pe_ratio': info.get('trailingPE'),
            'pb_ratio': info.get('priceToBook'),
            'dividend_yield': info.get('dividendYield'),
            'roe': info.get('returnOnEquity'),
            'debt_to_equity': info.get('debtToEquity'),
            'current_ratio': info.get('currentRatio'),
            'profit_margin': info.get('profitMargins'),
            'revenue_growth': info.get('revenueGrowth'),
            'market_cap': info.get('marketCap'),
            'sector': info.get('sector'),
            'industry': info.get('industry'),
        }
        
        # Save to cache
        with open(cache_file, 'w') as f:
            json.dump(fundamentals, f, indent=2)
        
        print(f"  ✓ Fundamentals cached")
        
        # Rate limiting delay
        time.sleep(2.0)
        
        return fundamentals
        
    except Exception as e:
        print(f"  ✗ Fundamentals download failed for {ticker}: {e}")
        return None

def download_nifty_benchmark(start_date, end_date, cache_dir):
    """
    Download Nifty 50 index data for benchmark comparison.
    
    Args:
        start_date: Start date string
        end_date: End date string
        cache_dir: Cache directory
    
    Returns:
        pd.DataFrame: Nifty 50 historical data
    """
    return download_stock_data('^NSEI', start_date, end_date, cache_dir, delay=2.0)

def main():
    """Main execution: Download Phase 1 data"""
    
    print("=" * 70)
    print("PHASE 1: DATA DOWNLOADER FOR GREYOAK SCORE VALIDATION")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Stocks: {len(PHASE1_STOCKS)} liquid stocks")
    print(f"  Period: {START_DATE} to {END_DATE}")
    print(f"  Rate Limit: {DELAY_BETWEEN_REQUESTS}s between requests")
    print(f"  Cache Dir: {VALIDATION_DATA_DIR}")
    print()
    
    # Download Nifty benchmark first
    print("Step 1: Downloading Nifty 50 Benchmark")
    print("-" * 70)
    nifty_data = download_nifty_benchmark(START_DATE, END_DATE, VALIDATION_DATA_DIR)
    if nifty_data is not None:
        print(f"✓ Nifty 50 data: {len(nifty_data)} rows")
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
        data = download_stock_data(ticker, START_DATE, END_DATE, VALIDATION_DATA_DIR, DELAY_BETWEEN_REQUESTS)
        
        if data is not None:
            successful_downloads.append(ticker)
        else:
            failed_downloads.append(ticker)
        print()
    
    # Download fundamentals
    print("Step 3: Downloading Fundamental Data")
    print("-" * 70)
    fundamentals_success = []
    fundamentals_failed = []
    
    for i, ticker in enumerate(successful_downloads, 1):
        print(f"[{i}/{len(successful_downloads)}] {ticker}")
        fundamentals = download_fundamentals(ticker, VALIDATION_DATA_DIR)
        
        if fundamentals is not None:
            fundamentals_success.append(ticker)
        else:
            fundamentals_failed.append(ticker)
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
    
    print(f"\nFundamental Data:")
    print(f"  ✓ Successful: {len(fundamentals_success)}/{len(successful_downloads)}")
    print(f"  ✗ Failed: {len(fundamentals_failed)}/{len(successful_downloads)}")
    if fundamentals_failed:
        print(f"    Failed tickers: {', '.join(fundamentals_failed)}")
    
    print(f"\nBenchmark:")
    print(f"  Nifty 50: {'✓ Downloaded' if nifty_data is not None else '✗ Failed'}")
    
    print(f"\nCache Location: {VALIDATION_DATA_DIR}")
    print(f"Total files: {len(list(VALIDATION_DATA_DIR.glob('*')))}")
    print()
    
    if len(successful_downloads) < 5:
        print("⚠️  WARNING: Less than 5 stocks downloaded successfully!")
        print("   Validation may not be reliable with limited data.")
    elif len(successful_downloads) >= 8:
        print("✓ SUCCESS: Sufficient data downloaded for Phase 1 validation!")
    
    print()
    print("Next step: Run phase1_score_calculator.py")
    print("=" * 70)

if __name__ == "__main__":
    main()
