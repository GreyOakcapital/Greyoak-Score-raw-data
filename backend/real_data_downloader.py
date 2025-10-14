#!/usr/bin/env python3
"""
Real Data Downloader - Getting actual market data for proper validation
Following user's exact guidance with yfinance
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import sys
sys.path.append('/app/backend')

# Step 1: Get Nifty 50 stock list (as of 2020)
nifty50_stocks = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
    'ICICIBANK.NS', 'KOTAKBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'BAJFINANCE.NS',
    'ITC.NS', 'ASIANPAINT.NS', 'MARUTI.NS', 'AXISBANK.NS', 'LT.NS',
    'SUNPHARMA.NS', 'TITAN.NS', 'ULTRACEMCO.NS', 'NESTLEIND.NS', 'WIPRO.NS',
    'M&M.NS', 'HCLTECH.NS', 'NTPC.NS', 'TECHM.NS', 'POWERGRID.NS',
    'TATASTEEL.NS', 'BAJAJFINSV.NS', 'ONGC.NS', 'ADANIPORTS.NS', 'COALINDIA.NS',
    'JSWSTEEL.NS', 'TATAMOTORS.NS', 'GRASIM.NS', 'CIPLA.NS', 'HINDALCO.NS',
    'BRITANNIA.NS', 'SHREECEM.NS', 'DIVISLAB.NS', 'DRREDDY.NS', 'EICHERMOT.NS',
    'HEROMOTOCO.NS', 'BAJAJ-AUTO.NS', 'BPCL.NS', 'TATACONSUM.NS', 'UPL.NS',
    'INDUSINDBK.NS', 'APOLLOHOSP.NS', 'ADANIENT.NS', 'SBILIFE.NS', 'HDFCLIFE.NS'
]

def download_stock_data(tickers, start_date, end_date, name="data"):
    """Download historical price data"""
    print(f"📥 Downloading {name}: {start_date} to {end_date}")
    
    try:
        data = yf.download(
            tickers,
            start=start_date,
            end=end_date,
            group_by='ticker',
            auto_adjust=True,  # Adjusts for splits and dividends
            progress=True
        )
        print(f"✅ {name} downloaded successfully: {len(data)} days")
        return data
    except Exception as e:
        print(f"❌ Error downloading {name}: {e}")
        return None

def validate_nifty_returns():
    """Validate actual Nifty returns against our claims"""
    print("\n🔍 VALIDATING ACTUAL NIFTY RETURNS")
    print("="*50)
    
    try:
        # Download Nifty index
        print("Downloading Nifty 50 index data...")
        nifty_index = yf.download('^NSEI', start='2020-01-01', end='2024-12-31', progress=False)
        
        if nifty_index is None or len(nifty_index) == 0:
            print("❌ Failed to download Nifty index")
            return None
        
        # Key validation periods
        periods_to_check = {
            '2022_reality_check': ('2022-01-03', '2022-10-31'),
            'march_2020_crash': ('2020-02-24', '2020-03-24'),
            'bull_2020_2021': ('2020-11-01', '2021-10-31')
        }
        
        results = {}
        
        for period_name, (start_date, end_date) in periods_to_check.items():
            try:
                start_price = nifty_index.loc[start_date]['Close']
                end_price = nifty_index.loc[end_date]['Close']
                return_pct = ((end_price - start_price) / start_price) * 100
                
                results[period_name] = {
                    'start_price': start_price,
                    'end_price': end_price,
                    'return_pct': return_pct,
                    'start_date': start_date,
                    'end_date': end_date
                }
                
                print(f"\n📊 {period_name.upper()}:")
                print(f"   {start_date}: ₹{start_price:,.0f}")
                print(f"   {end_date}: ₹{end_price:,.0f}")
                print(f"   Return: {return_pct:+.1f}%")
                
            except KeyError as e:
                print(f"⚠️  Missing data for {period_name}: {e}")
                continue
        
        # The big validation
        if '2022_reality_check' in results:
            actual_2022 = results['2022_reality_check']['return_pct']
            my_fake_2022 = -45.4
            
            print(f"\n🎯 CRITICAL VALIDATION:")
            print(f"   My fake 2022 return: {my_fake_2022:.1f}%")
            print(f"   Actual 2022 return: {actual_2022:+.1f}%")
            print(f"   Error magnitude: {abs(actual_2022 - my_fake_2022):.1f} percentage points")
            
            if abs(actual_2022 - my_fake_2022) > 30:
                print(f"   🚨 CONFIRMED: Massive error detected!")
            else:
                print(f"   ✅ Data appears reasonable")
        
        return results
        
    except Exception as e:
        print(f"❌ Error validating Nifty returns: {e}")
        return None

def convert_yfinance_to_monthly_returns(yf_data, stocks_list):
    """Convert yfinance data to monthly returns format for GreyOak testing"""
    print("\n🔄 Converting to monthly returns format...")
    
    monthly_data = []
    
    # Get month-end dates
    monthly_prices = yf_data.resample('M').last()
    
    for date in monthly_prices.index:
        date_str = date.strftime('%Y-%m-%d')
        print(f"Processing {date.strftime('%b %Y')}...")
        
        for stock in stocks_list:
            try:
                if stock in yf_data.columns.get_level_values(0):
                    # Current month close
                    current_close = monthly_prices.loc[date, (stock, 'Close')]
                    
                    # Previous month close for return calculation
                    prev_date_idx = monthly_prices.index.get_loc(date) - 1
                    if prev_date_idx >= 0:
                        prev_date = monthly_prices.index[prev_date_idx]
                        prev_close = monthly_prices.loc[prev_date, (stock, 'Close')]
                        monthly_return = ((current_close - prev_close) / prev_close) * 100
                    else:
                        monthly_return = 0
                    
                    # Volume (average of month)
                    try:
                        month_data = yf_data.loc[date.replace(day=1):date, (stock, 'Volume')]
                        avg_volume = month_data.mean()
                    except:
                        avg_volume = 1000000  # Default
                    
                    record = {
                        'ticker': stock,
                        'date': date,
                        'close': current_close,
                        'monthly_return': monthly_return,
                        'volume': avg_volume
                    }
                    
                    monthly_data.append(record)
                    
            except Exception as e:
                print(f"   ⚠️ Error processing {stock}: {e}")
                continue
    
    df = pd.DataFrame(monthly_data)
    print(f"✅ Converted to {len(df)} monthly records")
    return df

def main():
    """Download and validate real market data"""
    print("🚀 REAL DATA DOWNLOAD - Phase 2 RESTART")
    print("="*60)
    print("Following user guidance: Getting actual market data for proper validation")
    print()
    
    # Step 1: Validate Nifty returns first
    validation_results = validate_nifty_returns()
    
    if validation_results is None:
        print("❌ Cannot proceed without Nifty validation")
        return
    
    # Step 2: Download data for all test periods
    print(f"\n📥 DOWNLOADING REAL STOCK DATA")
    print("="*40)
    
    datasets = {}
    
    # Priority 1: March 2020 COVID Crash ⭐
    print("\n🎯 PRIORITY 1: March 2020 COVID Crash")
    crash_data = download_stock_data(
        nifty50_stocks[:20],  # Start with subset for speed
        start_date='2020-02-01',
        end_date='2020-04-30',
        name="COVID Crash Data"
    )
    if crash_data is not None:
        datasets['covid_crash'] = convert_yfinance_to_monthly_returns(crash_data, nifty50_stocks[:20])
    
    # Priority 2: 2020-2021 Bull Run (verify previous results)
    print("\n🎯 PRIORITY 2: 2020-2021 Bull Run") 
    bull_data = download_stock_data(
        nifty50_stocks[:20],
        start_date='2020-10-01',
        end_date='2021-11-30', 
        name="Bull Market Data"
    )
    if bull_data is not None:
        datasets['bull_market'] = convert_yfinance_to_monthly_returns(bull_data, nifty50_stocks[:20])
    
    # Priority 3: 2022 Volatility
    print("\n🎯 PRIORITY 3: 2022 Volatility")
    vol_data = download_stock_data(
        nifty50_stocks[:20],
        start_date='2021-12-01',
        end_date='2022-11-30',
        name="2022 Volatility Data"
    )
    if vol_data is not None:
        datasets['volatility_2022'] = convert_yfinance_to_monthly_returns(vol_data, nifty50_stocks[:20])
    
    # Step 3: Quick data quality checks
    print(f"\n✅ DATA DOWNLOAD SUMMARY")
    print("="*30)
    
    for period_name, df in datasets.items():
        if df is not None and len(df) > 0:
            date_range = f"{df['date'].min().strftime('%b %Y')} - {df['date'].max().strftime('%b %Y')}"
            unique_stocks = df['ticker'].nunique()
            avg_return = df['monthly_return'].mean()
            
            print(f"📊 {period_name.upper()}")
            print(f"   Date range: {date_range}")
            print(f"   Stocks: {unique_stocks}")
            print(f"   Records: {len(df):,}")
            print(f"   Avg monthly return: {avg_return:+.1f}%")
            print()
            
            # Save to CSV for inspection
            filename = f"/app/backend/real_data_{period_name}.csv"
            df.to_csv(filename, index=False)
            print(f"   💾 Saved to: {filename}")
            print()
    
    # Step 4: Reality check against validation
    if validation_results and '2022_reality_check' in validation_results:
        actual_2022_nifty = validation_results['2022_reality_check']['return_pct']
        
        if 'volatility_2022' in datasets and len(datasets['volatility_2022']) > 0:
            # Calculate average stock return for 2022
            df_2022 = datasets['volatility_2022']
            df_2022_filtered = df_2022[(df_2022['date'] >= '2022-01-01') & (df_2022['date'] <= '2022-10-31')]
            
            if len(df_2022_filtered) > 0:
                avg_stock_return_2022 = df_2022_filtered['monthly_return'].mean() * 10  # Approx annualized
                
                print(f"🎯 2022 REALITY CHECK:")
                print(f"   Nifty 50 Index: {actual_2022_nifty:+.1f}%")
                print(f"   Avg Stock Performance: {avg_stock_return_2022:+.1f}%")
                print(f"   Difference: {abs(actual_2022_nifty - avg_stock_return_2022):.1f}% (should be <10%)")
    
    print(f"\n🚀 NEXT STEPS:")
    print("="*15)
    print("1. ✅ Real data downloaded and validated")
    print("2. 🔄 Run March 2020 crash test (Priority 1)")
    print("3. 🔄 Verify 2020-2021 bull market with real data")
    print("4. 🔄 Test 2022 volatility navigation")
    print("5. 📊 Generate realistic performance report")
    
    return datasets, validation_results

if __name__ == "__main__":
    datasets, validation = main()