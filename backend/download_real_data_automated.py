#!/usr/bin/env python3
"""
REAL DATA ONLY - Fully Automated Downloader
Uses NSEPython library and Kaggle API for authentic historical data

One-time setup required:
1. Kaggle API credentials in ~/.kaggle/kaggle.json
   Get from: https://www.kaggle.com/settings → Create New API Token

After setup, runs fully automated with REAL DATA ONLY.
"""

import pandas as pd
import os
import time
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def download_sector_indices_nsepython():
    """
    Method 1: Download sector indices using NSEPython library
    """
    print("\n" + "="*80)
    print("METHOD 1: NSEPython Library - Sector Indices")
    print("="*80)
    
    try:
        from nsepython import index_history
        
        # NSE sector index names
        sector_indices = {
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
        start_date = '01-01-2020'
        end_date = '31-12-2022'
        
        print(f"\n📥 Downloading sector indices from NSE...")
        print(f"   Date range: {start_date} to {end_date}\n")
        
        for display_name, nse_name in sector_indices.items():
            try:
                print(f"  📊 {display_name} ({nse_name})...", end=' ')
                
                # NSEPython function to get index history
                df = index_history(
                    symbol=nse_name,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if df is not None and not df.empty:
                    # Standardize columns
                    df['Index'] = display_name
                    
                    # NSEPython returns: DATE, OPEN, HIGH, LOW, CLOSE, etc.
                    df = df.rename(columns={
                        'DATE': 'Date',
                        'OPEN': 'Open',
                        'HIGH': 'High',
                        'LOW': 'Low',
                        'CLOSE': 'Close',
                        'HistoricalDate': 'Date'
                    })
                    
                    # If volume column exists, use it; otherwise set to 0
                    if 'Volume' not in df.columns:
                        df['Volume'] = 0
                    
                    df = df[['Index', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                    
                    all_data.append(df)
                    print(f"✓ {len(df)} rows")
                else:
                    print(f"✗ No data")
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                print(f"✗ Error: {str(e)[:50]}")
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df['Date'] = pd.to_datetime(combined_df['Date'])
            combined_df = combined_df.sort_values(['Index', 'Date'])
            
            print(f"\n✓ NSEPython: Downloaded {len(all_data)}/9 indices ({len(combined_df):,} rows)")
            return combined_df
        else:
            print(f"\n✗ NSEPython: No data retrieved")
            return None
            
    except ImportError:
        print("\n✗ NSEPython not installed")
        print("  Install: pip install nsepython")
        return None
    except Exception as e:
        print(f"\n✗ NSEPython failed: {e}")
        return None

def download_sector_indices_kaggle():
    """
    Method 2: Download from Kaggle using API
    Requires one-time setup: ~/.kaggle/kaggle.json
    """
    print("\n" + "="*80)
    print("METHOD 2: Kaggle API - Sector Indices")
    print("="*80)
    
    try:
        import kaggle
        
        dataset_name = "debashis74017/stock-market-index-data-india-1990-2022"
        download_path = "/app/backend/data/kaggle_indices"
        
        print(f"\n📥 Downloading from Kaggle: {dataset_name}")
        
        os.makedirs(download_path, exist_ok=True)
        
        # Download dataset
        kaggle.api.dataset_download_files(
            dataset_name,
            path=download_path,
            unzip=True,
            quiet=False
        )
        
        print(f"✓ Dataset downloaded to: {download_path}")
        
        # Find the CSV file
        csv_files = [f for f in os.listdir(download_path) if f.endswith('.csv')]
        
        if not csv_files:
            print("✗ No CSV files found in download")
            return None
        
        # Use the largest CSV (main dataset)
        csv_file = max(csv_files, key=lambda f: os.path.getsize(os.path.join(download_path, f)))
        csv_path = os.path.join(download_path, csv_file)
        
        print(f"✓ Processing: {csv_file}")
        
        # Load and process
        df = pd.read_csv(csv_path)
        
        print(f"  Loaded {len(df):,} rows")
        print(f"  Columns: {list(df.columns)}")
        
        # Filter for sector indices and 2020-2022
        # Assuming columns: Date, Index/Symbol, Open, High, Low, Close, Volume
        
        # Standardize column names
        column_map = {}
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'date' in col_lower:
                column_map[col] = 'Date'
            elif any(x in col_lower for x in ['index', 'symbol', 'name']):
                column_map[col] = 'Index'
            elif 'open' in col_lower:
                column_map[col] = 'Open'
            elif 'high' in col_lower:
                column_map[col] = 'High'
            elif 'low' in col_lower:
                column_map[col] = 'Low'
            elif 'close' in col_lower:
                column_map[col] = 'Close'
            elif 'volume' in col_lower or 'vol' in col_lower:
                column_map[col] = 'Volume'
        
        df = df.rename(columns=column_map)
        
        # Convert date
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        # Filter for 2020-2022
        df = df[(df['Date'] >= '2020-01-01') & (df['Date'] <= '2022-12-31')]
        
        # Filter for sector indices
        sector_keywords = ['BANK', 'IT', 'AUTO', 'PHARMA', 'FMCG', 'METAL', 'REALTY', 'ENERGY', 'MEDIA']
        sector_mask = df['Index'].str.upper().str.contains('|'.join(sector_keywords), na=False)
        df_sectors = df[sector_mask].copy()
        
        # Standardize index names
        name_map = {
            'NIFTY BANK': 'Nifty Bank',
            'NIFTY IT': 'Nifty IT',
            'NIFTY AUTO': 'Nifty Auto',
            'NIFTY PHARMA': 'Nifty Pharma',
            'NIFTY FMCG': 'Nifty FMCG',
            'NIFTY METAL': 'Nifty Metal',
            'NIFTY REALTY': 'Nifty Realty',
            'NIFTY ENERGY': 'Nifty Energy',
            'NIFTY MEDIA': 'Nifty Media'
        }
        
        for old_name, new_name in name_map.items():
            mask = df_sectors['Index'].str.upper().str.contains(old_name, na=False)
            df_sectors.loc[mask, 'Index'] = new_name
        
        # Select required columns
        df_sectors = df_sectors[['Index', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        df_sectors = df_sectors.sort_values(['Index', 'Date'])
        
        print(f"\n✓ Kaggle: Extracted {df_sectors['Index'].nunique()} sector indices")
        print(f"  Total rows: {len(df_sectors):,}")
        print(f"  Indices found: {df_sectors['Index'].unique().tolist()}")
        
        return df_sectors
        
    except ImportError:
        print("\n✗ Kaggle library not installed")
        print("  Install: pip install kaggle")
        return None
    except FileNotFoundError:
        print("\n✗ Kaggle API credentials not found")
        print("\n📝 ONE-TIME SETUP REQUIRED:")
        print("  1. Go to: https://www.kaggle.com/settings")
        print("  2. Scroll to 'API' section")
        print("  3. Click 'Create New API Token'")
        print("  4. Save kaggle.json to: ~/.kaggle/kaggle.json")
        print("  5. Run: chmod 600 ~/.kaggle/kaggle.json")
        print("  6. Re-run this script")
        return None
    except Exception as e:
        print(f"\n✗ Kaggle API failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def download_corporate_actions_kaggle():
    """
    Download corporate actions from Kaggle
    """
    print("\n" + "="*80)
    print("METHOD 1: Kaggle API - Corporate Actions")
    print("="*80)
    
    try:
        import kaggle
        
        # Search for corporate actions datasets
        datasets_to_try = [
            'rohanrao/nifty50-stock-market-data',  # May have corporate actions
            'debashis74017/indian-stock-market-data'  # May have corporate actions
        ]
        
        print("\n📥 Searching Kaggle for corporate actions data...")
        
        for dataset_name in datasets_to_try:
            try:
                print(f"\n  Trying dataset: {dataset_name}")
                
                download_path = f"/app/backend/data/kaggle_ca_{dataset_name.split('/')[-1]}"
                os.makedirs(download_path, exist_ok=True)
                
                kaggle.api.dataset_download_files(
                    dataset_name,
                    path=download_path,
                    unzip=True,
                    quiet=True
                )
                
                # Look for corporate actions file
                csv_files = [f for f in os.listdir(download_path) if f.endswith('.csv')]
                
                for csv_file in csv_files:
                    filepath = os.path.join(download_path, csv_file)
                    df_sample = pd.read_csv(filepath, nrows=10)
                    
                    # Check if it's corporate actions data
                    cols_lower = ' '.join([c.lower() for c in df_sample.columns])
                    if any(kw in cols_lower for kw in ['dividend', 'split', 'bonus', 'corporate', 'action']):
                        print(f"    ✓ Found corporate actions in: {csv_file}")
                        
                        # Load full file
                        df_full = pd.read_csv(filepath)
                        
                        # Process and filter for 2020-2022
                        # Assuming columns like: Symbol, Date, Action, Details, etc.
                        # This needs to be adjusted based on actual dataset structure
                        
                        print(f"    Loaded {len(df_full)} records")
                        return df_full  # Return raw data for now
                        
                print("    ✗ No corporate actions data found")
                
            except Exception as e:
                print(f"    ✗ Error: {str(e)[:50]}")
        
        print("\n✗ Kaggle: No corporate actions data found in searched datasets")
        return None
        
    except Exception as e:
        print(f"\n✗ Kaggle API failed: {e}")
        return None

def process_nse_corporate_actions(df):
    """
    Process NSE corporate actions to standard schema
    """
    import re
    
    processed = []
    
    for _, row in df.iterrows():
        try:
            ticker = row.get('symbol', row.get('SYMBOL', ''))
            ex_date = row.get('exDate', row.get('ex_date', row.get('Ex-Date', '')))
            purpose = str(row.get('purpose', row.get('subject', row.get('PURPOSE', '')))).upper()
            
            # Determine action type
            action_type = 'Unknown'
            details = purpose
            ratio = 0.0
            amount = 0.0
            
            if 'DIVIDEND' in purpose:
                action_type = 'Dividend'
                # Extract amount: "DIVIDEND - RS 2.50 PER SHARE"
                match = re.search(r'RS\.?\s*(\d+\.?\d*)', purpose)
                if match:
                    amount = float(match.group(1))
                details = 'Interim' if 'INTERIM' in purpose else 'Final'
                
            elif 'SPLIT' in purpose:
                action_type = 'Split'
                # Extract ratio: "STOCK SPLIT FROM RS 10 TO RS 5" or "1:2"
                match = re.search(r'(\d+)\s*:\s*(\d+)', purpose)
                if match:
                    ratio = float(match.group(2)) / float(match.group(1))
                else:
                    match = re.search(r'RS\s*(\d+)\s*TO\s*RS\s*(\d+)', purpose)
                    if match:
                        ratio = float(match.group(1)) / float(match.group(2))
                details = purpose
                
            elif 'BONUS' in purpose:
                action_type = 'Bonus'
                # Extract ratio: "BONUS 1:1"
                match = re.search(r'(\d+)\s*:\s*(\d+)', purpose)
                if match:
                    ratio = (float(match.group(1)) + float(match.group(2))) / float(match.group(2))
                details = purpose
                
            elif 'RIGHTS' in purpose:
                action_type = 'Rights'
                details = purpose
                
            elif 'BUYBACK' in purpose or 'BUY BACK' in purpose:
                action_type = 'Buyback'
                details = purpose
            
            else:
                continue  # Skip unknown types
            
            processed.append({
                'Ticker': ticker,
                'Date': ex_date,
                'Action_Type': action_type,
                'Details': details[:100],  # Limit length
                'Ratio': ratio,
                'Amount': amount
            })
            
        except Exception as e:
            continue
    
    if processed:
        result_df = pd.DataFrame(processed)
        result_df['Date'] = pd.to_datetime(result_df['Date'], errors='coerce')
        result_df = result_df.dropna(subset=['Date'])
        result_df = result_df.sort_values('Date')
        return result_df
    else:
        return None

def save_data(df, filepath, data_type):
    """
    Save data to CSV
    """
    if df is None or df.empty:
        print(f"\n✗ No {data_type} data to save")
        return False
    
    df.to_csv(filepath, index=False)
    
    print(f"\n" + "="*80)
    print(" "*30 + "DOWNLOAD COMPLETE")
    print("="*80)
    print(f"\n✅ {data_type} saved to: {filepath}")
    print(f"\n📊 Summary:")
    print(f"   Total rows: {len(df):,}")
    print(f"   Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
    
    if data_type == "Sector Indices":
        print(f"   Indices: {df['Index'].nunique()}")
        print(f"\n   Indices found: {sorted(df['Index'].unique().tolist())}")
    else:
        print(f"   Stocks: {df['Ticker'].nunique()}")
        print(f"   Action types: {df['Action_Type'].value_counts().to_dict()}")
    
    return True

def main():
    """
    Main execution - REAL DATA ONLY
    """
    print("\n" + "="*80)
    print(" "*15 + "REAL DATA AUTOMATED DOWNLOADER - NO SYNTHETIC DATA")
    print("="*80)
    
    print("\n🎯 Target: Real historical data (2020-2022)")
    print("📍 Sources: NSEPython → Kaggle API")
    print("⚠️  One-time Kaggle API setup may be required\n")
    
    success_count = 0
    
    # ============================================================================
    # TASK 1: SECTOR INDICES
    # ============================================================================
    print("\n" + "█"*80)
    print("█" + " "*30 + "TASK 1: SECTOR INDICES" + " "*27 + "█")
    print("█"*80)
    
    sector_file = "/app/backend/sector_indices_2020_2022.csv"
    
    # Try NSEPython first
    df_sectors = download_sector_indices_nsepython()
    
    # Fallback to Kaggle if NSEPython fails
    if df_sectors is None or len(df_sectors) < 1000:
        print("\n⚠️ NSEPython incomplete/failed. Trying Kaggle API...")
        df_sectors = download_sector_indices_kaggle()
    
    if save_data(df_sectors, sector_file, "Sector Indices"):
        success_count += 1
    
    # ============================================================================
    # TASK 2: CORPORATE ACTIONS
    # ============================================================================
    print("\n\n" + "█"*80)
    print("█" + " "*27 + "TASK 2: CORPORATE ACTIONS" + " "*27 + "█")
    print("█"*80)
    
    ca_file = "/app/backend/corporate_actions_2020_2022.csv"
    
    # Try Kaggle for corporate actions (NSEPython doesn't have this feature)
    df_ca = download_corporate_actions_kaggle()
    
    # If Kaggle data found, process it
    if df_ca is not None and not df_ca.empty:
        # Try to process it to our schema
        try:
            df_ca_processed = process_nse_corporate_actions(df_ca)
            if save_data(df_ca_processed, ca_file, "Corporate Actions"):
                success_count += 1
        except:
            print("⚠️ Could not process corporate actions to standard schema")
    else:
        print("⚠️ Corporate actions data not available from automated sources")
        print("   Consider manual collection for this data type")
    
    # ============================================================================
    # FINAL REPORT
    # ============================================================================
    print("\n\n" + "="*80)
    print(" "*30 + "FINAL REPORT")
    print("="*80)
    
    print(f"\n📊 Results: {success_count}/2 tasks completed with REAL DATA")
    
    if success_count == 2:
        print("\n" + "="*80)
        print(" "*25 + "🎉 SUCCESS - ALL REAL DATA! 🎉")
        print("="*80)
        print("\n✅ Ready for GreyOak Score computation with authentic data!")
        return True
    else:
        print("\n" + "="*80)
        print(" "*25 + "⚠️ PARTIAL OR NO SUCCESS ⚠️")
        print("="*80)
        
        if success_count == 0:
            print("\n❌ No real data could be downloaded")
            print("\n💡 ACTION REQUIRED:")
            print("   1. Setup Kaggle API credentials (one-time):")
            print("      - Visit: https://www.kaggle.com/settings")
            print("      - Create New API Token")
            print("      - Save kaggle.json to: ~/.kaggle/kaggle.json")
            print("      - chmod 600 ~/.kaggle/kaggle.json")
            print("   2. Re-run this script")
            print("\n   After setup, everything runs automatically!")
        
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
