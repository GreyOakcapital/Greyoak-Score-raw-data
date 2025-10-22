#!/usr/bin/env python3
"""
Simple script to download Nifty sector indices data from investing.com
This script provides URLs and helps organize downloaded CSV files
"""

import os
import pandas as pd
from datetime import datetime

# Define the 9 sector indices
SECTOR_INDICES = [
    ('Nifty Bank', 'bank-nifty'),
    ('Nifty IT', 'nifty-it'),
    ('Nifty Auto', 'cnx-auto'),
    ('Nifty Pharma', 'cnx-pharma'),
    ('Nifty FMCG', 'cnx-fmcg'),
    ('Nifty Metal', 'cnx-metal'),
    ('Nifty Realty', 'cnx-realty'),
    ('Nifty Energy', 'cnx-energy'),
    ('Nifty Media', 'cnx-media')
]

def print_download_instructions():
    """Print step-by-step manual download instructions"""
    print("\n" + "="*100)
    print(" "*30 + "SECTOR INDICES DOWNLOAD INSTRUCTIONS")
    print("="*100)
    print("\nYou need to download 9 sector indices from investing.com for the period 2020-2022\n")
    
    for i, (name, slug) in enumerate(SECTOR_INDICES, 1):
        url = f"https://in.investing.com/indices/{slug}-historical-data"
        print(f"\n{i}. {name}")
        print(f"   └─ URL: {url}")
        print(f"   └─ Steps:")
        print(f"      1. Open URL in browser")
        print(f"      2. Look for date range selector (shows current range like '22-09-2025 - 22-10-2025')")
        print(f"      3. Click on the date selector")
        print(f"      4. Change start date to: 01/01/2020")
        print(f"      5. Change end date to: 31/12/2022")
        print(f"      6. Click 'Apply' or press Enter")
        print(f"      7. Click the 'Download' button")
        print(f"      8. Save the file as: {slug}_2020_2022.csv in /app/backend/data/")
    
    print("\n" + "="*100)
    print("\nAfter downloading all 9 files, run:")
    print("  python download_sector_indices_simple.py --combine")
    print("\n" + "="*100 + "\n")

def combine_downloaded_files():
    """Combine all downloaded sector CSV files into one"""
    print("\n" + "="*100)
    print(" "*35 + "COMBINING DOWNLOADED FILES")
    print("="*100 + "\n")
    
    data_dir = "/app/backend/data"
    all_data = []
    missing_files = []
    
    for sector_name, slug in SECTOR_INDICES:
        filename = f"{slug}_2020_2022.csv"
        filepath = os.path.join(data_dir, filename)
        
        if os.path.exists(filepath):
            print(f"✓ Found: {filename}")
            try:
                # Read the CSV file
                df = pd.read_csv(filepath)
                
                # Add sector column
                df['Sector'] = sector_name
                
                # Clean column names
                df.columns = df.columns.str.strip()
                
                # Investing.com format: Date, Price, Open, High, Low, Vol., Change %
                # Rename columns to standard names
                rename_map = {
                    'Date': 'Date',
                    'Price': 'Close',
                    'Open': 'Open',
                    'High': 'High',
                    'Low': 'Low',
                    'Vol.': 'Volume',
                    'Change %': 'Change_Pct'
                }
                
                df = df.rename(columns=rename_map)
                
                # Select and reorder columns
                df = df[['Date', 'Sector', 'Open', 'High', 'Low', 'Close', 'Volume', 'Change_Pct']]
                
                # Convert date to standard format
                # Investing.com uses DD-MM-YYYY format
                df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y', errors='coerce')
                
                # Clean numeric columns - remove commas and convert
                for col in ['Open', 'High', 'Low', 'Close']:
                    if df[col].dtype == 'object':
                        df[col] = df[col].str.replace(',', '').astype(float)
                
                # Clean volume - may have M, K suffixes
                if df['Volume'].dtype == 'object':
                    df['Volume'] = df['Volume'].apply(clean_volume)
                
                # Clean Change_Pct - remove % sign
                if df['Change_Pct'].dtype == 'object':
                    df['Change_Pct'] = df['Change_Pct'].str.replace('%', '').astype(float)
                
                all_data.append(df)
                print(f"  └─ Rows: {len(df)}, Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
                
            except Exception as e:
                print(f"✗ Error reading {filename}: {e}")
                missing_files.append(filename)
        else:
            print(f"✗ Missing: {filename}")
            missing_files.append(filename)
    
    if missing_files:
        print(f"\n⚠️ {len(missing_files)} file(s) missing. Please download them first.")
        return None
    
    if all_data:
        print(f"\n\nCombining {len(all_data)} sector files...")
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Sort by date and sector
        combined_df = combined_df.sort_values(['Date', 'Sector'])
        
        # Remove any rows with invalid dates
        combined_df = combined_df.dropna(subset=['Date'])
        
        # Save to final output file
        output_file = "/app/backend/sector_indices_2020_2022.csv"
        combined_df.to_csv(output_file, index=False)
        
        print(f"\n✓ SUCCESS! Combined file saved to: {output_file}")
        print(f"\n📊 Summary:")
        print(f"   Total rows: {len(combined_df):,}")
        print(f"   Date range: {combined_df['Date'].min().date()} to {combined_df['Date'].max().date()}")
        print(f"   Number of sectors: {combined_df['Sector'].nunique()}")
        
        # Show per-sector statistics
        print(f"\n📈 Data by sector:")
        summary = combined_df.groupby('Sector').agg({
            'Date': ['count', 'min', 'max']
        }).round(2)
        summary.columns = ['Row Count', 'Start Date', 'End Date']
        print(summary)
        
        # Check data quality
        print(f"\n🔍 Data Quality Check:")
        print(f"   Missing values:")
        missing = combined_df.isnull().sum()
        for col in missing[missing > 0].index:
            print(f"      {col}: {missing[col]}")
        
        if missing.sum() == 0:
            print(f"      ✓ No missing values!")
        
        print("\n" + "="*100 + "\n")
        return output_file
    else:
        print("\n✗ No data files found!")
        return None

def clean_volume(vol_str):
    """Convert volume strings like '42.47M', '301.13K' to numeric values"""
    if pd.isna(vol_str) or vol_str == '-':
        return 0
    
    vol_str = str(vol_str).strip()
    
    try:
        if 'M' in vol_str:
            return float(vol_str.replace('M', '')) * 1_000_000
        elif 'K' in vol_str:
            return float(vol_str.replace('K', '')) * 1_000
        else:
            return float(vol_str.replace(',', ''))
    except:
        return 0

def check_downloads_status():
    """Check which files have been downloaded"""
    print("\n" + "="*100)
    print(" "*35 + "DOWNLOAD STATUS CHECK")
    print("="*100 + "\n")
    
    data_dir = "/app/backend/data"
    downloaded = []
    missing = []
    
    for sector_name, slug in SECTOR_INDICES:
        filename = f"{slug}_2020_2022.csv"
        filepath = os.path.join(data_dir, filename)
        
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            downloaded.append((sector_name, filename, file_size))
            print(f"✓ {sector_name:20} - {filename:30} ({file_size:,} bytes)")
        else:
            missing.append((sector_name, filename))
            print(f"✗ {sector_name:20} - {filename:30} (NOT FOUND)")
    
    print(f"\n📊 Status: {len(downloaded)}/9 files downloaded")
    
    if missing:
        print(f"\n⚠️ Still need to download {len(missing)} file(s):")
        for sector_name, filename in missing:
            slug = filename.replace('_2020_2022.csv', '')
            url = f"https://in.investing.com/indices/{slug}-historical-data"
            print(f"   • {sector_name}: {url}")
    else:
        print(f"\n✓ All files downloaded! Ready to combine.")
        print(f"   Run: python download_sector_indices_simple.py --combine")
    
    print("\n" + "="*100 + "\n")
    
    return len(downloaded), len(missing)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--combine':
            # Combine downloaded files
            combine_downloaded_files()
        elif sys.argv[1] == '--status':
            # Check download status
            check_downloads_status()
        elif sys.argv[1] == '--help':
            print("\nUsage:")
            print("  python download_sector_indices_simple.py              # Show download instructions")
            print("  python download_sector_indices_simple.py --status     # Check download status")
            print("  python download_sector_indices_simple.py --combine    # Combine downloaded files")
            print("  python download_sector_indices_simple.py --help       # Show this help\n")
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Run with --help to see available options")
    else:
        # Default: show download instructions
        print_download_instructions()
