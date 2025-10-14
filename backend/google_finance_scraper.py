#!/usr/bin/env python3
"""
Google Finance Data Scraper
Extracts historical price data from Google Finance pages
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import pandas as pd
import time
from pathlib import Path

CACHE_DIR = Path("/app/backend/validation_data")
CACHE_DIR.mkdir(exist_ok=True)

def extract_historical_data_from_html(html_content):
    """
    Extract historical data from Google Finance HTML
    The data is embedded in JavaScript AF_initDataCallback calls
    """
    # Look for historical data in the JavaScript
    # Pattern: AF_initDataCallback with historical price data
    pattern = r'AF_initDataCallback\({key:\s*[\'"]ds:11[\'"],[^}]+data:(\[.+?\]),'
    matches = re.findall(pattern, html_content, re.DOTALL)
    
    if not matches:
        return None
    
    try:
        # Parse the JSON data
        data_str = matches[0]
        # Fix the data structure (remove trailing commas if any)
        data = json.loads(data_str)
        
        # Navigate the nested structure to find historical prices
        # Structure: [[[[timestamp],[price_data]]...]]
        historical_points = []
        
        if len(data) > 0 and len(data[0]) > 0:
            price_data = data[0][0]
            
            for entry in price_data:
                if len(entry) >= 2:
                    timestamp = entry[0]
                    price_info = entry[1]
                    
                    if len(price_info) > 0:
                        historical_points.append({
                            'timestamp': timestamp,
                            'price': price_info[0] if len(price_info) > 0 else None,
                            'change': price_info[1] if len(price_info) > 1 else None,
                            'change_pct': price_info[2] if len(price_info) > 2 else None,
                        })
        
        return historical_points
    except Exception as e:
        print(f"  Error parsing historical data: {e}")
        return None

def download_google_finance_data(ticker_nse, start_date=None, end_date=None, cache_dir=CACHE_DIR):
    """
    Download stock data from Google Finance
    
    Args:
        ticker_nse: Stock ticker in NSE format (e.g., 'RELIANCE')
        start_date: Not used (Google Finance provides recent data)
        end_date: Not used
        cache_dir: Directory to cache data
    
    Returns:
        pd.DataFrame: Historical data
    """
    cache_file = cache_dir / f"{ticker_nse}_google_finance.csv"
    
    # Check cache
    if cache_file.exists():
        print(f"✓ Loading cached data for {ticker_nse}")
        try:
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return df
        except Exception as e:
            print(f"  Warning: Cache read failed ({e}), re-downloading...")
    
    # Download fresh data
    print(f"↓ Downloading {ticker_nse} from Google Finance...")
    
    # Google Finance URL format
    url = f"https://www.google.com/finance/quote/{ticker_nse}:NSE"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"  ✗ Failed with status {response.status_code}")
            return None
        
        # Extract historical data from HTML
        historical_data = extract_historical_data_from_html(response.text)
        
        if not historical_data or len(historical_data) == 0:
            print(f"  ✗ No historical data found in page")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(historical_data)
        
        # Convert timestamp to datetime
        # Timestamp format: [year, month, day, hour, minute]
        def parse_timestamp(ts):
            if len(ts) >= 5:
                return pd.Timestamp(year=ts[0], month=ts[1], day=ts[2], 
                                   hour=ts[3], minute=ts[4])
            return None
        
        df['datetime'] = df['timestamp'].apply(parse_timestamp)
        df = df.set_index('datetime')
        df = df.dropna(subset=['price'])
        
        # Save to cache
        df.to_csv(cache_file)
        print(f"  ✓ Downloaded {len(df)} datapoints, saved to cache")
        
        # Rate limiting
        time.sleep(2.0)
        
        return df
        
    except Exception as e:
        print(f"  ✗ Download failed for {ticker_nse}: {e}")
        return None

def main():
    """Test the Google Finance scraper"""
    
    print("=" * 70)
    print("GOOGLE FINANCE DATA SCRAPER TEST")
    print("=" * 70)
    print()
    
    # Test with RELIANCE
    test_tickers = ['RELIANCE', 'TCS', 'HDFCBANK']
    
    for ticker in test_tickers:
        print(f"\nTesting: {ticker}")
        print("-" * 70)
        df = download_google_finance_data(ticker)
        
        if df is not None and len(df) > 0:
            print(f"\nData Summary for {ticker}:")
            print(f"  Date range: {df.index[0]} to {df.index[-1]}")
            print(f"  Total points: {len(df)}")
            print(f"  Latest price: {df['price'].iloc[-1]}")
            print(f"\nFirst 5 rows:")
            print(df.head())
        else:
            print(f"  ✗ Failed to get data")
        print()
    
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
