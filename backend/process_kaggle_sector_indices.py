#!/usr/bin/env python3
"""
Process Kaggle Indian Stock Market Index Data (1990-2022)
Extract 9 Nifty sector indices for 2020-2022 period
Source: https://www.kaggle.com/datasets/debashis74017/stock-market-index-data-india-1990-2022
"""

import pandas as pd
import os
from datetime import datetime

# Target 9 Nifty sector indices
TARGET_INDICES = [
    'Nifty Bank',
    'Nifty IT',
    'Nifty Auto',
    'Nifty Pharma',
    'Nifty FMCG',
    'Nifty Metal',
    'Nifty Realty',
    'Nifty Energy',
    'Nifty Media'
]

# Alternative names that might be in the dataset
INDEX_NAME_MAPPINGS = {
    'NIFTY BANK': 'Nifty Bank',
    'NIFTY IT': 'Nifty IT',
    'NIFTY AUTO': 'Nifty Auto',
    'NIFTY PHARMA': 'Nifty Pharma',
    'NIFTY FMCG': 'Nifty FMCG',
    'NIFTY METAL': 'Nifty Metal',
    'NIFTY REALTY': 'Nifty Realty',
    'NIFTY ENERGY': 'Nifty Energy',
    'NIFTY MEDIA': 'Nifty Media',
    'CNX Bank': 'Nifty Bank',
    'CNX IT': 'Nifty IT',
    'CNX Auto': 'Nifty Auto',
    'CNX Pharma': 'Nifty Pharma',
    'CNX FMCG': 'Nifty FMCG',
    'CNX Metal': 'Nifty Metal',
    'CNX Realty': 'Nifty Realty',
    'CNX Energy': 'Nifty Energy',
    'CNX Media': 'Nifty Media',
}

def download_from_kaggle():
    """
    Download dataset from Kaggle using Kaggle API
    Requires: pip install kaggle
    Requires: Kaggle API credentials in ~/.kaggle/kaggle.json
    """
    try:
        import kaggle
        
        print("📥 Downloading dataset from Kaggle...")
        dataset_name = "debashis74017/stock-market-index-data-india-1990-2022"
        download_path = "/app/backend/data/kaggle_raw"
        
        os.makedirs(download_path, exist_ok=True)
        
        kaggle.api.dataset_download_files(
            dataset_name,
            path=download_path,
            unzip=True
        )
        
        print(f"✓ Dataset downloaded to: {download_path}")
        return download_path
        
    except ImportError:
        print("✗ Kaggle library not installed")
        print("  Install with: pip install kaggle")
        return None
    except Exception as e:
        print(f"✗ Error downloading from Kaggle: {e}")
        print("\n📝 Manual Download Instructions:")
        print("  1. Go to: https://www.kaggle.com/datasets/debashis74017/stock-market-index-data-india-1990-2022")
        print("  2. Click 'Download' button")
        print("  3. Extract ZIP to: /app/backend/data/kaggle_raw/")
        print("  4. Run this script again")
        return None

def find_dataset_file(data_dir):
    """
    Find the main CSV file in the downloaded dataset
    """
    if not os.path.exists(data_dir):
        return None
    
    # Common patterns for the file
    possible_files = [
        'index_data.csv',
        'stock_market_index_data.csv',
        'india_index_data.csv',
        'indices.csv',
        'nifty_indices.csv'
    ]
    
    # Check for these specific files first
    for filename in possible_files:
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            return filepath
    
    # Otherwise, find any CSV file
    csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    
    if csv_files:
        print(f"\n📁 Found CSV files in {data_dir}:")
        for i, f in enumerate(csv_files, 1):
            print(f"  {i}. {f}")
        
        if len(csv_files) == 1:
            return os.path.join(data_dir, csv_files[0])
        else:
            # Return the largest file (likely the main dataset)
            largest_file = max(csv_files, key=lambda f: os.path.getsize(os.path.join(data_dir, f)))
            print(f"\n✓ Using largest file: {largest_file}")
            return os.path.join(data_dir, largest_file)
    
    return None

def process_kaggle_dataset(csv_file):
    """
    Process the Kaggle dataset and extract sector indices for 2020-2022
    """
    print(f"\n📊 Processing dataset: {csv_file}")
    
    # Read the CSV file
    df = pd.read_csv(csv_file)
    
    print(f"✓ Loaded {len(df):,} rows")
    print(f"\n📋 Dataset columns: {list(df.columns)}")
    print(f"\n📋 Sample data:")
    print(df.head())
    
    # Identify the column names (datasets may have different naming)
    # Common patterns: Date, Index/Symbol/Name, Open, High, Low, Close, Volume
    
    # Standardize column names
    column_mapping = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if 'date' in col_lower:
            column_mapping[col] = 'Date'
        elif 'index' in col_lower or 'symbol' in col_lower or 'name' in col_lower:
            column_mapping[col] = 'Index'
        elif 'open' in col_lower:
            column_mapping[col] = 'Open'
        elif 'high' in col_lower:
            column_mapping[col] = 'High'
        elif 'low' in col_lower:
            column_mapping[col] = 'Low'
        elif 'close' in col_lower:
            column_mapping[col] = 'Close'
        elif 'volume' in col_lower or 'vol' in col_lower:
            column_mapping[col] = 'Volume'
    
    df = df.rename(columns=column_mapping)
    
    print(f"\n✓ Standardized columns: {list(df.columns)}")
    
    # Convert date to datetime
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # Filter for 2020-2022 period
    start_date = pd.Timestamp('2020-01-01')
    end_date = pd.Timestamp('2022-12-31')
    
    df_filtered = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)].copy()
    
    print(f"\n✓ Filtered to 2020-2022: {len(df_filtered):,} rows")
    print(f"  Date range: {df_filtered['Date'].min()} to {df_filtered['Date'].max()}")
    
    # Check unique indices in the dataset
    if 'Index' in df_filtered.columns:
        unique_indices = df_filtered['Index'].unique()
        print(f"\n📊 Found {len(unique_indices)} unique indices in dataset:")
        for idx in sorted(unique_indices):
            print(f"  • {idx}")
    else:
        print("\n✗ Error: Could not find Index/Symbol column")
        return None
    
    # Find and filter for our target 9 sector indices
    # Try exact match first, then fuzzy matching
    found_indices = []
    sector_data = []
    
    for target in TARGET_INDICES:
        # Try exact match
        mask = df_filtered['Index'].str.contains(target, case=False, na=False)
        
        if mask.any():
            found_indices.append(target)
            sector_df = df_filtered[mask].copy()
            sector_df['Index'] = target  # Standardize name
            sector_data.append(sector_df)
            print(f"  ✓ Found: {target} ({len(sector_df)} rows)")
        else:
            # Try alternative names
            found = False
            for alt_name, standard_name in INDEX_NAME_MAPPINGS.items():
                if standard_name == target:
                    mask = df_filtered['Index'].str.contains(alt_name, case=False, na=False)
                    if mask.any():
                        found_indices.append(target)
                        sector_df = df_filtered[mask].copy()
                        sector_df['Index'] = target  # Standardize name
                        sector_data.append(sector_df)
                        print(f"  ✓ Found: {target} (as '{alt_name}') ({len(sector_df)} rows)")
                        found = True
                        break
            
            if not found:
                print(f"  ✗ Missing: {target}")
    
    if not sector_data:
        print("\n✗ Error: No target sector indices found in dataset")
        print("\n💡 Available indices that might be relevant:")
        for idx in sorted(unique_indices):
            if any(keyword in idx.lower() for keyword in ['nifty', 'cnx', 'bank', 'it', 'auto', 'pharma', 'fmcg', 'metal', 'realty', 'energy', 'media']):
                print(f"  • {idx}")
        return None
    
    # Combine all sector data
    final_df = pd.concat(sector_data, ignore_index=True)
    
    # Select required columns in specified order
    required_columns = ['Index', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    
    # Check if all columns exist
    missing_cols = [col for col in required_columns if col not in final_df.columns]
    if missing_cols:
        print(f"\n⚠️ Warning: Missing columns: {missing_cols}")
        # Add missing columns with NaN
        for col in missing_cols:
            final_df[col] = None
    
    final_df = final_df[required_columns]
    
    # Sort by Index and Date
    final_df = final_df.sort_values(['Index', 'Date'])
    
    # Remove duplicates
    final_df = final_df.drop_duplicates(subset=['Index', 'Date'])
    
    return final_df, found_indices

def save_output(df, output_file):
    """
    Save the processed data to CSV
    """
    df.to_csv(output_file, index=False)
    print(f"\n✅ SUCCESS! Data saved to: {output_file}")
    
    # Print summary statistics
    print(f"\n📊 Output Summary:")
    print(f"   Total rows: {len(df):,}")
    print(f"   Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
    print(f"   Number of indices: {df['Index'].nunique()}")
    
    # Per-index summary
    print(f"\n📈 Data by Index:")
    summary = df.groupby('Index').agg({
        'Date': ['count', 'min', 'max']
    })
    summary.columns = ['Row Count', 'Start Date', 'End Date']
    print(summary)
    
    # Check for missing data
    print(f"\n🔍 Data Quality Check:")
    missing = df.isnull().sum()
    if missing.sum() == 0:
        print(f"   ✓ No missing values!")
    else:
        print(f"   Missing values:")
        for col in missing[missing > 0].index:
            print(f"      {col}: {missing[col]}")
    
    return True

def main():
    """
    Main execution function
    """
    print("\n" + "="*80)
    print(" "*20 + "KAGGLE SECTOR INDICES PROCESSOR")
    print("="*80)
    
    # Try to find existing dataset first
    data_dirs = [
        "/app/backend/data/kaggle_raw",
        "/app/backend/data",
        "/app/backend"
    ]
    
    csv_file = None
    for data_dir in data_dirs:
        csv_file = find_dataset_file(data_dir)
        if csv_file:
            print(f"\n✓ Found dataset: {csv_file}")
            break
    
    # If not found, try to download
    if not csv_file:
        print("\n📁 Dataset not found locally")
        download_path = download_from_kaggle()
        
        if download_path:
            csv_file = find_dataset_file(download_path)
    
    # If still not found, provide manual instructions
    if not csv_file:
        print("\n" + "="*80)
        print(" "*25 + "MANUAL DOWNLOAD REQUIRED")
        print("="*80)
        print("\n📝 Instructions:")
        print("  1. Go to: https://www.kaggle.com/datasets/debashis74017/stock-market-index-data-india-1990-2022")
        print("  2. Click 'Download' button (you may need to create a Kaggle account)")
        print("  3. Extract the ZIP file")
        print("  4. Copy the CSV file to: /app/backend/data/kaggle_raw/")
        print("  5. Run this script again")
        print("\n" + "="*80)
        return False
    
    # Process the dataset
    result = process_kaggle_dataset(csv_file)
    
    if result is None:
        print("\n✗ Failed to process dataset")
        return False
    
    df, found_indices = result
    
    # Report findings
    print(f"\n✓ Successfully extracted {len(found_indices)}/9 target indices:")
    for idx in found_indices:
        print(f"  ✓ {idx}")
    
    missing = set(TARGET_INDICES) - set(found_indices)
    if missing:
        print(f"\n⚠️ Missing {len(missing)} indices:")
        for idx in missing:
            print(f"  ✗ {idx}")
    
    # Save output
    output_file = "/app/backend/sector_indices_2020_2022.csv"
    save_output(df, output_file)
    
    print("\n" + "="*80)
    print(" "*30 + "PROCESSING COMPLETE")
    print("="*80 + "\n")
    
    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("\nUsage:")
        print("  python process_kaggle_sector_indices.py         # Auto-detect and process")
        print("  python process_kaggle_sector_indices.py --help  # Show this help")
        print("\nDataset Source:")
        print("  https://www.kaggle.com/datasets/debashis74017/stock-market-index-data-india-1990-2022")
        print("\nOutput:")
        print("  /app/backend/sector_indices_2020_2022.csv")
        print()
    else:
        success = main()
        sys.exit(0 if success else 1)
