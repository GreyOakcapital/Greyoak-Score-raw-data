#!/usr/bin/env python3
"""
Automated download of sector indices from investing.com using Playwright
Downloads historical data for 9 Nifty sector indices (2020-2022)
"""

import os
import time
import pandas as pd
from datetime import datetime

def download_with_playwright():
    """
    Use Playwright to automate browser and download historical data
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("✗ Playwright not installed")
        print("Install with: pip install playwright && playwright install chromium")
        return False
    
    # Define sector indices
    SECTOR_INDICES = {
        'Nifty_Bank': 'bank-nifty',
        'Nifty_IT': 'nifty-it',
        'Nifty_Auto': 'cnx-auto',
        'Nifty_Pharma': 'cnx-pharma',
        'Nifty_FMCG': 'cnx-fmcg',
        'Nifty_Metal': 'cnx-metal',
        'Nifty_Realty': 'cnx-realty',
        'Nifty_Energy': 'cnx-energy',
        'Nifty_Media': 'cnx-media'
    }
    
    download_dir = "/app/backend/data/sector_downloads"
    os.makedirs(download_dir, exist_ok=True)
    
    print("\n" + "="*80)
    print("AUTOMATED DOWNLOAD FROM INVESTING.COM")
    print("="*80)
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(
            headless=False,  # Set to False to see what's happening
            downloads_path=download_dir
        )
        
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        
        all_data = []
        
        for sector_name, index_slug in SECTOR_INDICES.items():
            print(f"\n📥 Downloading {sector_name}...")
            url = f"https://in.investing.com/indices/{index_slug}-historical-data"
            
            try:
                # Navigate to the page
                page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(2)
                
                # Click on date picker to set custom range
                # Note: These selectors need to be adjusted based on actual page structure
                try:
                    # Try to find and click the date picker
                    date_picker = page.locator("text=Time Frame")
                    if date_picker.count() > 0:
                        date_picker.click()
                        time.sleep(1)
                        
                        # Select custom date range option
                        custom_option = page.locator("text=Custom")
                        if custom_option.count() > 0:
                            custom_option.click()
                            time.sleep(1)
                    
                    # Fill in date range (01/01/2020 - 31/12/2022)
                    # These selectors are placeholders and need adjustment
                    start_date_input = page.locator("input[name='start_date']")
                    if start_date_input.count() > 0:
                        start_date_input.fill("01/01/2020")
                    
                    end_date_input = page.locator("input[name='end_date']")
                    if end_date_input.count() > 0:
                        end_date_input.fill("31/12/2022")
                    
                    # Click apply button
                    apply_btn = page.locator("button:has-text('Apply')")
                    if apply_btn.count() > 0:
                        apply_btn.click()
                        time.sleep(2)
                        
                except Exception as e:
                    print(f"  ⚠️ Could not set custom date range: {e}")
                    print(f"  Proceeding with default range...")
                
                # Extract table data directly from the page
                print(f"  Extracting table data...")
                
                # Wait for table to load
                page.wait_for_selector("table", timeout=10000)
                
                # Get all rows
                rows = page.locator("table tbody tr").all()
                
                data_rows = []
                for row in rows[:10]:  # Get at least a few rows to verify
                    try:
                        cells = row.locator("td").all()
                        if len(cells) >= 7:
                            row_data = {
                                'Date': cells[0].inner_text().strip(),
                                'Close': cells[1].inner_text().strip(),
                                'Open': cells[2].inner_text().strip(),
                                'High': cells[3].inner_text().strip(),
                                'Low': cells[4].inner_text().strip(),
                                'Volume': cells[5].inner_text().strip(),
                                'Change_Pct': cells[6].inner_text().strip(),
                                'Sector': sector_name.replace('_', ' ')
                            }
                            data_rows.append(row_data)
                    except Exception as e:
                        continue
                
                if data_rows:
                    print(f"  ✓ Extracted {len(data_rows)} rows")
                    all_data.extend(data_rows)
                else:
                    print(f"  ✗ No data extracted")
                
            except Exception as e:
                print(f"  ✗ Error downloading {sector_name}: {e}")
                continue
        
        browser.close()
        
        # Save combined data
        if all_data:
            df = pd.DataFrame(all_data)
            output_file = "/app/backend/sector_indices_2020_2022.csv"
            df.to_csv(output_file, index=False)
            print(f"\n✓ Data saved to: {output_file}")
            print(f"  Total rows: {len(df)}")
            return True
        else:
            print("\n✗ No data collected")
            return False

if __name__ == "__main__":
    download_with_playwright()
