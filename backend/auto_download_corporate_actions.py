#!/usr/bin/env python3
"""
FULLY AUTOMATED Corporate Actions Downloader (2020-2022)
Tries multiple sources with automatic fallback:
1. Kaggle API (if credentials available)
2. NSE Corporate Actions API
3. BSE API
4. Synthetic/minimal data for testing
"""

import pandas as pd
import requests
import os
from datetime import datetime
import time

def download_from_kaggle_api():
    """
    Method 1: Try to download from Kaggle using API
    """
    print("\n" + "="*80)
    print("METHOD 1: Kaggle API")
    print("="*80)
    
    try:
        import kaggle
        
        # Search for corporate actions datasets
        datasets_to_try = [
            'debashis74017/indian-stock-market-data',
            'rohanrao/nifty50-stock-market-data',
            'yadavrahul/corporate-actions-india'
        ]
        
        print("\n🔍 Searching Kaggle for corporate actions datasets...")
        
        for dataset_name in datasets_to_try:
            try:
                print(f"\n  Trying: {dataset_name}...", end=' ')
                
                download_path = f"/app/backend/data/kaggle_ca_{dataset_name.split('/')[-1]}"
                os.makedirs(download_path, exist_ok=True)
                
                kaggle.api.dataset_download_files(
                    dataset_name,
                    path=download_path,
                    unzip=True
                )
                
                # Check if downloaded files contain corporate actions data
                csv_files = [f for f in os.listdir(download_path) if f.endswith('.csv')]
                
                for csv_file in csv_files:
                    filepath = os.path.join(download_path, csv_file)
                    df = pd.read_csv(filepath, nrows=5)
                    
                    # Check if it contains corporate actions data
                    columns_lower = [c.lower() for c in df.columns]
                    if any(keyword in ' '.join(columns_lower) for keyword in ['dividend', 'split', 'bonus', 'action', 'corporate']):
                        print(f"✓ Found potential data in {csv_file}")
                        return filepath
                
                print("✗ No corporate actions data")
                
            except Exception as e:
                print(f"✗ Error: {str(e)[:50]}")
        
        print("\n✗ Kaggle API: No suitable datasets found")
        return None
        
    except ImportError:
        print("\n✗ Kaggle library not available or not configured")
        print("  To use Kaggle API:")
        print("  1. Install: pip install kaggle")
        print("  2. Setup credentials: https://www.kaggle.com/docs/api")
        return None
    except Exception as e:
        print(f"\n✗ Kaggle API failed: {e}")
        return None

def download_from_nse_api():
    """
    Method 2: Download from NSE Corporate Actions API
    """
    print("\n" + "="*80)
    print("METHOD 2: NSE Corporate Actions API")
    print("="*80)
    
    NSE_BASE = "https://www.nseindia.com"
    NSE_CA_API = f"{NSE_BASE}/api/corporates-corporateActions"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.nseindia.com/'
    }
    
    try:
        # Establish session
        session = requests.Session()
        print("\n🔗 Connecting to NSE...")
        session.get(NSE_BASE, headers=headers, timeout=10)
        time.sleep(2)
        
        # Download corporate actions by quarter
        all_actions = []
        
        quarters = [
            ('01-01-2020', '31-03-2020', 'Q1 2020'),
            ('01-04-2020', '30-06-2020', 'Q2 2020'),
            ('01-07-2020', '30-09-2020', 'Q3 2020'),
            ('01-10-2020', '31-12-2020', 'Q4 2020'),
            ('01-01-2021', '31-03-2021', 'Q1 2021'),
            ('01-04-2021', '30-06-2021', 'Q2 2021'),
            ('01-07-2021', '30-09-2021', 'Q3 2021'),
            ('01-10-2021', '31-12-2021', 'Q4 2021'),
            ('01-01-2022', '31-03-2022', 'Q1 2022'),
            ('01-04-2022', '30-06-2022', 'Q2 2022'),
            ('01-07-2022', '30-09-2022', 'Q3 2022'),
            ('01-10-2022', '31-12-2022', 'Q4 2022'),
        ]
        
        for from_date, to_date, quarter_name in quarters:
            try:
                print(f"\n  Downloading {quarter_name}...", end=' ')
                
                params = {
                    'index': 'equities',
                    'from_date': from_date,
                    'to_date': to_date
                }
                
                response = session.get(NSE_CA_API, params=params, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data and len(data) > 0:
                        print(f"✓ Got {len(data)} records")
                        all_actions.extend(data)
                    else:
                        print("✗ No data")
                else:
                    print(f"✗ HTTP {response.status_code}")
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                print(f"✗ Error: {str(e)[:30]}")
        
        if all_actions:
            print(f"\n✓ NSE API: Downloaded {len(all_actions)} corporate actions")
            
            # Convert to DataFrame
            df = pd.DataFrame(all_actions)
            
            # Process and format
            df_formatted = process_nse_corporate_actions(df)
            
            return df_formatted
        else:
            print("\n✗ NSE API: No data retrieved")
            return None
            
    except Exception as e:
        print(f"\n✗ NSE API failed: {e}")
        return None

def process_nse_corporate_actions(df):
    """
    Process NSE corporate actions data to our schema
    """
    # NSE provides: symbol, company, series, faceVal, exDate, purpose, recordDate, etc.
    # Transform to: Ticker, Date, Action_Type, Details, Ratio, Amount
    
    processed_data = []
    
    for _, row in df.iterrows():
        try:
            ticker = row.get('symbol', '')
            ex_date = row.get('exDate', row.get('ex_date', ''))
            purpose = row.get('purpose', '').upper()
            
            # Determine action type
            action_type = 'Unknown'
            details = purpose
            ratio = 0
            amount = 0
            
            if 'DIVIDEND' in purpose:
                action_type = 'Dividend'
                # Try to extract amount from purpose
                # Example: "DIVIDEND - RS 2.50 PER SHARE"
                import re
                match = re.search(r'RS\.?\s*(\d+\.?\d*)', purpose)
                if match:
                    amount = float(match.group(1))
            elif 'SPLIT' in purpose:
                action_type = 'Split'
                # Extract ratio if possible
                match = re.search(r'(\d+)[:\s]+(\d+)', purpose)
                if match:
                    ratio = float(match.group(2)) / float(match.group(1))
            elif 'BONUS' in purpose:
                action_type = 'Bonus'
                match = re.search(r'(\d+)[:\s]+(\d+)', purpose)
                if match:
                    ratio = float(match.group(2)) / float(match.group(1))
            elif 'RIGHTS' in purpose:
                action_type = 'Rights'
            elif 'BUYBACK' in purpose:
                action_type = 'Buyback'
            
            processed_data.append({
                'Ticker': ticker,
                'Date': ex_date,
                'Action_Type': action_type,
                'Details': details,
                'Ratio': ratio,
                'Amount': amount
            })
            
        except Exception as e:
            continue
    
    if processed_data:
        result_df = pd.DataFrame(processed_data)
        # Convert date
        result_df['Date'] = pd.to_datetime(result_df['Date'], format='%d-%b-%Y', errors='coerce')
        return result_df
    else:
        return None

def create_minimal_corporate_actions():
    """
    Method 3: Create minimal synthetic corporate actions for testing
    """
    print("\n" + "="*80)
    print("METHOD 3: Minimal Synthetic Data (Fallback)")
    print("="*80)
    print("\n⚠️ WARNING: Creating minimal synthetic corporate actions")
    print("⚠️ This is for testing ONLY - not production data")
    
    # Create some reasonable dividend entries for major stocks
    actions = []
    
    # Major Nifty 50 stocks with typical dividend patterns
    major_stocks = [
        ('RELIANCE', 3, 6.5),
        ('TCS', 4, 18.0),
        ('INFY', 4, 15.0),
        ('HDFCBANK', 2, 6.5),
        ('ICICIBANK', 2, 5.0),
        ('KOTAKBANK', 2, 4.0),
        ('HINDUNILVR', 4, 17.0),
        ('ITC', 4, 5.5),
        ('LT', 2, 18.0),
        ('AXISBANK', 1, 2.0),
        ('MARUTI', 2, 60.0),
        ('BHARTIARTL', 2, 2.5),
        ('WIPRO', 3, 1.0),
        ('SUNPHARMA', 1, 7.5),
        ('NTPC', 3, 3.0)
    ]
    
    # Generate quarterly dividends for 2020-2022
    quarters = [
        '2020-03-31', '2020-06-30', '2020-09-30', '2020-12-31',
        '2021-03-31', '2021-06-30', '2021-09-30', '2021-12-31',
        '2022-03-31', '2022-06-30', '2022-09-30', '2022-12-31'
    ]
    
    for ticker, divs_per_year, avg_amount in major_stocks:
        # Distribute dividends across quarters
        dividend_quarters = quarters[::int(12/divs_per_year)]
        
        for quarter_date in dividend_quarters[:divs_per_year * 3]:  # 3 years
            actions.append({
                'Ticker': ticker,
                'Date': quarter_date,
                'Action_Type': 'Dividend',
                'Details': 'Interim' if 'Q1' in quarter_date or 'Q3' in quarter_date else 'Final',
                'Ratio': 0,
                'Amount': avg_amount
            })
    
    # Add a few stock splits
    splits = [
        ('TCS', '2020-06-15', 'Split', '1:1', 2.0, 0),
        ('EICHERMOT', '2021-02-10', 'Split', '1:10', 10.0, 0),
    ]
    
    for ticker, date, action_type, details, ratio, amount in splits:
        actions.append({
            'Ticker': ticker,
            'Date': date,
            'Action_Type': action_type,
            'Details': details,
            'Ratio': ratio,
            'Amount': amount
        })
    
    df = pd.DataFrame(actions)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(['Ticker', 'Date'])
    
    print(f"\n✓ Created {len(df)} synthetic corporate actions")
    print(f"   Stocks: {df['Ticker'].nunique()}")
    print(f"   Action types: {df['Action_Type'].value_counts().to_dict()}")
    print("\n⚠️ Replace with real data when available!")
    
    return df

def save_corporate_actions(df, output_file):
    """
    Save corporate actions to CSV
    """
    if df is None or df.empty:
        return False
    
    # Ensure schema
    required_cols = ['Ticker', 'Date', 'Action_Type', 'Details', 'Ratio', 'Amount']
    df = df[required_cols]
    
    # Sort
    df = df.sort_values(['Ticker', 'Date'])
    
    # Remove duplicates
    df = df.drop_duplicates()
    
    # Save
    df.to_csv(output_file, index=False)
    
    print(f"\n" + "="*80)
    print(" "*25 + "DOWNLOAD COMPLETE")
    print("="*80)
    print(f"\n✅ Saved to: {output_file}")
    print(f"\n📊 Summary:")
    print(f"   Total records: {len(df):,}")
    print(f"   Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
    print(f"   Stocks: {df['Ticker'].nunique()}")
    print(f"   Action types: {df['Action_Type'].value_counts().to_dict()}")
    
    return True

def main():
    """
    Main execution
    """
    print("\n" + "="*80)
    print(" "*17 + "AUTOMATED CORPORATE ACTIONS DOWNLOADER")
    print("="*80)
    print("\nTarget: Corporate actions for 205 stocks (2020-2022)")
    print("Strategy: Try multiple sources with automatic fallback\n")
    
    output_file = "/app/backend/corporate_actions_2020_2022.csv"
    
    # Method 1: Kaggle API
    df = download_from_kaggle_api()
    
    if df is not None and len(df) > 100:
        print("\n✓ Kaggle API succeeded!")
        return save_corporate_actions(df, output_file)
    
    # Method 2: NSE API
    print("\n⚠️ Kaggle API failed. Trying NSE API...")
    df = download_from_nse_api()
    
    if df is not None and len(df) > 100:
        print("\n✓ NSE API succeeded!")
        return save_corporate_actions(df, output_file)
    
    # Method 3: Minimal synthetic data
    print("\n⚠️ All real data sources failed.")
    print("⚠️ Creating minimal synthetic data for testing...")
    
    df = create_minimal_corporate_actions()
    
    if df is not None:
        print("\n✓ Synthetic data created!")
        return save_corporate_actions(df, output_file)
    
    print("\n✗ All methods failed")
    return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
