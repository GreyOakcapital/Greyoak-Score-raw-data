#!/usr/bin/env python3
"""
Simplified Real Data Download - Testing individual stocks first
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
sys.path.append('/app/backend')

def test_single_stock():
    """Test downloading single stock first"""
    print("🔍 Testing single stock download...")
    
    try:
        # Test with most liquid stock
        ticker = yf.Ticker("RELIANCE.NS")
        
        # Get recent data
        hist = ticker.history(period="1y")
        
        if len(hist) > 0:
            print(f"✅ RELIANCE.NS data retrieved: {len(hist)} days")
            print(f"   Latest price: ₹{hist['Close'].iloc[-1]:.2f}")
            print(f"   Date range: {hist.index[0].date()} to {hist.index[-1].date()}")
            
            # Calculate some returns to verify
            monthly_returns = hist['Close'].resample('M').last().pct_change() * 100
            print(f"   Recent monthly returns: {monthly_returns.tail(3).values}")
            
            return True
        else:
            print("❌ No data retrieved")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def download_key_stocks_simple():
    """Download a few key stocks for testing"""
    print("\n📥 Downloading key stocks for validation...")
    
    # Start with just 5 most liquid stocks
    key_stocks = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ITC.NS']
    
    stock_data = {}
    
    for stock in key_stocks:
        print(f"   Downloading {stock}...")
        try:
            ticker = yf.Ticker(stock)
            
            # Get 3 years of data
            hist = ticker.history(start='2020-01-01', end='2023-12-31')
            
            if len(hist) > 0:
                stock_data[stock] = hist
                print(f"   ✅ {stock}: {len(hist)} days")
            else:
                print(f"   ❌ {stock}: No data")
                
        except Exception as e:
            print(f"   ❌ {stock}: Error - {e}")
            continue
    
    return stock_data

def calculate_period_returns(stock_data):
    """Calculate returns for key test periods"""
    print("\n📊 Calculating period returns...")
    
    results = {}
    
    # Define test periods
    periods = {
        'march_2020_crash': ('2020-02-24', '2020-03-24'),
        'bull_2020_2021': ('2020-11-01', '2021-10-31'), 
        'year_2022': ('2022-01-03', '2022-12-30')
    }
    
    for period_name, (start_date, end_date) in periods.items():
        print(f"\n🎯 {period_name.upper()}:")
        
        period_results = {}
        
        for stock, hist_data in stock_data.items():
            try:
                # Get start and end prices
                start_price = hist_data.loc[start_date:start_date]['Close'].iloc[0]
                end_price = hist_data.loc[end_date:end_date]['Close'].iloc[0]
                
                return_pct = ((end_price - start_price) / start_price) * 100
                
                period_results[stock] = {
                    'start_price': start_price,
                    'end_price': end_price,
                    'return_pct': return_pct
                }
                
                print(f"   {stock}: {return_pct:+6.1f}% (₹{start_price:.0f} → ₹{end_price:.0f})")
                
            except Exception as e:
                print(f"   {stock}: Error - {e}")
                continue
        
        if period_results:
            # Calculate average return (proxy for market)
            avg_return = np.mean([data['return_pct'] for data in period_results.values()])
            period_results['market_average'] = avg_return
            
            print(f"   📈 Market Average: {avg_return:+6.1f}%")
            
            # Validate against expectations
            if period_name == 'march_2020_crash':
                print(f"   🎯 Expected: -25% to -40% (COVID crash)")
                if -40 <= avg_return <= -25:
                    print(f"   ✅ Realistic crash data")
                else:
                    print(f"   ⚠️  Unexpected crash magnitude")
                    
            elif period_name == 'year_2022':
                print(f"   🎯 Expected: -5% to +10% (mixed year)")
                if -10 <= avg_return <= 15:
                    print(f"   ✅ Realistic 2022 data")
                else:
                    print(f"   ⚠️  Unexpected 2022 performance")
        
        results[period_name] = period_results
    
    return results

def create_monthly_dataset(stock_data, period_name, start_date, end_date):
    """Create monthly dataset for backtesting"""
    print(f"\n📅 Creating monthly dataset for {period_name}...")
    
    monthly_records = []
    
    # Filter date range
    period_start = pd.to_datetime(start_date)
    period_end = pd.to_datetime(end_date)
    
    # Get monthly data for each stock
    for stock, hist_data in stock_data.items():
        try:
            # Filter to period
            period_data = hist_data.loc[period_start:period_end]
            
            if len(period_data) == 0:
                continue
            
            # Resample to monthly
            monthly_data = period_data.resample('M').agg({
                'Open': 'first',
                'High': 'max', 
                'Low': 'min',
                'Close': 'last',
                'Volume': 'mean'
            })
            
            # Calculate monthly returns
            monthly_returns = monthly_data['Close'].pct_change() * 100
            
            for date, row in monthly_data.iterrows():
                monthly_return = monthly_returns.loc[date]
                
                if pd.isna(monthly_return):
                    monthly_return = 0
                
                record = {
                    'ticker': stock.replace('.NS', ''),  # Clean ticker
                    'date': date,
                    'close': row['Close'],
                    'monthly_return': monthly_return,
                    'volume': row['Volume'],
                    'period': period_name
                }
                
                monthly_records.append(record)
                
        except Exception as e:
            print(f"   ⚠️ Error processing {stock}: {e}")
            continue
    
    df = pd.DataFrame(monthly_records)
    
    if len(df) > 0:
        print(f"   ✅ Created {len(df)} monthly records")
        print(f"   Date range: {df['date'].min().strftime('%b %Y')} - {df['date'].max().strftime('%b %Y')}")
        print(f"   Stocks: {df['ticker'].nunique()}")
        print(f"   Avg monthly return: {df['monthly_return'].mean():+.1f}%")
        
        # Save for inspection
        filename = f"/app/backend/real_monthly_{period_name}.csv"
        df.to_csv(filename, index=False)
        print(f"   💾 Saved to: {filename}")
    
    return df

def main():
    """Main execution with error handling"""
    print("🚀 REAL DATA VALIDATION - Simplified Approach")
    print("="*60)
    
    # Step 1: Test single stock connectivity
    if not test_single_stock():
        print("❌ Cannot connect to yfinance. Check internet connection.")
        return None
    
    # Step 2: Download key stocks
    stock_data = download_key_stocks_simple()
    
    if not stock_data:
        print("❌ No stock data downloaded")
        return None
    
    print(f"\n✅ Successfully downloaded {len(stock_data)} stocks")
    
    # Step 3: Calculate key period returns
    period_results = calculate_period_returns(stock_data)
    
    # Step 4: Create monthly datasets for backtesting
    datasets = {}
    
    # March 2020 crash dataset
    if 'march_2020_crash' in period_results:
        crash_df = create_monthly_dataset(
            stock_data, 
            'march_2020_crash', 
            '2020-02-01', 
            '2020-04-30'
        )
        datasets['crash'] = crash_df
    
    # 2022 volatility dataset  
    if 'year_2022' in period_results:
        vol_df = create_monthly_dataset(
            stock_data,
            'volatility_2022',
            '2021-12-01',
            '2022-12-31'
        )
        datasets['volatility'] = vol_df
    
    # Summary
    print(f"\n📊 VALIDATION SUMMARY")
    print("="*25)
    
    for period, results in period_results.items():
        if 'market_average' in results:
            avg_return = results['market_average']
            print(f"{period}: {avg_return:+6.1f}% market return")
    
    print(f"\n🎯 KEY VALIDATION:")
    if 'year_2022' in period_results:
        actual_2022 = period_results['year_2022']['market_average']
        print(f"   2022 actual return: {actual_2022:+.1f}%")
        print(f"   My fake 2022 return: -45.4%")
        print(f"   Error magnitude: {abs(actual_2022 - (-45.4)):.1f} percentage points")
        
        if abs(actual_2022 - (-45.4)) > 30:
            print(f"   🚨 CONFIRMED: Massive error in original data")
        else:
            print(f"   ⚠️  Error not as severe as expected")
    
    print(f"\n✅ Ready for realistic backtesting with actual market data")
    
    return datasets, period_results

if __name__ == "__main__":
    result = main()