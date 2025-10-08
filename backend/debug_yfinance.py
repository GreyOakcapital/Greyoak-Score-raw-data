#!/usr/bin/env python3
"""
Debug yfinance connectivity
"""

import yfinance as yf
import pandas as pd

def test_yfinance_basic():
    """Test basic yfinance functionality."""
    print("🔍 Testing yfinance connectivity...")
    
    # Test with a simple ticker first
    test_symbols = ["RELIANCE.NS", "TCS.NS", "AAPL"]
    
    for symbol in test_symbols:
        print(f"\nTesting {symbol}:")
        try:
            ticker = yf.Ticker(symbol)
            
            # Try to get info first
            print(f"  Getting info...", end=" ")
            info = ticker.info
            if info:
                print(f"✅ Got info: {info.get('longName', 'Name not found')}")
            else:
                print("❌ No info")
                
            # Try to get history
            print(f"  Getting history...", end=" ")
            hist = ticker.history(period="5d")
            if not hist.empty:
                print(f"✅ Got {len(hist)} days of data")
                print(f"      Latest close: {hist['Close'].iloc[-1]:.2f}")
            else:
                print("❌ No historical data")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test with different periods
    print(f"\n🕐 Testing different time periods for AAPL:")
    periods = ["1d", "5d", "1mo", "3mo"]
    
    for period in periods:
        try:
            ticker = yf.Ticker("AAPL")
            hist = ticker.history(period=period)
            print(f"  {period:4s}: {len(hist)} days of data")
        except Exception as e:
            print(f"  {period:4s}: Error - {e}")

if __name__ == "__main__":
    test_yfinance_basic()