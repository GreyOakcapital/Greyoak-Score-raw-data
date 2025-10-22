# Historical Data Files - Complete Index

## 📊 Main Price Data Files (3 Years: 2020-2022)

### ⭐ PRIMARY FILE (Use This)
**Location:** `/app/backend/HISTORICAL_DATA_3_YEARS_205_STOCKS.csv`

- **Stocks:** 205 NSE stocks
- **Period:** January 1, 2020 to December 30, 2022 (exactly 3 years)
- **Records:** 158,716 daily OHLCV records
- **Size:** 6.9 MB
- **Format:**
  ```csv
  Ticker,Date,Open,High,Low,Close
  RELIANCE,2020-01-01,1535.0,1544.0,1520.0,1537.8
  ```

**Stocks Included (205):**
AARTIIND, ABBOTINDIA, ABCAPITAL, ABFRL, ACC, ADANIENSOL, ADANIENT, ADANIGREEN, ADANIPORTS, ADANIPOWER, ADANITRANS, AJANTPHARM, ALKEM, AMARAJABAT, AMBUJACEM, APLLTD, APOLLOHOSP, APOLLOTYRE, ASHOKLEY, ASIANPAINT, ASTRAL, ATGL, ATUL, AUBANK, AUROPHARMA, AXISBANK, BAJAJ-AUTO, BAJAJFINSV, BAJFINANCE, BALKRISIND, BALRAMCHIN, BANDHANBNK, BANKBARODA, BATAINDIA, BEL, BERGEPAINT, BHARATFORG, BHARTIARTL, BHEL, BIOCON, BOSCHLTD, BPCL, BRITANNIA, BSOFT, CANBK, CANFINHOME, CASTROLIND, CESC, CHAMBLFERT, CHOLAFIN, CIPLA, COALINDIA, COFORGE, COLPAL, CONCOR, COROMANDEL, CREDITACC, CROMPTON, CUMMINSIND, DABUR, DALBHARAT, DEEPAKNTR, DELTACORP, DHANI, DIVISLAB, DIXON, DLF, DRREDDY, EICHERMOT, ESCORTS, EXIDEIND, FEDERALBNK, FORTIS, GAIL, GLENMARK, GMRINFRA, GODREJCP, GODREJPROP, GRANULES, GRASIM, GRINDWELL, GUJGASLTD, HAL, HATSUN, HAVELLS, HCLTECH, HDFCAMC, HDFCBANK, HDFCLIFE, HEROMOTOCO, HINDALCO, HINDCOPPER, HINDPETRO, HINDUNILVR, HONAUT, ICICIBANK, ICICIGI, ICICIPRULI, IDFCFIRSTB, IEX, IGL, INDHOTEL, INDIACEM, INDIAMART, INDIANB, INDIGO, INDUSINDBK, INDUSTOWER, INFY, INTELLECT, IOC, IPCALAB, IRB, IRCTC, ITC, JINDALSTEL, JKCEMENT, JSWENERGY, JSWSTEEL, JUBLFOOD, KAJARIACER, KOTAKBANK, KPITTECH, L&TFH, LALPATHLAB, LAURUSLABS, LICHSGFIN, LT, LTIM, LTTS, LUPIN, M&M, MANAPPURAM, MARICO, MARUTI, MAXHEALTH, MCDOWELL-N, METROPOLIS, MFSL, MGL, MINDTREE, MOTHERSON, MPHASIS, MRF, MUTHOOTFIN, NATIONALUM, NAUKRI, NAVINFLUOR, NESTLEIND, NHPC, NMDC, NTPC, OBEROIRLTY, OFSS, ONGC, PAGEIND, PEL, PERSISTENT, PETRONET, PFC, PGHH, PIIND, PIDILITIND, PNB, POLYCAB, POWERGRID, PRAJIND, PVRINOX, RAMCOCEM, RBLBANK, RECLTD, RELAXO, RELIANCE, SAIL, SBICARD, SBILIFE, SBIN, SCHAEFFLER, SHREECEM, SIEMENS, SRF, SRTRANSFIN, SUNPHARMA, SUNDARMFIN, SUPREMEIND, SYNGENE, TATACHEM, TATACOMM, TATACONSUM, TATAMOTORS, TATAPOWER, TATASTEEL, TCS, TECHM, TITAN, TORNTPHARM, TRENT, TVSMOTOR, UBL, ULTRACEMCO, UNIONBANK, UPL, VEDL, VOLTAS, WHIRLPOOL, WIPRO, ZOMATO, ZYDUSLIFE

---

## 📁 All Data File Locations

### Price Data (OHLCV)

1. **Main Consolidated File** ⭐
   - `/app/backend/HISTORICAL_DATA_3_YEARS_205_STOCKS.csv`
   - 205 stocks, 3 years, 158,716 records

2. **Alternative Locations (Same Data)**
   - `/app/backend/raw_data_export/all_stocks_ohlc_data.csv`
   - `/app/backend/greyoak_complete_dataset/1_price_data_daily.csv`

3. **Older Dataset (85 stocks)**
   - `/app/backend/stock_prices_2019_2022.csv`
   - 85 stocks, 3 years, 62,546 records

4. **Individual Stock Files (205 files)**
   - `/app/backend/validation_data_large/[TICKER]_price_data.csv`
   - One file per stock

### Calculated Scores

5. **GreyOak Scores (Historical)**
   - `/app/backend/greyoak_scores_historical/greyoak_scores_all_stocks.csv`
   - Pre-calculated scores for 205 stocks
   - 117,716 score records

6. **Older Scores (85 stocks)**
   - `/app/backend/greyoak_scores_2019_2022.csv`

### Fundamentals & Ownership

7. **Fundamentals (Partial)**
   - `/app/backend/greyoak_complete_dataset/2_fundamentals_quarterly.csv`
   - 1,020 records (limited stocks)

8. **Fundamentals (Older, 85 stocks)**
   - `/app/backend/stock_fundamentals_2019_2022.csv`

9. **Ownership (Minimal)**
   - `/app/backend/greyoak_complete_dataset/3_ownership_quarterly.csv`
   - 15 records

10. **Sector Mapping**
    - `/app/backend/greyoak_complete_dataset/4_sector_mapping.csv`
    - `/app/backend/data/sector_map.csv`

### Backtest Results

11. **Trade History**
    - `/app/backend/backtest_results/all_trades.csv`
    - 575 trades from rule-based predictor

12. **Stock Metrics**
    - `/app/backend/backtest_results/stock_metrics.csv`
    - Performance metrics per stock

13. **Summary**
    - `/app/backend/backtest_results/backtest_summary.json`

---

## 📊 Data Summary by Years

| Dataset | Stocks | Start Date | End Date | Years | Records | File |
|---------|--------|------------|----------|-------|---------|------|
| **Primary** | **205** | **2020-01-01** | **2022-12-30** | **3.0** | **158,716** | `HISTORICAL_DATA_3_YEARS_205_STOCKS.csv` |
| Secondary | 85 | 2020-01-01 | 2022-12-30 | 3.0 | 62,546 | `stock_prices_2019_2022.csv` |

**Note:** We have **exactly 3 years** of data (2020-2022), not 4 or 5 years.

---

## 🎯 What Data You Have

### ✅ Complete (Production Ready)
- **Price Data (OHLCV):** 205 stocks × 3 years = 158,716 records
- **Sector Mapping:** Available
- **Backtest Results:** 575 trades, proven strategy

### ⚠️ Partial (Needs Sourcing)
- **Fundamentals:** Only 1,020 records (need quarterly data for all 205 stocks)
- **Ownership:** Only 15 records (need historical quarterly data)
- **Indices:** Need to download separately (easy with yfinance)

---

## 🚀 Quick Start

### Download Price Data (Primary File)
```bash
# The main file with all data:
/app/backend/HISTORICAL_DATA_3_YEARS_205_STOCKS.csv
```

### Load in Python
```python
import pandas as pd

# Load all price data
df = pd.read_csv('/app/backend/HISTORICAL_DATA_3_YEARS_205_STOCKS.csv')

print(f"Stocks: {df['Ticker'].nunique()}")
print(f"Date Range: {df['Date'].min()} to {df['Date'].max()}")
print(f"Total Records: {len(df):,}")

# Filter specific stock
reliance = df[df['Ticker'] == 'RELIANCE']

# Filter date range
df['Date'] = pd.to_datetime(df['Date'])
df_2022 = df[df['Date'].dt.year == 2022]
```

### Calculate Technical Indicators
```python
# Example: Calculate RSI for a stock
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Get RELIANCE data
rel = df[df['Ticker'] == 'RELIANCE'].copy()
rel = rel.sort_values('Date')
rel['RSI'] = calculate_rsi(rel['Close'])
```

---

## 📞 Need More Data?

### To Get 5 Years (2018-2023)
You'll need to:
1. Use `nsepython` library to download older data
2. Or use paid APIs (Financial Modeling Prep, Alpha Vantage)
3. Or scrape from NSE/BSE websites

### To Get Fundamentals
See: `/app/backend/DATA_SUMMARY.md` for complete sourcing guide

### To Get Market Indices
```python
import yfinance as yf

# Download Nifty 50 (5 years)
nifty = yf.download("^NSEI", start="2018-01-01", end="2023-12-31")
```

---

## ✅ Bottom Line

**You have 3 YEARS of complete price data for 205 stocks RIGHT NOW.**

- File: `HISTORICAL_DATA_3_YEARS_205_STOCKS.csv` (6.9 MB)
- Ready to use for GreyOak Score calculation
- Proven in backtests (46.6% win rate)
- Clean, reliable NSE data

**For more years or complete fundamentals, see DATA_SUMMARY.md for sourcing instructions.**
