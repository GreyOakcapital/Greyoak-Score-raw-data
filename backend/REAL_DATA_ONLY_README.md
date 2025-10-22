# GreyOak Dataset - REAL DATA ONLY

## ✅ Policy: NO SYNTHETIC DATA

All data must be from verifiable, authentic public sources. Synthetic or simulated data has been removed.

---

## 📦 Available REAL Data

### ✅ Complete & Verified

| File | Source | Records | Status |
|------|--------|---------|--------|
| **HISTORICAL_DATA_3_YEARS_205_STOCKS.csv** | NSE via nsepython | 158,716 | ✅ Real |
| **stable_sector_map_2020_2022.csv** | Manual classification | 205 | ✅ Real |
| **trading_calendar_2020_2022.csv** | Extracted from NSE data | 1,096 | ✅ Real |
| **data_quality_flags_2020_2022.csv** | Calculated from price data | 158,716 | ✅ Real |

**Total REAL data:** 6.9 MB (price) + 11 MB (quality flags) = ~18 MB

---

## ❌ Missing Data (Requires Collection)

### 1. Sector Indices (Daily OHLCV)

**Required:** Nifty 50, Bank, IT, Auto, Pharma, Metal, FMCG, Energy, PSU Bank

**Source:** https://www1.nseindia.com/products/content/equities/indices/historical_index_data.htm

**Steps:**
1. Visit NSE indices historical data page
2. For each index:
   - Select index name
   - Set date range: 01-Jan-2020 to 31-Dec-2022
   - Click 'Get Data'
   - Download CSV
3. Save files to `/app/backend/real_data/indices/`

**Time Required:** ~20 minutes (manual)

**File Format:**
```csv
Date,Open,High,Low,Close,Shares Traded,Turnover (Rs. Cr)
01-Jan-2020,12100.0,12150.0,12050.0,12120.0,225000000,8500.0
```

---

### 2. Quarterly Fundamentals

**Required:** EPS, P/E, P/B, ROE, ROCE, Debt/Equity, margins, growth rates

**Source Options:**

**Option A: Screener.in (Free, requires scraping)**
- URL Pattern: `https://www.screener.in/company/{TICKER}/consolidated/`
- Contains: Quarterly results, key ratios, financial statements
- **Pros:** Free, comprehensive data
- **Cons:** Requires web scraping, rate limiting needed
- **Time:** 2-3 days to build robust scraper

**Option B: NSE Corporate Filings (Free, manual)**
- URL: https://www.nseindia.com/companies-listing/corporate-filings-financial-results
- Contains: Official quarterly results (PDF)
- **Pros:** Official source, accurate
- **Cons:** Requires PDF parsing, manual effort
- **Time:** 1-2 weeks for 205 stocks

**Option C: Paid API (Fastest)**
- Financial Modeling Prep: $29-99/mo
- Alpha Vantage: $49/mo
- **Pros:** Clean JSON/CSV, immediate access
- **Cons:** Monthly cost
- **Time:** 1-2 days integration

**Required Fields:**
```csv
ticker,quarter_end,eps,pe_ratio,pb_ratio,roe_3y,roce_3y,debt_equity,dividend_yield,sales_cagr_3y,opm,market_cap_cr
RELIANCE,2020-03-31,62.5,15.2,2.1,12.5,11.8,0.45,0.35,10.2,8.5,850000
```

---

### 3. Quarterly Ownership

**Required:** Promoter%, FII%, DII%, Retail%, Pledge%

**Source Options:**

**Option A: NSE Shareholding Pattern (Free, manual)**
- URL: https://www.nseindia.com/ → Company → Shareholding Pattern
- Contains: Quarterly shareholding reports (PDF/Excel)
- **Pros:** Official, accurate
- **Cons:** Requires PDF parsing
- **Time:** 1-2 weeks for 205 stocks

**Option B: Screener.in (Free, scraping)**
- Has shareholding history on company pages
- **Time:** Same as fundamentals scraper

**Option C: Paid API**
- Same providers as fundamentals
- **Time:** 1-2 days

**Required Fields:**
```csv
ticker,quarter_end,promoter_pct,promoter_pledge_pct,fii_pct,dii_pct,retail_pct,free_float_pct
RELIANCE,2020-03-31,50.25,0.0,22.35,18.40,9.00,49.75
```

---

## 🎯 What You Can Do NOW (With Existing REAL Data)

### ✅ Technicals Pillar (100% Complete)

```python
import pandas as pd
import numpy as np

# Load real price data
df = pd.read_csv('HISTORICAL_DATA_3_YEARS_205_STOCKS.csv')
df['Date'] = pd.to_datetime(df['Date'])

# Calculate technical indicators
def calculate_technicals(ticker_data):
    close = ticker_data['Close']
    
    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Moving averages
    dma20 = close.rolling(20).mean()
    dma50 = close.rolling(50).mean()
    dma200 = close.rolling(200).mean()
    
    # ATR
    high = ticker_data['High']
    low = ticker_data['Low']
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    
    # Breakouts
    high_20d = high.rolling(20).max()
    breakout = close > high_20d.shift(1)
    
    return {
        'rsi': rsi.iloc[-1],
        'dma20': dma20.iloc[-1],
        'dma50': dma50.iloc[-1],
        'dma200': dma200.iloc[-1],
        'atr': atr.iloc[-1],
        'breakout': breakout.iloc[-1]
    }

# Example: Calculate for RELIANCE
reliance = df[df['Ticker'] == 'RELIANCE'].sort_values('Date')
indicators = calculate_technicals(reliance)
print(indicators)
```

**Result:** Technical pillar can be calculated with 100% real NSE data.

---

### ⚠️ Relative Strength (Needs Indices)

Once you manually download sector indices:

```python
# Load indices (after manual download)
df_indices = pd.read_csv('sector_indices_2020_2022.csv')

# Calculate RS for a stock
def calculate_relative_strength(stock_data, index_data):
    # Align dates
    merged = stock_data.merge(index_data, on='Date')
    
    # Calculate returns
    stock_ret = merged['Close_stock'].pct_change()
    index_ret = merged['Close_index'].pct_change()
    
    # Relative strength
    rs = (1 + stock_ret) / (1 + index_ret)
    
    # RS score (0-100)
    rs_score = rs.rolling(60).apply(lambda x: (x > 1).sum() / len(x) * 100)
    
    return rs_score.iloc[-1]
```

---

## 📋 Recommended Action Plan

### Phase 1: Immediate (Use Real Price Data)
1. ✅ Calculate Technicals Pillar for all 205 stocks
2. ✅ Implement rule-based predictor (price + technicals only)
3. ✅ Backtest with real data
4. ✅ Validate technical analysis framework

**Outcome:** Working predictor with 1 pillar (Technicals), real data only

---

### Phase 2: Manual Data Collection (1 week)
1. Download sector indices from NSE (~20 min)
2. Manually collect fundamentals for top 50 stocks (1 week)
3. Manually collect ownership for top 50 stocks (1 week)

**Outcome:** Partial multi-pillar scoring (50 stocks complete)

---

### Phase 3: Complete Coverage (2-4 weeks OR pay for API)

**Option A: Build Scrapers (Free)**
- Screener.in scraper for fundamentals (2-3 days)
- NSE shareholding parser (2-3 days)
- Run for all 205 stocks (1 week)

**Option B: Use Paid API ($50-100/mo)**
- Sign up for Financial Modeling Prep or Alpha Vantage
- Download all data via API (2 days)
- Format and validate (1 day)

**Outcome:** Complete 6-pillar GreyOak Score on 205 stocks

---

## 🚀 Quick Start (Real Data Only)

### 1. Load Available Real Data

```python
import pandas as pd

# Price data (Real)
prices = pd.read_csv('HISTORICAL_DATA_3_YEARS_205_STOCKS.csv')

# Sector mapping (Real)
sectors = pd.read_csv('stable_sector_map_2020_2022.csv')

# Trading calendar (Real)
calendar = pd.read_csv('trading_calendar_2020_2022.csv')

# Quality flags (Real)
quality = pd.read_csv('data_quality_flags_2020_2022.csv')
```

### 2. Calculate What's Possible

```python
# Calculate technical indicators for all stocks
from concurrent.futures import ProcessPoolExecutor

def process_stock(ticker):
    stock_data = prices[prices['Ticker'] == ticker]
    if len(stock_data) < 200:
        return None
    return calculate_technicals(stock_data)

# Process all stocks in parallel
with ProcessPoolExecutor() as executor:
    results = list(executor.map(process_stock, prices['Ticker'].unique()))
```

---

## ✅ Data Integrity Guarantee

**All files in this repository contain ONLY:**
1. ✅ Real NSE price data (via nsepython)
2. ✅ Real trading calendar (from NSE dates)
3. ✅ Real sector classifications
4. ✅ Calculated metrics from real data

**ZERO synthetic, simulated, or placeholder data.**

**Missing data is clearly marked and instructions provided for collection.**

---

## 📞 Support

**For data collection:**
- See `source_real_data_only.py` for detailed instructions
- Check NSE/Screener.in terms of service before scraping
- Consider paid APIs for faster, cleaner data access

**For validation:**
- Run `validate_complete_dataset.py` to check available data
- All validations use real data only

---

## 📝 File Manifest

### In Repository (Real Data)
```
/app/backend/
├── HISTORICAL_DATA_3_YEARS_205_STOCKS.csv (6.9 MB) ✅ Real
├── stable_sector_map_2020_2022.csv (10 KB) ✅ Real
├── trading_calendar_2020_2022.csv (33 KB) ✅ Real
├── data_quality_flags_2020_2022.csv (10.6 MB) ✅ Real
└── REAL_DATA_ONLY_README.md (This file)
```

### Not In Repository (Need Collection)
```
- sector_indices_2020_2022.csv ❌ Need manual download
- fundamentals_quarterly_2020_2022.csv ❌ Need scraping or API
- ownership_quarterly_2020_2022.csv ❌ Need scraping or API
```

---

## 🎯 Bottom Line

**Current State:**
- ✅ Real price data for 205 stocks (3 years)
- ✅ Can calculate Technicals pillar immediately
- ❌ Need to collect indices, fundamentals, ownership

**To Proceed:**
1. Start with technical analysis (available now)
2. Manually download indices (20 min)
3. Decide on fundamentals/ownership source (scrape vs pay)
4. Collect data incrementally
5. Never use synthetic/placeholder data

**Quality over completeness. Real data only.**
