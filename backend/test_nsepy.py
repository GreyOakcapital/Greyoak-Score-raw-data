#!/usr/bin/env python3
"""Test NSEpy for downloading Indian stock data"""

from nsepy import get_history
from datetime import date
import time

print("=" * 70)
print("NSEPY DATA SOURCE TEST")
print("=" * 70)
print()

# Test stocks
test_stocks = ['RELIANCE', 'TCS', 'HDFCBANK']

# Date range: 2020-2022
start = date(2020, 1, 1)
end = date(2022, 12, 31)

print(f"Testing period: {start} to {end}")
print()

for symbol in test_stocks:
    print(f"Testing: {symbol}")
    print("-" * 70)
    
    try:
        # Download data
        print(f"  Downloading...")
        df = get_history(symbol=symbol, start=start, end=end)
        
        if df is not None and len(df) > 0:
            print(f"  ✓ SUCCESS!")
            print(f"    Rows: {len(df)}")
            print(f"    Date range: {df.index[0]} to {df.index[-1]}")
            print(f"    Columns: {list(df.columns)}")
            print(f"    Latest Close: ₹{df['Close'].iloc[-1]:.2f}")
            print(f"\n  Sample data:")
            print(df.head(3))
        else:
            print(f"  ✗ Empty data returned")
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print()
    time.sleep(2)  # Rate limiting

print("=" * 70)
print("TEST COMPLETE")
print("=" * 70)
