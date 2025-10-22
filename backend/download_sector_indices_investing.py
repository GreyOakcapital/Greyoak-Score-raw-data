#!/usr/bin/env python3
"""
Download historical sector indices data from investing.com (2020-2022)
for 9 Nifty sector indices and combine into sector_indices_2020_2022.csv
"""

import pandas as pd
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

# Define the 9 sector indices with their investing.com slugs
SECTOR_INDICES = {
    'Nifty Bank': 'bank-nifty',
    'Nifty IT': 'nifty-it',
    'Nifty Auto': 'cnx-auto',
    'Nifty Pharma': 'cnx-pharma',
    'Nifty FMCG': 'cnx-fmcg',
    'Nifty Metal': 'cnx-metal',
    'Nifty Realty': 'cnx-realty',
    'Nifty Energy': 'cnx-energy',
    'Nifty Media': 'cnx-media'
}

# Date range: 2020-2022
START_DATE = '01/01/2020'  # DD/MM/YYYY format
END_DATE = '31/12/2022'

def download_investing_data(index_slug, index_name, start_date, end_date):
    """
    Download historical data for a given index from investing.com
    
    Note: investing.com requires a more complex approach as it uses JavaScript.
    This is a placeholder that needs to be replaced with proper scraping logic.
    """
    print(f"\nDownloading {index_name}...")
    
    # URL pattern for investing.com historical data
    url = f"https://in.investing.com/indices/{index_slug}-historical-data"
    
    print(f"URL: {url}")
    print(f"Date range: {start_date} to {end_date}")
    
    # Note: investing.com requires JavaScript rendering and may need Selenium/Playwright
    # For now, this returns a placeholder
    print(f"⚠️ WARNING: Automated download from investing.com requires browser automation")
    print(f"Please manually download data from: {url}")
    print(f"Set date range to: {start_date} - {end_date}")
    print(f"Click 'Download' button and save as: {index_name.replace(' ', '_')}.csv")
    
    return None

def manual_download_instructions():
    """
    Provide manual download instructions for the user
    """
    print("\n" + "="*80)
    print("MANUAL DOWNLOAD INSTRUCTIONS")
    print("="*80)
    print("\nTo download sector indices data from investing.com:")
    print("\n1. For each sector index below:")
    
    for i, (index_name, index_slug) in enumerate(SECTOR_INDICES.items(), 1):
        url = f"https://in.investing.com/indices/{index_slug}-historical-data"
        print(f"\n   {i}. {index_name}:")
        print(f"      URL: {url}")
        print(f"      - Open the URL in browser")
        print(f"      - Set date range: 01/01/2020 to 31/12/2022")
        print(f"      - Click the 'Download' button")
        print(f"      - Save as: /app/backend/data/{index_name.replace(' ', '_').lower()}_2020_2022.csv")
    
    print("\n2. After downloading all files, run this script again with --combine flag")
    print("   python download_sector_indices_investing.py --combine")
    print("\n" + "="*80)

def combine_downloaded_files():
    """
    Combine all downloaded sector index files into one consolidated CSV
    """
    print("\n" + "="*80)
    print("COMBINING DOWNLOADED FILES")
    print("="*80)
    
    data_dir = "/app/backend/data"
    combined_data = []
    
    for index_name in SECTOR_INDICES.keys():
        filename = f"{index_name.replace(' ', '_').lower()}_2020_2022.csv"
        filepath = os.path.join(data_dir, filename)
        
        if os.path.exists(filepath):
            print(f"\n✓ Found: {filename}")
            df = pd.read_csv(filepath)
            
            # Add sector column
            df['Sector'] = index_name
            
            # Standardize column names
            df.columns = df.columns.str.strip()
            
            # Expected columns from investing.com: Date, Price, Open, High, Low, Vol., Change %
            # Rename to match our schema
            column_mapping = {
                'Date': 'Date',
                'Price': 'Close',
                'Open': 'Open',
                'High': 'High',
                'Low': 'Low',
                'Vol.': 'Volume',
                'Change %': 'Change_Pct'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Select relevant columns
            df = df[['Date', 'Sector', 'Open', 'High', 'Low', 'Close', 'Volume', 'Change_Pct']]
            
            combined_data.append(df)
            print(f"   Rows: {len(df)}")
        else:
            print(f"\n✗ Missing: {filename}")
            print(f"   Please download from investing.com and save to {filepath}")
    
    if combined_data:
        print(f"\n\nCombining {len(combined_data)} files...")
        final_df = pd.concat(combined_data, ignore_index=True)
        
        # Convert date to standard format
        final_df['Date'] = pd.to_datetime(final_df['Date'], format='%d-%m-%Y', errors='coerce')
        
        # Sort by date and sector
        final_df = final_df.sort_values(['Date', 'Sector'])
        
        # Save combined file
        output_file = "/app/backend/sector_indices_2020_2022.csv"
        final_df.to_csv(output_file, index=False)
        
        print(f"\n✓ Combined file saved: {output_file}")
        print(f"  Total rows: {len(final_df)}")
        print(f"  Date range: {final_df['Date'].min()} to {final_df['Date'].max()}")
        print(f"  Sectors: {final_df['Sector'].nunique()}")
        
        # Show summary
        print("\nSummary by sector:")
        summary = final_df.groupby('Sector').agg({
            'Date': ['min', 'max', 'count']
        })
        print(summary)
        
        return output_file
    else:
        print("\n✗ No files found to combine. Please download the data first.")
        return None

def try_automated_download_with_playwright():
    """
    Attempt automated download using Playwright (browser automation)
    """
    print("\n" + "="*80)
    print("AUTOMATED DOWNLOAD ATTEMPT (Using Playwright)")
    print("="*80)
    
    try:
        from playwright.sync_api import sync_playwright
        
        print("\n✓ Playwright is available. Starting automated download...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            for index_name, index_slug in SECTOR_INDICES.items():
                print(f"\nDownloading {index_name}...")
                url = f"https://in.investing.com/indices/{index_slug}-historical-data"
                
                try:
                    page.goto(url, timeout=30000)
                    time.sleep(3)
                    
                    # Set date range (this requires understanding the UI elements)
                    # Note: This is a placeholder - actual implementation needs inspection
                    print(f"  Navigated to: {url}")
                    print(f"  ⚠️ Date range selection requires manual UI interaction")
                    print(f"  ⚠️ Download button requires manual click")
                    
                except Exception as e:
                    print(f"  ✗ Error: {e}")
            
            browser.close()
            
    except ImportError:
        print("\n✗ Playwright not installed")
        print("  Install with: pip install playwright && playwright install chromium")
        return False
    except Exception as e:
        print(f"\n✗ Automated download failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--combine':
        # Combine already downloaded files
        combine_downloaded_files()
    elif len(sys.argv) > 1 and sys.argv[1] == '--auto':
        # Try automated download
        success = try_automated_download_with_playwright()
        if not success:
            manual_download_instructions()
    else:
        # Show manual download instructions
        manual_download_instructions()
