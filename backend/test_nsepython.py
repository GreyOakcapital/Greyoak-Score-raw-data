#!/usr/bin/env python3
"""Test nsepython for downloading Indian stock data"""

from nsepython import *
import time

print("=" * 70)
print("NSEPYTHON DATA SOURCE TEST")
print("=" * 70)
print()

# Test 1: Get current price
print("Test 1: Get Current Stock Quote")
print("-" * 70)
try:
    quote = nse_quote_ltp("RELIANCE")
    print(f"RELIANCE LTP: {quote}")
except Exception as e:
    print(f"Error: {e}")
print()

# Test 2: Get historical data
print("Test 2: Get Historical Data")
print("-" * 70)
try:
    # nsepython can get historical data
    print("Checking available functions...")
    
    # Try equity_history function
    from datetime import datetime, timedelta
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # Last 90 days
    
    print(f"Attempting to fetch RELIANCE data from {start_date.date()} to {end_date.date()}")
    
    # Try different approaches
    try:
        data = equity_history("RELIANCE", "EQ", start_date, end_date)
        print(f"✓ Got data: {type(data)}")
        if hasattr(data, 'head'):
            print(data.head())
    except Exception as e:
        print(f"equity_history failed: {e}")
    
except Exception as e:
    print(f"Error: {e}")
print()

# Test 3: Get Nifty 50 data
print("Test 3: Get Nifty 50 Index")
print("-" * 70)
try:
    nifty = nse_quote_ltp("NIFTY 50")
    print(f"Nifty 50: {nifty}")
except Exception as e:
    print(f"Error: {e}")
print()

print("=" * 70)
print("Exploring nsepython functions...")
print("=" * 70)
import nsepython
print([x for x in dir(nsepython) if not x.startswith('_')])

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
