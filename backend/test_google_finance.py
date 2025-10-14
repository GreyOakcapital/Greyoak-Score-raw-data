#!/usr/bin/env python3
"""Test Google Finance accessibility and data extraction"""

import requests
from bs4 import BeautifulSoup
import json

print("=" * 70)
print("GOOGLE FINANCE CONNECTIVITY TEST")
print("=" * 70)
print()

# Test 1: Basic connectivity
print("Test 1: Basic Connectivity")
print("-" * 70)
try:
    response = requests.get("https://www.google.com/finance/", timeout=10)
    print(f"  Status Code: {response.status_code}")
    print(f"  Response Size: {len(response.text)} bytes")
    print(f"  ✓ Can reach Google Finance")
except Exception as e:
    print(f"  ✗ Cannot reach Google Finance: {e}")
    exit(1)
print()

# Test 2: Check specific stock page
print("Test 2: Fetch Reliance Stock Page")
print("-" * 70)
# Google Finance format for NSE stocks: /quote/TICKER:NSE
test_url = "https://www.google.com/finance/quote/RELIANCE:NSE"
try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(test_url, headers=headers, timeout=10)
    print(f"  URL: {test_url}")
    print(f"  Status Code: {response.status_code}")
    print(f"  Response Size: {len(response.text)} bytes")
    
    if response.status_code == 200:
        print(f"  ✓ Can access stock page")
        
        # Try to parse some data
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for price data
        price_div = soup.find('div', {'class': 'YMlKec fxKbKc'})
        if price_div:
            print(f"  Current Price Found: {price_div.text}")
        
        # Look for any structured data
        scripts = soup.find_all('script')
        print(f"  Script tags found: {len(scripts)}")
        
        # Save sample HTML for inspection
        with open('/app/backend/google_finance_sample.html', 'w') as f:
            f.write(response.text)
        print(f"  ✓ Sample HTML saved to google_finance_sample.html")
    else:
        print(f"  ✗ Failed with status {response.status_code}")
        
except Exception as e:
    print(f"  ✗ Error: {e}")
print()

# Test 3: Check Nifty 50 index
print("Test 3: Fetch Nifty 50 Index")
print("-" * 70)
nifty_url = "https://www.google.com/finance/quote/NIFTY_50:INDEXNSE"
try:
    response = requests.get(nifty_url, headers=headers, timeout=10)
    print(f"  URL: {nifty_url}")
    print(f"  Status Code: {response.status_code}")
    if response.status_code == 200:
        print(f"  ✓ Can access Nifty index page")
    else:
        print(f"  ✗ Failed with status {response.status_code}")
except Exception as e:
    print(f"  ✗ Error: {e}")
print()

# Test 4: Check available libraries
print("Test 4: Check for Google Finance Libraries")
print("-" * 70)
try:
    import google_finance_data
    print(f"  ✓ google_finance_data library available")
except ImportError:
    print(f"  ✗ google_finance_data not installed")

try:
    from yahoo_fin import stock_info
    print(f"  ✓ yahoo_fin library available (alternative)")
except ImportError:
    print(f"  ✗ yahoo_fin not available")

try:
    import nsepy
    print(f"  ✓ nsepy library available (NSE India)")
except ImportError:
    print(f"  ✗ nsepy not installed")

print()

print("=" * 70)
print("Summary:")
print("  Google Finance is accessible via web scraping")
print("  Historical data would require parsing JavaScript/HTML")
print("  Alternative: Check for dedicated libraries (nsepy, etc.)")
print("=" * 70)
