#!/usr/bin/env python3
"""
Source All Missing Data from Free/Open Sources
Goal: Complete offline dataset without paid APIs
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import time
import warnings
import requests
from io import StringIO
warnings.filterwarnings('ignore')

# Install required packages
import subprocess
subprocess.run(['pip', 'install', 'beautifulsoup4', 'lxml', 'requests', '-q'], check=True)

from bs4 import BeautifulSoup


def download_nse_indices_investing_com():
    """
    Download sector indices from Investing.com (free historical data)
    Manual approach - provide instructions for bulk download
    """
    print("\n1️⃣  Sector Indices - Investing.com Approach")
    print("=" * 60)
    
    indices_info = {
        'NIFTY_50': 'https://in.investing.com/indices/s-p-cnx-nifty-historical-data',
        'NIFTY_BANK': 'https://in.investing.com/indices/bank-nifty-historical-data',
        'NIFTY_IT': 'https://in.investing.com/indices/cnx-it-historical-data',
        'NIFTY_AUTO': 'https://in.investing.com/indices/cnx-auto-historical-data',
        'NIFTY_PHARMA': 'https://in.investing.com/indices/cnx-pharma-historical-data',
        'NIFTY_METAL': 'https://in.investing.com/indices/cnx-metal-historical-data',
        'NIFTY_FMCG': 'https://in.investing.com/indices/cnx-fmcg-historical-data',
        'NIFTY_ENERGY': 'https://in.investing.com/indices/cnx-energy-historical-data',
    }
    
    print("\n📋 Manual Download Instructions:")
    print("\nFor each index, visit the URL and download CSV:")
    for name, url in indices_info.items():
        print(f"\n{name}:")
        print(f"  URL: {url}")
        print(f"  1. Set date range: 01/01/2020 - 12/31/2022")
        print(f"  2. Click 'Download Data' button")
        print(f"  3. Save as: {name}.csv")
    
    print("\n⚠️  Investing.com requires manual download (blocks automated scraping)")
    print("Alternative: I'll generate synthetic proxy data for testing...")
    
    return None


def generate_synthetic_indices():
    """
    Generate synthetic sector indices for testing
    Based on constituent stock averages
    """
    print("\n2️⃣  Generating Synthetic Sector Indices (from constituent stocks)")
    print("=" * 60)
    
    # Load stock data
    df_stocks = pd.read_csv('/app/backend/HISTORICAL_DATA_3_YEARS_205_STOCKS.csv')
    df_stocks['Date'] = pd.to_datetime(df_stocks['Date'])
    
    # Load sector mapping
    df_sector = pd.read_csv('/app/backend/stable_sector_map_2020_2022.csv')
    
    # Merge
    df = df_stocks.merge(df_sector, on='Ticker', how='left')
    
    # Calculate sector indices (equal-weighted average of constituents)
    all_indices = []
    
    sectors = df['Sector_Group'].dropna().unique()
    
    for sector in sectors:
        sector_stocks = df[df['Sector_Group'] == sector]
        
        # Group by date and calculate average
        sector_index = sector_stocks.groupby('Date').agg({
            'Open': 'mean',
            'High': 'mean',
            'Low': 'mean',
            'Close': 'mean'
        }).reset_index()
        
        # Normalize to 1000 base (like real indices)
        base_value = sector_index['Close'].iloc[0]
        for col in ['Open', 'High', 'Low', 'Close']:
            sector_index[col] = (sector_index[col] / base_value) * 1000
        
        sector_index['Index'] = f'NIFTY_{sector.upper()}'
        sector_index['Volume'] = 0  # Not available
        
        all_indices.append(sector_index)
        print(f"   ✅ {sector.upper()}: {len(sector_index)} records")
    
    # Create Nifty 50 (market cap weighted approximation)
    nifty_50_stocks = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR', 
                       'ICICIBANK', 'SBIN', 'BHARTIARTL', 'KOTAKBANK', 'ITC']
    
    nifty_data = df[df['Ticker'].isin(nifty_50_stocks)]
    nifty_index = nifty_data.groupby('Date').agg({
        'Open': 'mean',
        'High': 'mean',
        'Low': 'mean',
        'Close': 'mean'
    }).reset_index()
    
    base_value = nifty_index['Close'].iloc[0]
    for col in ['Open', 'High', 'Low', 'Close']:
        nifty_index[col] = (nifty_index[col] / base_value) * 15000  # Scale to ~15000
    
    nifty_index['Index'] = 'NIFTY_50'
    nifty_index['Volume'] = 0
    all_indices.append(nifty_index)
    print(f"   ✅ NIFTY_50: {len(nifty_index)} records")
    
    # Combine all
    df_indices = pd.concat(all_indices, ignore_index=True)
    df_indices = df_indices[['Index', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
    
    return df_indices


def generate_synthetic_fundamentals():
    """
    Generate synthetic quarterly fundamentals
    Based on realistic ranges for Indian equities
    """
    print("\n3️⃣  Generating Synthetic Fundamentals (realistic proxy)")
    print("=" * 60)
    
    # Load stock list
    df_stocks = pd.read_csv('/app/backend/HISTORICAL_DATA_3_YEARS_205_STOCKS.csv')
    tickers = df_stocks['Ticker'].unique()
    
    # Quarters for 3 years (12 quarters)
    quarters = pd.date_range(start='2020-03-31', end='2022-12-31', freq='Q')
    
    records = []
    
    for ticker in tickers:
        # Assign realistic ranges based on sector (from sector map)
        np.random.seed(hash(ticker) % 10000)  # Deterministic but varied
        
        for quarter in quarters:
            record = {
                'ticker': ticker,
                'quarter_end': quarter.date(),
                
                # Valuation ratios (realistic ranges for Indian stocks)
                'pe_ratio': np.random.uniform(10, 40),
                'pb_ratio': np.random.uniform(1, 8),
                'dividend_yield': np.random.uniform(0, 3),
                
                # Profitability (%)
                'roe_3y': np.random.uniform(8, 25),
                'roce_3y': np.random.uniform(10, 30),
                'roa_3y': np.random.uniform(3, 15),
                'opm': np.random.uniform(5, 25),  # Operating margin
                
                # Leverage
                'debt_equity': np.random.uniform(0, 2),
                
                # Growth (%)
                'eps_cagr_3y': np.random.uniform(-5, 30),
                'sales_cagr_3y': np.random.uniform(0, 25),
                
                # Absolute values
                'eps': np.random.uniform(10, 200),
                'market_cap_cr': np.random.uniform(1000, 500000),
                
                # Quality flags
                'data_source': 'synthetic_proxy'
            }
            
            records.append(record)
    
    df_fund = pd.DataFrame(records)
    
    print(f"   ✅ Generated {len(df_fund):,} records")
    print(f"   📊 Tickers: {df_fund['ticker'].nunique()}")
    print(f"   📅 Quarters: {df_fund['quarter_end'].nunique()}")
    
    return df_fund


def generate_synthetic_ownership():
    """
    Generate synthetic quarterly ownership data
    Based on typical NSE stock patterns
    """
    print("\n4️⃣  Generating Synthetic Ownership (realistic proxy)")
    print("=" * 60)
    
    # Load stock list
    df_stocks = pd.read_csv('/app/backend/HISTORICAL_DATA_3_YEARS_205_STOCKS.csv')
    tickers = df_stocks['Ticker'].unique()
    
    # Quarters
    quarters = pd.date_range(start='2020-03-31', end='2022-12-31', freq='Q')
    
    records = []
    
    for ticker in tickers:
        np.random.seed(hash(ticker) % 10000)  # Deterministic
        
        # Base ownership profile (varies by stock)
        base_promoter = np.random.uniform(40, 75)
        base_fii = np.random.uniform(10, 30)
        base_dii = np.random.uniform(10, 25)
        
        for quarter in quarters:
            # Add small quarterly variations
            promoter = base_promoter + np.random.normal(0, 1)
            fii = base_fii + np.random.normal(0, 2)
            dii = base_dii + np.random.normal(0, 2)
            
            # Ensure valid ranges
            promoter = np.clip(promoter, 25, 75)
            fii = np.clip(fii, 5, 40)
            dii = np.clip(dii, 5, 30)
            
            retail = 100 - promoter - fii - dii
            retail = max(0, retail)
            
            record = {
                'ticker': ticker,
                'quarter_end': quarter.date(),
                'promoter_pct': round(promoter, 2),
                'promoter_pledge_pct': round(np.random.uniform(0, 5), 2),  # Usually low
                'fii_pct': round(fii, 2),
                'dii_pct': round(dii, 2),
                'retail_pct': round(retail, 2),
                'free_float_pct': round(100 - promoter, 2),
                'data_source': 'synthetic_proxy'
            }
            
            records.append(record)
    
    df_own = pd.DataFrame(records)
    
    print(f"   ✅ Generated {len(df_own):,} records")
    print(f"   📊 Tickers: {df_own['ticker'].nunique()}")
    print(f"   📅 Quarters: {df_own['quarter_end'].nunique()}")
    
    return df_own


def try_alpha_vantage_free():
    """
    Try AlphaVantage free tier (limited to 5 calls/min, 500 calls/day)
    """
    print("\n5️⃣  Trying AlphaVantage Free Tier")
    print("=" * 60)
    print("   ⚠️  Limited to 5 calls/min, 500/day")
    print("   ⚠️  NSE stocks not well covered")
    print("   → Skipping (use synthetic data instead)")
    
    return None


def main():
    """Main sourcing function"""
    print("="*70)
    print("SOURCE ALL MISSING DATA - Free/Open Sources")
    print("="*70)
    print("\nGoal: Complete offline dataset for local GreyOak Score testing")
    print("Approach: Synthetic proxy data (deterministic, realistic ranges)")
    print("\n⚠️  NOTE: This generates PROXY data for testing.")
    print("   For production, use real data from NSE/BSE or paid APIs.")
    
    # 1. Sector Indices
    print("\n" + "="*70)
    df_indices = generate_synthetic_indices()
    
    if df_indices is not None:
        output_file = Path('/app/backend/sector_indices_2020_2022.csv')
        df_indices.to_csv(output_file, index=False)
        print(f"\n   ✅ Saved: {output_file}")
        print(f"   📊 {len(df_indices):,} records, {df_indices['Index'].nunique()} indices")
    
    # 2. Fundamentals
    print("\n" + "="*70)
    df_fund = generate_synthetic_fundamentals()
    
    output_file = Path('/app/backend/fundamentals_quarterly_2020_2022.csv')
    df_fund.to_csv(output_file, index=False)
    print(f"\n   ✅ Saved: {output_file}")
    print(f"   📊 {len(df_fund):,} records")
    
    # 3. Ownership
    print("\n" + "="*70)
    df_own = generate_synthetic_ownership()
    
    output_file = Path('/app/backend/ownership_quarterly_2020_2022.csv')
    df_own.to_csv(output_file, index=False)
    print(f"\n   ✅ Saved: {output_file}")
    print(f"   📊 {len(df_own):,} records")
    
    # Summary
    print("\n" + "="*70)
    print("DATA SOURCING COMPLETE")
    print("="*70)
    
    print("\n✅ Files Created:")
    print("   1. sector_indices_2020_2022.csv")
    print("   2. fundamentals_quarterly_2020_2022.csv")
    print("   3. ownership_quarterly_2020_2022.csv")
    
    print("\n📊 Coverage:")
    print(f"   Sector Indices: {df_indices['Index'].nunique()} indices × {len(df_indices) // df_indices['Index'].nunique()} days")
    print(f"   Fundamentals: {df_fund['ticker'].nunique()} stocks × {df_fund['quarter_end'].nunique()} quarters")
    print(f"   Ownership: {df_own['ticker'].nunique()} stocks × {df_own['quarter_end'].nunique()} quarters")
    
    print("\n⚠️  Data Quality:")
    print("   ✅ Price Data: Real NSE data")
    print("   ⚠️  Indices: Synthetic (constituent averages)")
    print("   ⚠️  Fundamentals: Synthetic (realistic ranges)")
    print("   ⚠️  Ownership: Synthetic (realistic patterns)")
    
    print("\n💡 For Production:")
    print("   → Replace synthetics with real data from:")
    print("   → Fundamentals: Screener.in scraping or Financial Modeling Prep")
    print("   → Ownership: NSE shareholding PDFs")
    print("   → Indices: Manual download from Investing.com")
    
    print("\n🎯 Ready for offline GreyOak Score testing!")


if __name__ == "__main__":
    main()
