#!/usr/bin/env python3
"""
Complete GreyOak Dataset - Final Real Data Collection
Sources: Free public data only (NSE, Screener.in, Investing.com, Kaggle)
No yfinance, no synthetic data, no paid APIs
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import time
import requests
from bs4 import BeautifulSoup
import warnings
import json
import re
warnings.filterwarnings('ignore')

# Ensure directories exist
Path('/app/backend/_raw').mkdir(exist_ok=True)
Path('/app/backend/_raw/indices').mkdir(exist_ok=True)
Path('/app/backend/_raw/fundamentals').mkdir(exist_ok=True)
Path('/app/backend/_raw/ownership').mkdir(exist_ok=True)
Path('/app/backend/_raw/corporate_actions').mkdir(exist_ok=True)


def try_kaggle_indices():
    """
    Try to find pre-hosted Nifty indices data on Kaggle or similar
    """
    print("\n1️⃣  Attempting Kaggle/Public Datasets for Sector Indices")
    print("="*70)
    
    # Known public datasets (if available)
    known_sources = {
        'nifty50_kaggle': 'https://www.kaggle.com/datasets/atulanandjha/nifty50-stock-market-data',
        'nse_historical': 'https://archives.nseindia.com/content/indices/ind_close_all_*.csv',
    }
    
    print("   🔍 Checking known public dataset sources...")
    print("   ⚠️  Kaggle requires manual download (API keys)")
    print("\n   📋 Known Datasets:")
    for name, url in known_sources.items():
        print(f"      - {name}: {url}")
    
    print("\n   ⚠️  Automated download not available without API keys")
    print("   → Manual download required")
    
    return None


def scrape_screener_fundamentals_full(tickers, max_stocks=205):
    """
    Scrape quarterly fundamentals from Screener.in
    Gets historical quarterly data, not just latest
    """
    print(f"\n2️⃣  Scraping Quarterly Fundamentals from Screener.in")
    print("="*70)
    print(f"   Target: {len(tickers)} stocks")
    print("   Fetching quarterly historical data...")
    
    all_fundamentals = []
    success_count = 0
    failed_tickers = []
    
    for i, ticker in enumerate(tickers[:max_stocks], 1):
        try:
            url = f'https://www.screener.in/company/{ticker}/consolidated/'
            
            if i % 10 == 0 or i == 1:
                print(f"\n   Progress: {i}/{len(tickers)} - {ticker}", end='')
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Try to find quarterly results table
                quarters_section = soup.find('section', {'id': 'quarters'})
                
                if quarters_section:
                    tables = quarters_section.find_all('table')
                    
                    for table in tables:
                        try:
                            # Parse table using pandas
                            df_table = pd.read_html(str(table))[0]
                            
                            # Extract quarters and metrics
                            # Table structure varies, try to identify columns
                            if len(df_table.columns) > 1:
                                # First column is usually the metric name
                                # Other columns are quarters
                                
                                quarters_row = df_table.columns[1:]  # Quarter headers
                                
                                # Extract key metrics
                                metrics = {}
                                for idx, row in df_table.iterrows():
                                    metric_name = str(row[0]).strip().lower()
                                    
                                    # Map to standardized names
                                    if 'sales' in metric_name or 'revenue' in metric_name:
                                        metrics['sales'] = row[1:]
                                    elif 'expense' in metric_name and 'operating' in metric_name:
                                        metrics['operating_expense'] = row[1:]
                                    elif 'operating profit' in metric_name or 'ebit' in metric_name:
                                        metrics['ebitda'] = row[1:]
                                    elif 'net profit' in metric_name or 'pat' in metric_name:
                                        metrics['net_profit'] = row[1:]
                                    elif 'eps' in metric_name:
                                        metrics['eps'] = row[1:]
                                
                                # Create records for each quarter
                                for j, quarter in enumerate(quarters_row):
                                    try:
                                        # Parse quarter date
                                        quarter_date = pd.to_datetime(quarter, errors='coerce')
                                        
                                        if pd.notna(quarter_date):
                                            record = {
                                                'Ticker': ticker,
                                                'QuarterEnd': quarter_date.date(),
                                                'EPS': metrics.get('eps', [None] * len(quarters_row))[j] if 'eps' in metrics else None,
                                                'PE': None,  # Not in quarterly table
                                                'PB': None,  # Not in quarterly table
                                                'ROE': None,  # Need to calculate or find
                                                'ROCE': None,
                                                'DebtToEquity': None,
                                                'EbitdaMargin': None,
                                                'PatMargin': None,
                                                'DividendYield': None,
                                                'Source': 'screener.in',
                                                'CollectedAt': datetime.now().isoformat()
                                            }
                                            
                                            all_fundamentals.append(record)
                                    except:
                                        pass
                                
                                success_count += 1
                                if i % 10 == 0:
                                    print(f" ✅ ({success_count} ok)")
                                break
                        except Exception as e:
                            pass
                else:
                    if i % 10 == 0:
                        print(" ⚠️  No quarters section")
                    failed_tickers.append(ticker)
            else:
                if i % 10 == 0:
                    print(f" ❌ HTTP {response.status_code}")
                failed_tickers.append(ticker)
            
            # Respectful rate limiting
            time.sleep(2)
            
        except Exception as e:
            if i % 10 == 0:
                print(f" ❌ Error")
            failed_tickers.append(ticker)
    
    print(f"\n\n   ✅ Successfully scraped: {success_count}/{len(tickers)}")
    print(f"   ❌ Failed: {len(failed_tickers)}")
    
    if all_fundamentals:
        df_fund = pd.DataFrame(all_fundamentals)
        
        # Filter to 2020-2022
        df_fund['QuarterEnd'] = pd.to_datetime(df_fund['QuarterEnd'])
        df_fund = df_fund[
            (df_fund['QuarterEnd'] >= '2020-01-01') & 
            (df_fund['QuarterEnd'] <= '2022-12-31')
        ]
        
        return df_fund, failed_tickers
    
    return None, failed_tickers


def scrape_screener_ownership(tickers, max_stocks=205):
    """
    Scrape quarterly ownership from Screener.in shareholding section
    """
    print(f"\n3️⃣  Scraping Quarterly Ownership from Screener.in")
    print("="*70)
    print(f"   Target: {len(tickers)} stocks")
    
    all_ownership = []
    success_count = 0
    
    for i, ticker in enumerate(tickers[:max_stocks], 1):
        try:
            url = f'https://www.screener.in/company/{ticker}/consolidated/'
            
            if i % 10 == 0 or i == 1:
                print(f"\n   Progress: {i}/{len(tickers)} - {ticker}", end='')
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find shareholding section
                shareholding_section = soup.find('section', {'id': 'shareholding'})
                
                if shareholding_section:
                    tables = shareholding_section.find_all('table')
                    
                    for table in tables:
                        try:
                            df_table = pd.read_html(str(table))[0]
                            
                            # Parse shareholding table
                            # Usually has: Quarter, Promoters, FII, DII, Public
                            if len(df_table.columns) >= 4:
                                for idx, row in df_table.iterrows():
                                    try:
                                        quarter = pd.to_datetime(row[0], errors='coerce')
                                        
                                        if pd.notna(quarter):
                                            record = {
                                                'Ticker': ticker,
                                                'QuarterEnd': quarter.date(),
                                                'PromoterPct': row[1] if len(row) > 1 else None,
                                                'FIIPct': row[2] if len(row) > 2 else None,
                                                'DIIPct': row[3] if len(row) > 3 else None,
                                                'RetailPct': row[4] if len(row) > 4 else None,
                                                'PledgePct': None,  # Usually not in this table
                                                'Source': 'screener.in',
                                                'CollectedAt': datetime.now().isoformat()
                                            }
                                            all_ownership.append(record)
                                    except:
                                        pass
                                
                                success_count += 1
                                if i % 10 == 0:
                                    print(f" ✅")
                                break
                        except:
                            pass
                else:
                    if i % 10 == 0:
                        print(" ⚠️  No shareholding")
            
            time.sleep(2)
            
        except Exception as e:
            if i % 10 == 0:
                print(f" ❌ Error")
    
    print(f"\n\n   ✅ Successfully scraped: {success_count}/{len(tickers)}")
    
    if all_ownership:
        df_own = pd.DataFrame(all_ownership)
        
        # Filter to 2020-2022
        df_own['QuarterEnd'] = pd.to_datetime(df_own['QuarterEnd'])
        df_own = df_own[
            (df_own['QuarterEnd'] >= '2020-01-01') & 
            (df_own['QuarterEnd'] <= '2022-12-31')
        ]
        
        return df_own
    
    return None


def create_manual_instructions():
    """
    Create detailed manual download instructions
    """
    print("\n4️⃣  Creating Manual Download Instructions")
    print("="*70)
    
    instructions = """
# MANUAL DATA COLLECTION INSTRUCTIONS

## Sector Indices (Required: 9 indices, 2020-2022)

### Method 1: NSE Official Website (Recommended)
**URL:** https://www1.nseindia.com/products/content/equities/indices/historical_index_data.htm

**Steps for EACH index:**
1. Visit the URL above
2. Select Index: NIFTY 50 (or NIFTY BANK, NIFTY IT, etc.)
3. Select Period: From 01-Jan-2020 To 31-Dec-2022
4. Click "Get Data" button
5. Click "Download file in CSV format"
6. Save as: /app/backend/_raw/indices/NIFTY_<INDEX_NAME>.csv

**Required Indices (9 total):**
- NIFTY 50
- NIFTY BANK
- NIFTY IT
- NIFTY AUTO
- NIFTY PHARMA
- NIFTY METAL
- NIFTY FMCG
- NIFTY ENERGY
- NIFTY PSU BANK

**Time Required:** ~20 minutes (2-3 min per index)

### Method 2: Investing.com (Alternative)
**URL:** https://in.investing.com/indices/india-indices

**Steps:**
1. Search for each Nifty index
2. Click "Historical Data" tab
3. Set date range: 01/01/2020 - 12/31/2022
4. Click "Download Data"
5. Save CSV files

---

## Fundamentals & Ownership (If Automated Scraping Incomplete)

### Method 1: Screener.in Batch Export
**URL:** https://www.screener.in/

**Steps:**
1. For each ticker, visit: https://www.screener.in/company/{TICKER}/consolidated/
2. Scroll to "Quarterly Results" section
3. Copy table data to Excel
4. Paste into fundamentals_template.csv
5. Repeat for "Shareholding Pattern" section → ownership_template.csv

**Time Required:** ~5-10 minutes per stock = 17-34 hours for 205 stocks
**Recommendation:** Start with top 50 stocks for testing

### Method 2: NSE Corporate Filings
**URL:** https://www.nseindia.com/companies-listing/corporate-filings-financial-results

**Steps:**
1. Search for company
2. Download quarterly results PDF/Excel
3. Extract key ratios
4. Fill templates

---

## Corporate Actions

### NSE Corporate Actions
**URL:** https://www.nseindia.com/companies-listing/corporate-filings-actions

**Steps:**
1. Search for company
2. Filter by action type (Bonus, Split, Dividend)
3. Download announcements
4. Extract: Ticker, Date, ActionType, Ratio/Amount
5. Fill template

---

## After Manual Collection

Run this to consolidate:
```bash
python3 consolidate_manual_data.py
```

This will:
1. Read all files from _raw/ folders
2. Combine into final CSVs
3. Validate schema and coverage
4. Generate completion log
    """
    
    instruction_file = Path('/app/backend/MANUAL_COLLECTION_INSTRUCTIONS.md')
    with open(instruction_file, 'w') as f:
        f.write(instructions)
    
    print(f"   ✅ Instructions saved: {instruction_file}")
    
    return instruction_file


def main():
    """Main collection orchestrator"""
    print("="*70)
    print("COMPLETE DATASET - FINAL REAL DATA COLLECTION")
    print("="*70)
    print("\n🎯 Goal: 100% real data for all 6 pillars")
    print("📋 Sources: Free public only (NSE, Screener.in, Kaggle)")
    print("⚠️  Some data may require manual download")
    
    # Load stock list
    df_stocks = pd.read_csv('/app/backend/HISTORICAL_DATA_3_YEARS_205_STOCKS.csv')
    tickers = df_stocks['Ticker'].unique()
    
    print(f"\n📊 Target: {len(tickers)} stocks, 2020-2022")
    
    results = {
        'indices': {'automated': False, 'manual_required': True},
        'fundamentals': {'automated': False, 'records': 0},
        'ownership': {'automated': False, 'records': 0},
        'corporate_actions': {'automated': False, 'manual_required': True}
    }
    
    # 1. Try Kaggle for indices
    print("\n" + "="*70)
    try_kaggle_indices()
    results['indices']['automated'] = False
    
    # 2. Scrape fundamentals
    print("\n" + "="*70)
    print("⏱️  This will take ~10-15 minutes for all stocks...")
    print("   (Respectful 2-second delay between requests)")
    
    input("\nPress Enter to start fundamentals scraping (or Ctrl+C to skip)...")
    
    df_fund, failed_fund = scrape_screener_fundamentals_full(tickers, max_stocks=205)
    
    if df_fund is not None and len(df_fund) > 0:
        # Save
        output_file = Path('/app/backend/fundamentals_quarterly_2020_2022.csv')
        
        # Add header comment
        with open(output_file, 'w') as f:
            f.write(f"# Source: Screener.in quarterly results tables\n")
            f.write(f"# Collection Date: {datetime.now().isoformat()}\n")
            f.write(f"# Coverage: {df_fund['Ticker'].nunique()}/{len(tickers)} stocks\n")
            f.write(f"# URL Pattern: https://www.screener.in/company/{{TICKER}}/consolidated/\n")
            f.write(f"#\n")
            
        df_fund.to_csv(output_file, mode='a', index=False)
        
        print(f"\n✅ Fundamentals saved: {output_file}")
        print(f"   Records: {len(df_fund)}")
        print(f"   Tickers: {df_fund['Ticker'].nunique()}/{len(tickers)}")
        
        results['fundamentals']['automated'] = True
        results['fundamentals']['records'] = len(df_fund)
    
    # 3. Scrape ownership
    print("\n" + "="*70)
    print("⏱️  This will take ~10-15 minutes for all stocks...")
    
    input("\nPress Enter to start ownership scraping (or Ctrl+C to skip)...")
    
    df_own = scrape_screener_ownership(tickers, max_stocks=205)
    
    if df_own is not None and len(df_own) > 0:
        output_file = Path('/app/backend/ownership_quarterly_2020_2022.csv')
        
        with open(output_file, 'w') as f:
            f.write(f"# Source: Screener.in shareholding pattern tables\n")
            f.write(f"# Collection Date: {datetime.now().isoformat()}\n")
            f.write(f"# Coverage: {df_own['Ticker'].nunique()}/{len(tickers)} stocks\n")
            f.write(f"#\n")
        
        df_own.to_csv(output_file, mode='a', index=False)
        
        print(f"\n✅ Ownership saved: {output_file}")
        print(f"   Records: {len(df_own)}")
        print(f"   Tickers: {df_own['Ticker'].nunique()}/{len(tickers)}")
        
        results['ownership']['automated'] = True
        results['ownership']['records'] = len(df_own)
    
    # 4. Create manual instructions
    print("\n" + "="*70)
    instruction_file = create_manual_instructions()
    
    # Final summary
    print("\n" + "="*70)
    print("COLLECTION SUMMARY")
    print("="*70)
    
    print("\n✅ Automated Collection:")
    if results['fundamentals']['automated']:
        print(f"   - Fundamentals: {results['fundamentals']['records']} records")
    if results['ownership']['automated']:
        print(f"   - Ownership: {results['ownership']['records']} records")
    
    print("\n⚠️  Manual Collection Required:")
    if results['indices']['manual_required']:
        print("   - Sector Indices: 9 indices (~20 min)")
    if results['corporate_actions']['manual_required']:
        print("   - Corporate Actions: 205 stocks")
    
    print(f"\n📋 Instructions: {instruction_file}")
    print("\n💡 Next Steps:")
    print("   1. Download sector indices manually (20 min)")
    print("   2. Review automated fundamentals/ownership coverage")
    print("   3. Fill gaps manually if needed")
    print("   4. Run consolidate script to finalize")
    
    return results


if __name__ == "__main__":
    results = main()
