#!/usr/bin/env python3
"""Diagnose yfinance connectivity and data retrieval issues"""

import yfinance as yf
import pandas as pd
import sys

print("=" * 70)
print("YFINANCE DIAGNOSTIC TOOL")
print("=" * 70)
print()

# Test 1: Basic import
print("Test 1: Import Check")
print(f"  yfinance version: {yf.__version__}")
print(f"  pandas version: {pd.__version__}")
print("  ✓ Imports successful")
print()

# Test 2: Simple ticker fetch
print("Test 2: Simple Ticker Fetch (RELIANCE.NS)")
print("-" * 70)
try:
    ticker = yf.Ticker("RELIANCE.NS")
    print(f"  Ticker object created: {ticker}")
    print(f"  Ticker symbol: {ticker.ticker}")
    print("  ✓ Ticker creation successful")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    sys.exit(1)
print()

# Test 3: Get info
print("Test 3: Get Basic Info")
print("-" * 70)
try:
    info = ticker.info
    print(f"  Info keys: {len(info.keys() if info else 0)}")
    if info:
        print(f"  Sample info: longName = {info.get('longName', 'N/A')}")
        print(f"               sector = {info.get('sector', 'N/A')}")
        print(f"               marketCap = {info.get('marketCap', 'N/A')}")
        print("  ✓ Info retrieval successful")
    else:
        print("  ⚠ Info is empty or None")
except Exception as e:
    print(f"  ✗ Failed: {e}")
print()

# Test 4: Historical data with different date ranges
print("Test 4: Historical Data Retrieval")
print("-" * 70)

test_cases = [
    ("1 month", "1mo"),
    ("3 months", "3mo"),
    ("6 months", "6mo"),
    ("1 year", "1y"),
    ("2020-2022", None),  # Custom range
]

for label, period in test_cases:
    try:
        if period:
            df = ticker.history(period=period)
            print(f"  {label} (period={period}):")
        else:
            df = ticker.history(start="2020-01-01", end="2022-12-31")
            print(f"  {label} (start/end dates):")
        
        if df.empty:
            print(f"    ✗ Empty DataFrame returned")
        else:
            print(f"    ✓ {len(df)} rows retrieved")
            print(f"      Date range: {df.index[0]} to {df.index[-1]}")
            print(f"      Columns: {list(df.columns)}")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    print()

# Test 5: Try alternative index
print("Test 5: Try Nifty 50 Index")
print("-" * 70)
try:
    nifty = yf.Ticker("^NSEI")
    df = nifty.history(period="1mo")
    if df.empty:
        print("  ✗ Empty DataFrame for Nifty")
    else:
        print(f"  ✓ {len(df)} rows for Nifty")
        print(f"    Date range: {df.index[0]} to {df.index[-1]}")
except Exception as e:
    print(f"  ✗ Error: {e}")
print()

# Test 6: Try different ticker format
print("Test 6: Try Different Ticker Formats")
print("-" * 70)
test_tickers = [
    "RELIANCE.NS",
    "RELIANCE.BO",  # Bombay instead of NSE
    "INFY",  # US ticker
    "AAPL",  # US stock (control test)
]

for test_ticker in test_tickers:
    try:
        t = yf.Ticker(test_ticker)
        df = t.history(period="1mo")
        if df.empty:
            print(f"  {test_ticker}: ✗ Empty")
        else:
            print(f"  {test_ticker}: ✓ {len(df)} rows")
    except Exception as e:
        print(f"  {test_ticker}: ✗ Error: {e}")
print()

# Test 7: Network connectivity
print("Test 7: Network Connectivity Check")
print("-" * 70)
try:
    import urllib.request
    response = urllib.request.urlopen("https://query1.finance.yahoo.com", timeout=5)
    print(f"  ✓ Can reach Yahoo Finance (status: {response.status})")
except Exception as e:
    print(f"  ✗ Cannot reach Yahoo Finance: {e}")
print()

print("=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
