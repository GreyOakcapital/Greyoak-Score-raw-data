#!/usr/bin/env python3
"""
FULLY AUTOMATED Sector Indices Downloader (2020-2022)
Tries multiple sources with automatic fallback:
1. Yahoo Finance (yfinance) with correct NSE tickers
2. NSE API direct access
3. Fallback: Calculate from constituent stocks or use synthetic data
"""

import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import warnings
warnings.filterwarnings('ignore')

# Yahoo Finance ticker symbols for Nifty sector indices
SECTOR_INDICES_YFINANCE = {
    'Nifty Bank': '^NSEBANK',
    'Nifty IT': '^CNXIT',
    'Nifty Auto': '^CNXAUTO',
    'Nifty Pharma': '^CNXPHARMA',
    'Nifty FMCG': '^CNXFMCG',
    'Nifty Metal': '^CNXMETAL',
    'Nifty Realty': '^CNXREALTY',
    'Nifty Energy': '^CNXENERGY',
    'Nifty Media': '^CNXMEDIA'
}

# Alternative ticker formats to try
ALTERNATIVE_TICKERS = {
    'Nifty Bank': ['NIFTY_BANK.NS', 'BANKNIFTY.NS', '^NIFTYBANK'],
    'Nifty IT': ['NIFTY_IT.NS', 'CNXIT.NS', '^NIFTYIT'],
    'Nifty Auto': ['NIFTY_AUTO.NS', 'CNXAUTO.NS', '^NIFTYAUTO'],
    'Nifty Pharma': ['NIFTY_PHARMA.NS', 'CNXPHARMA.NS', '^NIFTYPHARMA'],
    'Nifty FMCG': ['NIFTY_FMCG.NS', 'CNXFMCG.NS', '^NIFTYFMCG'],
    'Nifty Metal': ['NIFTY_METAL.NS', 'CNXMETAL.NS', '^NIFTYMETAL'],
    'Nifty Realty': ['NIFTY_REALTY.NS', 'CNXREALTY.NS', '^NIFTYREALTY'],
    'Nifty Energy': ['NIFTY_ENERGY.NS', 'CNXENERGY.NS', '^NIFTYENERGY'],
    'Nifty Media': ['NIFTY_MEDIA.NS', 'CNXMEDIA.NS', '^NIFTYMEDIA']
}

def try_yfinance_download(sector_name, ticker, start_date, end_date):
    """
    Try to download data from Yahoo Finance for a given ticker
    """
    try:
        print(f"  Trying ticker: {ticker}...", end=' ')
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        
        if df is not None and not df.empty and len(df) > 100:
            print(f"✓ Success! ({len(df)} rows)")
            df = df.reset_index()
            df['Index'] = sector_name
            df = df.rename(columns={
                'Date': 'Date',
                'Open': 'Open',
                'High': 'High',
                'Low': 'Low',
                'Close': 'Close',
                'Volume': 'Volume'
            })
            df = df[['Index', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            return df
        else:
            print(f"✗ No data")
            return None
    except Exception as e:
        print(f"✗ Error: {str(e)[:50]}")
        return None

def download_sector_yfinance():
    """
    Method 1: Download sector indices using Yahoo Finance
    """
    print("\n" + "="*80)
    print("METHOD 1: Yahoo Finance (yfinance)")
    print("="*80)
    
    start_date = '2020-01-01'
    end_date = '2022-12-31'
    
    all_data = []
    
    for sector_name, primary_ticker in SECTOR_INDICES_YFINANCE.items():
        print(f"\n📊 {sector_name}")
        
        # Try primary ticker
        df = try_yfinance_download(sector_name, primary_ticker, start_date, end_date)
        
        # If primary fails, try alternatives
        if df is None and sector_name in ALTERNATIVE_TICKERS:
            print(f"  Primary ticker failed. Trying alternatives...")
            for alt_ticker in ALTERNATIVE_TICKERS[sector_name]:
                df = try_yfinance_download(sector_name, alt_ticker, start_date, end_date)
                if df is not None:
                    break
        
        if df is not None:
            all_data.append(df)
        else:
            print(f"  ✗ All tickers failed for {sector_name}")
    
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        print(f"\n✓ Yahoo Finance: Downloaded {len(all_data)}/9 indices ({len(combined_df)} rows)")
        return combined_df
    else:
        print(f"\n✗ Yahoo Finance: No data retrieved")
        return None

def download_sector_nse_api():
    """
    Method 2: Try NSE API direct access
    """
    print("\n" + "="*80)
    print("METHOD 2: NSE India API")
    print("="*80)
    
    # NSE Index Data API endpoints
    NSE_BASE = "https://www.nseindia.com"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.nseindia.com/'
    }
    
    # Map our sector names to NSE index names
    NSE_INDEX_NAMES = {
        'Nifty Bank': 'NIFTY BANK',
        'Nifty IT': 'NIFTY IT',
        'Nifty Auto': 'NIFTY AUTO',
        'Nifty Pharma': 'NIFTY PHARMA',
        'Nifty FMCG': 'NIFTY FMCG',
        'Nifty Metal': 'NIFTY METAL',
        'Nifty Realty': 'NIFTY REALTY',
        'Nifty Energy': 'NIFTY ENERGY',
        'Nifty Media': 'NIFTY MEDIA'
    }
    
    all_data = []
    
    try:
        # First, establish a session with NSE
        session = requests.Session()
        session.get(NSE_BASE, headers=headers, timeout=10)
        time.sleep(2)
        
        for sector_name, nse_name in NSE_INDEX_NAMES.items():
            print(f"\n📊 {sector_name} ({nse_name})...", end=' ')
            
            try:
                # NSE Historical Data API
                url = f"{NSE_BASE}/api/historical/indicesHistory"
                params = {
                    'indexType': nse_name,
                    'from': '01-01-2020',
                    'to': '31-12-2022'
                }
                
                response = session.get(url, params=params, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'data' in data and data['data']:
                        df = pd.DataFrame(data['data'])
                        df['Index'] = sector_name
                        # Rename columns to match our schema
                        # NSE format may vary - adjust as needed
                        print(f"✓ Success! ({len(df)} rows)")
                        all_data.append(df)
                    else:
                        print(f"✗ No data in response")
                else:
                    print(f"✗ HTTP {response.status_code}")
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                print(f"✗ Error: {str(e)[:50]}")
        
        if all_data:
            print(f"\n✓ NSE API: Downloaded {len(all_data)}/9 indices")
            # Combine and format data
            combined_df = pd.concat(all_data, ignore_index=True)
            return combined_df
        else:
            print(f"\n✗ NSE API: No data retrieved")
            return None
            
    except Exception as e:
        print(f"\n✗ NSE API: Connection failed - {e}")
        return None

def create_synthetic_sector_data():
    """
    Method 3: Create synthetic/approximated sector data based on Nifty 50
    This is a fallback when no real data is available
    """
    print("\n" + "="*80)
    print("METHOD 3: Synthetic Data (Fallback)")
    print("="*80)
    print("\n⚠️ WARNING: Using synthetic data for testing purposes only")
    
    try:
        # Download Nifty 50 as base
        print("\n📊 Downloading Nifty 50 as base...")
        nifty = yf.download('^NSEI', start='2020-01-01', end='2022-12-31', progress=False)
        
        if nifty.empty:
            print("✗ Could not download Nifty 50 data")
            return None
        
        print(f"✓ Got Nifty 50 data ({len(nifty)} rows)")
        
        # Create sector variations with different volatility multipliers
        sector_multipliers = {
            'Nifty Bank': 1.3,      # More volatile
            'Nifty IT': 1.2,        # Tech sector
            'Nifty Auto': 1.15,     # Cyclical
            'Nifty Pharma': 0.9,    # Defensive
            'Nifty FMCG': 0.85,     # Stable
            'Nifty Metal': 1.4,     # Very volatile
            'Nifty Realty': 1.5,    # Most volatile
            'Nifty Energy': 1.1,    # Moderate
            'Nifty Media': 1.25     # Media sector
        }
        
        all_data = []
        
        for sector_name, multiplier in sector_multipliers.items():
            sector_df = nifty.copy()
            sector_df = sector_df.reset_index()
            
            # Apply multiplier to create sector variation
            for col in ['Open', 'High', 'Low', 'Close']:
                sector_df[col] = sector_df[col] * multiplier
            
            sector_df['Index'] = sector_name
            sector_df['Volume'] = sector_df['Volume'] * (multiplier * 0.7)
            
            sector_df = sector_df[['Index', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            all_data.append(sector_df)
            
            print(f"  ✓ Generated {sector_name}")
        
        combined_df = pd.concat(all_data, ignore_index=True)
        print(f"\n✓ Synthetic Data: Created 9/9 indices ({len(combined_df)} rows)")
        print("⚠️ NOTE: This is approximated data. Replace with real data when available.")
        
        return combined_df
        
    except Exception as e:
        print(f"\n✗ Synthetic Data: Failed - {e}")
        return None

def save_sector_indices(df, output_file):
    """
    Save sector indices data to CSV
    """
    if df is None or df.empty:
        return False
    
    # Ensure proper column order
    df = df[['Index', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
    
    # Convert date to proper format
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Sort by Index and Date
    df = df.sort_values(['Index', 'Date'])
    
    # Remove duplicates
    df = df.drop_duplicates(subset=['Index', 'Date'])
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    
    print(f"\n" + "="*80)
    print(" "*25 + "DOWNLOAD COMPLETE")
    print("="*80)
    print(f"\n✅ Saved to: {output_file}")
    print(f"\n📊 Summary:")
    print(f"   Total rows: {len(df):,}")
    print(f"   Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
    print(f"   Indices: {df['Index'].nunique()}")
    
    # Per-index summary
    print(f"\n📈 Data by Index:")
    summary = df.groupby('Index').agg({
        'Date': ['count', 'min', 'max']
    })
    summary.columns = ['Row Count', 'Start Date', 'End Date']
    print(summary)
    
    return True

def main():
    """
    Main execution - try methods in order until one succeeds
    """
    print("\n" + "="*80)
    print(" "*20 + "AUTOMATED SECTOR INDICES DOWNLOADER")
    print("="*80)
    print("\nTarget: 9 Nifty sector indices (2020-2022)")
    print("Strategy: Try multiple sources with automatic fallback\n")
    
    output_file = "/app/backend/sector_indices_2020_2022.csv"
    
    # Method 1: Yahoo Finance
    df = download_sector_yfinance()
    
    if df is not None and len(df) > 1000:
        print("\n✓ Yahoo Finance succeeded!")
        return save_sector_indices(df, output_file)
    
    # Method 2: NSE API
    print("\n⚠️ Yahoo Finance incomplete. Trying NSE API...")
    df = download_sector_nse_api()
    
    if df is not None and len(df) > 1000:
        print("\n✓ NSE API succeeded!")
        return save_sector_indices(df, output_file)
    
    # Method 3: Synthetic data as last resort
    print("\n⚠️ All real data sources failed. Creating synthetic data...")
    print("⚠️ This is for testing only. Real data recommended for production.")
    
    user_input = input("\nCreate synthetic data for testing? (yes/no): ").lower()
    
    if user_input == 'yes':
        df = create_synthetic_sector_data()
        
        if df is not None:
            print("\n✓ Synthetic data created!")
            return save_sector_indices(df, output_file)
    
    # All methods failed
    print("\n" + "="*80)
    print(" "*25 + "DOWNLOAD FAILED")
    print("="*80)
    print("\n✗ Could not download sector indices data")
    print("\n💡 Alternatives:")
    print("   1. Check internet connection")
    print("   2. Try running again (APIs may be temporarily down)")
    print("   3. Use manual Kaggle download approach")
    print("   4. Consider adjusting data model to not require sector indices")
    print("\n" + "="*80)
    
    return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
