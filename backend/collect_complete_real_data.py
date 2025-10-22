#!/usr/bin/env python3
"""
Collect Complete Real Data from Public Sources
All pillars: Indices, Fundamentals, Ownership, Corporate Actions
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
warnings.filterwarnings('ignore')

# Install required packages
import subprocess
subprocess.run(['pip', 'install', 'beautifulsoup4', 'lxml', 'requests', 'selenium', '-q'], check=True)


def download_nifty_indices_real():
    """
    Attempt to download sector indices from NSE
    """
    print("\n1️⃣  Downloading Sector Indices from NSE")
    print("="*70)
    
    # NSE indices - will try multiple approaches
    indices_info = {
        'NIFTY 50': 'NIFTY%2050',
        'NIFTY BANK': 'NIFTY%20BANK',
        'NIFTY IT': 'NIFTY%20IT',
        'NIFTY AUTO': 'NIFTY%20AUTO',
        'NIFTY PHARMA': 'NIFTY%20PHARMA',
        'NIFTY METAL': 'NIFTY%20METAL',
        'NIFTY FMCG': 'NIFTY%20FMCG',
        'NIFTY ENERGY': 'NIFTY%20ENERGY'
    }
    
    # Try NSE API approach (often works)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive'
    }
    
    all_indices = []
    success_count = 0
    
    for idx_name, idx_code in indices_info.items():
        try:
            print(f"\n   Attempting {idx_name}...", end='')
            
            # Approach 1: Try Yahoo Finance as fallback (more reliable)
            yahoo_symbols = {
                'NIFTY 50': '^NSEI',
                'NIFTY BANK': '^NSEBANK',
                'NIFTY IT': '^CNXIT',
                'NIFTY AUTO': '^CNXAUTO',
                'NIFTY PHARMA': '^CNXPHARMA',
                'NIFTY METAL': '^CNXMETAL',
                'NIFTY FMCG': '^CNXFMCG',
                'NIFTY ENERGY': '^CNXENERGY'
            }
            
            if idx_name in yahoo_symbols:
                try:
                    import yfinance as yf
                    symbol = yahoo_symbols[idx_name]
                    df = yf.download(symbol, start='2020-01-01', end='2022-12-31', progress=False)
                    
                    if not df.empty:
                        df = df.reset_index()
                        df['Index'] = idx_name
                        df = df.rename(columns={'Adj Close': 'Adj_Close'})
                        df = df[['Index', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                        all_indices.append(df)
                        success_count += 1
                        print(f" ✅ ({len(df)} records)")
                    else:
                        print(" ❌ No data")
                except:
                    print(" ❌ Yahoo Finance failed")
            
            time.sleep(1)  # Rate limiting
            
        except Exception as e:
            print(f" ❌ Error: {str(e)[:50]}")
    
    if all_indices:
        df_indices = pd.concat(all_indices, ignore_index=True)
        df_indices['Date'] = pd.to_datetime(df_indices['Date'])
        df_indices = df_indices.sort_values(['Date', 'Index'])
        
        output_file = Path('/app/backend/sector_indices_2020_2022.csv')
        df_indices.to_csv(output_file, index=False)
        
        print(f"\n✅ Sector Indices Downloaded")
        print(f"   File: {output_file}")
        print(f"   Records: {len(df_indices):,}")
        print(f"   Indices: {df_indices['Index'].nunique()}")
        print(f"   Success Rate: {success_count}/{len(indices_info)}")
        
        return df_indices
    else:
        print("\n❌ Failed to download any indices")
        print("   Manual download required from niftyindices.com")
        return None


def scrape_screener_sample():
    """
    Scrape fundamentals from Screener.in for sample stocks
    Full scraping would take hours - this demonstrates the approach
    """
    print("\n2️⃣  Scraping Fundamentals from Screener.in (Sample)")
    print("="*70)
    
    # Load stock list
    df_stocks = pd.read_csv('/app/backend/HISTORICAL_DATA_3_YEARS_205_STOCKS.csv')
    
    # Sample stocks for demonstration (top 20)
    sample_tickers = df_stocks['Ticker'].unique()[:20]
    
    print(f"\n📊 Processing {len(sample_tickers)} sample stocks...")
    print("   (Full scraping of 205 stocks would take ~2-3 hours)")
    
    all_fundamentals = []
    success_count = 0
    
    for i, ticker in enumerate(sample_tickers, 1):
        try:
            url = f'https://www.screener.in/company/{ticker}/consolidated/'
            
            print(f"   {i}/{len(sample_tickers)} {ticker:12}", end='')
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract key ratios from the top section
                ratios = {}
                
                # Look for ratio boxes
                ratio_sections = soup.find_all('li', class_='flex flex-space-between')
                
                for section in ratio_sections:
                    name_elem = section.find('span', class_='name')
                    value_elem = section.find('span', class_='number')
                    
                    if name_elem and value_elem:
                        name = name_elem.text.strip()
                        value = value_elem.text.strip()
                        ratios[name] = value
                
                if ratios:
                    # Parse values (simplified)
                    record = {
                        'ticker': ticker,
                        'data_date': datetime.now().date(),
                        'source': 'screener.in',
                        'raw_data': json.dumps(ratios)
                    }
                    
                    # Try to extract specific metrics
                    for key in ['Market Cap', 'P/E', 'Book Value', 'Div Yield %', 'ROE', 'ROCE', 'Debt to Equity']:
                        record[key] = ratios.get(key, None)
                    
                    all_fundamentals.append(record)
                    success_count += 1
                    print(f" ✅ ({len(ratios)} metrics)")
                else:
                    print(" ⚠️  No ratios found")
            else:
                print(f" ❌ HTTP {response.status_code}")
            
            time.sleep(2)  # Respectful rate limiting
            
        except Exception as e:
            print(f" ❌ {str(e)[:30]}")
    
    print(f"\n✅ Sample Fundamentals Scraped: {success_count}/{len(sample_tickers)}")
    
    if all_fundamentals:
        df_fund = pd.DataFrame(all_fundamentals)
        
        # Save sample
        output_file = Path('/app/backend/fundamentals_sample_screener.csv')
        df_fund.to_csv(output_file, index=False)
        
        print(f"   File: {output_file}")
        print(f"   Records: {len(df_fund)}")
        
        print("\n⚠️  Note: This is a SAMPLE only")
        print("   Full scraping requires:")
        print("   - Processing all 205 stocks (~2-3 hours)")
        print("   - Quarterly historical data extraction")
        print("   - Proper parsing of financial tables")
        
        return df_fund
    
    return None


def create_manual_collection_templates():
    """
    Create CSV templates for manual data entry
    """
    print("\n3️⃣  Creating Manual Collection Templates")
    print("="*70)
    
    df_stocks = pd.read_csv('/app/backend/HISTORICAL_DATA_3_YEARS_205_STOCKS.csv')
    tickers = df_stocks['Ticker'].unique()
    
    # Quarters for 3 years
    quarters = pd.date_range(start='2020-03-31', end='2022-12-31', freq='Q')
    
    # Fundamentals template
    fund_template = []
    for ticker in tickers[:10]:  # Sample 10
        for quarter in quarters:
            fund_template.append({
                'ticker': ticker,
                'quarter_end': quarter.date(),
                'eps': None,
                'pe_ratio': None,
                'pb_ratio': None,
                'roe_3y': None,
                'roce_3y': None,
                'debt_equity': None,
                'dividend_yield': None,
                'sales_cagr_3y': None,
                'opm': None,
                'market_cap_cr': None,
                'data_source': 'manual_entry',
                'notes': 'Fill from Screener.in or NSE'
            })
    
    df_fund_template = pd.DataFrame(fund_template)
    fund_template_file = Path('/app/backend/fundamentals_template.csv')
    df_fund_template.to_csv(fund_template_file, index=False)
    
    print(f"\n   ✅ Fundamentals Template: {fund_template_file}")
    print(f"      Rows: {len(df_fund_template)} (sample for 10 stocks)")
    print(f"      Instructions: Fill values from Screener.in")
    
    # Ownership template
    own_template = []
    for ticker in tickers[:10]:
        for quarter in quarters:
            own_template.append({
                'ticker': ticker,
                'quarter_end': quarter.date(),
                'promoter_pct': None,
                'promoter_pledge_pct': None,
                'fii_pct': None,
                'dii_pct': None,
                'retail_pct': None,
                'free_float_pct': None,
                'data_source': 'manual_entry',
                'notes': 'Fill from NSE shareholding PDFs'
            })
    
    df_own_template = pd.DataFrame(own_template)
    own_template_file = Path('/app/backend/ownership_template.csv')
    df_own_template.to_csv(own_template_file, index=False)
    
    print(f"\n   ✅ Ownership Template: {own_template_file}")
    print(f"      Rows: {len(df_own_template)} (sample for 10 stocks)")
    print(f"      Instructions: Fill from NSE shareholding reports")
    
    return fund_template_file, own_template_file


def main():
    """Main collection function"""
    print("="*70)
    print("COMPLETE REAL DATA COLLECTION")
    print("="*70)
    print("\n🎯 Goal: Source all missing real data for 6-pillar GreyOak Score")
    print("📋 Sources: Public websites (NSE, Screener.in, Yahoo Finance)")
    print("⚠️  Some data may require manual collection due to website restrictions")
    
    results = {
        'indices': {'status': 'pending', 'file': None, 'records': 0},
        'fundamentals': {'status': 'pending', 'file': None, 'records': 0},
        'ownership': {'status': 'pending', 'file': None, 'records': 0},
        'corporate_actions': {'status': 'pending', 'file': None, 'records': 0}
    }
    
    # 1. Sector Indices
    print("\n" + "="*70)
    df_indices = download_nifty_indices_real()
    if df_indices is not None:
        results['indices']['status'] = 'complete'
        results['indices']['file'] = 'sector_indices_2020_2022.csv'
        results['indices']['records'] = len(df_indices)
    else:
        results['indices']['status'] = 'manual_required'
    
    # 2. Fundamentals (sample scraping)
    print("\n" + "="*70)
    df_fund = scrape_screener_sample()
    if df_fund is not None:
        results['fundamentals']['status'] = 'sample_only'
        results['fundamentals']['file'] = 'fundamentals_sample_screener.csv'
        results['fundamentals']['records'] = len(df_fund)
    else:
        results['fundamentals']['status'] = 'manual_required'
    
    # 3. Templates for manual entry
    print("\n" + "="*70)
    fund_template, own_template = create_manual_collection_templates()
    
    # Summary
    print("\n" + "="*70)
    print("DATA COLLECTION SUMMARY")
    print("="*70)
    
    for category, info in results.items():
        print(f"\n{category.upper()}:")
        print(f"   Status: {info['status']}")
        print(f"   File: {info['file'] or 'N/A'}")
        print(f"   Records: {info['records']}")
    
    print("\n📋 Next Steps:")
    print("\n   ✅ Automated Downloads Complete:")
    if results['indices']['status'] == 'complete':
        print("      - Sector indices downloaded via Yahoo Finance")
    
    print("\n   ⚠️  Manual Collection Required:")
    print("      - Full fundamentals (205 stocks × 12 quarters)")
    print("      - Full ownership (205 stocks × 12 quarters)")
    print("      - Corporate actions")
    
    print("\n   💡 Options:")
    print("      1. Use templates and fill manually from Screener.in")
    print("      2. Pay for API access (Financial Modeling Prep: $29/mo)")
    print("      3. Build robust scrapers (2-3 days development)")
    
    return results


if __name__ == "__main__":
    results = main()
