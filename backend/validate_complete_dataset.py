#!/usr/bin/env python3
"""
Validate Complete Dataset - Test GreyOak Score Computation Offline
Confirms all required data is present and properly formatted
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime


def validate_file(filepath, expected_cols, min_rows=0):
    """Validate a data file"""
    path = Path(filepath)
    
    if not path.exists():
        return False, f"❌ File not found: {filepath}"
    
    try:
        df = pd.read_csv(path)
        
        # Check columns
        missing_cols = set(expected_cols) - set(df.columns)
        if missing_cols:
            return False, f"❌ Missing columns: {missing_cols}"
        
        # Check rows
        if len(df) < min_rows:
            return False, f"❌ Too few rows: {len(df)} < {min_rows}"
        
        return True, f"✅ OK: {len(df):,} rows, {df.shape[1]} cols"
        
    except Exception as e:
        return False, f"❌ Error reading file: {e}"


def main():
    """Run complete validation"""
    print("="*70)
    print("COMPLETE DATASET VALIDATION")
    print("="*70)
    print("\nValidating all required files for offline GreyOak Score computation...")
    
    results = []
    
    # 1. Price Data
    print("\n1️⃣  Price Data (OHLCV)")
    status, msg = validate_file(
        '/app/backend/HISTORICAL_DATA_3_YEARS_205_STOCKS.csv',
        ['Ticker', 'Date', 'Open', 'High', 'Low', 'Close'],
        min_rows=100000
    )
    print(f"   {msg}")
    results.append(('Price Data', status))
    
    # 2. Sector Indices
    print("\n2️⃣  Sector Indices")
    status, msg = validate_file(
        '/app/backend/sector_indices_2020_2022.csv',
        ['Index', 'Date', 'Open', 'High', 'Low', 'Close'],
        min_rows=5000
    )
    print(f"   {msg}")
    results.append(('Sector Indices', status))
    
    # 3. Fundamentals
    print("\n3️⃣  Quarterly Fundamentals")
    status, msg = validate_file(
        '/app/backend/fundamentals_quarterly_2020_2022.csv',
        ['ticker', 'quarter_end', 'pe_ratio', 'pb_ratio', 'roe_3y', 'roce_3y'],
        min_rows=2000
    )
    print(f"   {msg}")
    results.append(('Fundamentals', status))
    
    # 4. Ownership
    print("\n4️⃣  Quarterly Ownership")
    status, msg = validate_file(
        '/app/backend/ownership_quarterly_2020_2022.csv',
        ['ticker', 'quarter_end', 'promoter_pct', 'fii_pct', 'dii_pct'],
        min_rows=2000
    )
    print(f"   {msg}")
    results.append(('Ownership', status))
    
    # 5. Sector Mapping
    print("\n5️⃣  Sector Mapping")
    status, msg = validate_file(
        '/app/backend/stable_sector_map_2020_2022.csv',
        ['Ticker', 'Sector_ID', 'Sector_Group'],
        min_rows=200
    )
    print(f"   {msg}")
    results.append(('Sector Map', status))
    
    # 6. Trading Calendar
    print("\n6️⃣  Trading Calendar")
    status, msg = validate_file(
        '/app/backend/trading_calendar_2020_2022.csv',
        ['Date', 'Is_Trading_Day'],
        min_rows=1000
    )
    print(f"   {msg}")
    results.append(('Trading Calendar', status))
    
    # 7. Data Quality Flags
    print("\n7️⃣  Data Quality Flags")
    status, msg = validate_file(
        '/app/backend/data_quality_flags_2020_2022.csv',
        ['Ticker', 'Date', 'Quality_Issue'],
        min_rows=100000
    )
    print(f"   {msg}")
    results.append(('Quality Flags', status))
    
    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, status in results if status)
    total = len(results)
    
    print(f"\n✅ Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("\n✅ Dataset is complete and ready for offline GreyOak Score computation")
        
        # Show coverage summary
        print("\n📊 Data Coverage:")
        
        df_price = pd.read_csv('/app/backend/HISTORICAL_DATA_3_YEARS_205_STOCKS.csv')
        df_fund = pd.read_csv('/app/backend/fundamentals_quarterly_2020_2022.csv')
        df_own = pd.read_csv('/app/backend/ownership_quarterly_2020_2022.csv')
        df_indices = pd.read_csv('/app/backend/sector_indices_2020_2022.csv')
        
        print(f"\n   Price Data:")
        print(f"      Stocks: {df_price['Ticker'].nunique()}")
        print(f"      Date Range: {df_price['Date'].min()} to {df_price['Date'].max()}")
        print(f"      Records: {len(df_price):,}")
        
        print(f"\n   Fundamentals:")
        print(f"      Stocks: {df_fund['ticker'].nunique()}")
        print(f"      Quarters: {df_fund['quarter_end'].nunique()}")
        print(f"      Records: {len(df_fund):,}")
        print(f"      Columns: {', '.join([c for c in df_fund.columns if c not in ['ticker', 'quarter_end', 'data_source']])}")
        
        print(f"\n   Ownership:")
        print(f"      Stocks: {df_own['ticker'].nunique()}")
        print(f"      Quarters: {df_own['quarter_end'].nunique()}")
        print(f"      Records: {len(df_own):,}")
        
        print(f"\n   Sector Indices:")
        print(f"      Indices: {df_indices['Index'].nunique()}")
        print(f"      Trading Days: {df_indices['Date'].nunique()}")
        print(f"      Records: {len(df_indices):,}")
        
        print("\n📋 Files Ready for GitHub:")
        files = [
            'HISTORICAL_DATA_3_YEARS_205_STOCKS.csv',
            'sector_indices_2020_2022.csv',
            'fundamentals_quarterly_2020_2022.csv',
            'ownership_quarterly_2020_2022.csv',
            'stable_sector_map_2020_2022.csv',
            'trading_calendar_2020_2022.csv',
            'data_quality_flags_2020_2022.csv'
        ]
        
        for f in files:
            path = Path('/app/backend') / f
            if path.exists():
                size = path.stat().st_size / 1024 / 1024
                print(f"   ✅ {f} ({size:.1f} MB)")
        
        print("\n💡 Usage Example:")
        print("""
   import pandas as pd
   
   # Load all data
   prices = pd.read_csv('HISTORICAL_DATA_3_YEARS_205_STOCKS.csv')
   fundamentals = pd.read_csv('fundamentals_quarterly_2020_2022.csv')
   ownership = pd.read_csv('ownership_quarterly_2020_2022.csv')
   indices = pd.read_csv('sector_indices_2020_2022.csv')
   
   # Calculate GreyOak Score for a stock on a specific date
   ticker = 'RELIANCE'
   date = '2022-06-30'
   
   # Get price data up to date
   hist = prices[(prices['Ticker'] == ticker) & (prices['Date'] <= date)]
   
   # Get latest fundamentals
   fund = fundamentals[
       (fundamentals['ticker'] == ticker) & 
       (fundamentals['quarter_end'] <= date)
   ].iloc[-1]
   
   # Calculate score...
        """)
        
    else:
        print(f"\n❌ {total - passed} validation(s) failed")
        print("\nFailed validations:")
        for name, status in results:
            if not status:
                print(f"   ❌ {name}")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
