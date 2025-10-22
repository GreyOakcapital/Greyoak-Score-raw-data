# GreyOak Score - Complete Dataset

## 📊 Available Data

### ✅ 1. Price Data (Daily OHLCV)
- **File:** `1_price_data_daily.csv`
- **Records:** 158,716
- **Stocks:** 205
- **Period:** 2020-2022 (3 years)
- **Columns:** Ticker, Date, Open, High, Low, Close
- **Status:** COMPLETE ✅

### ⚠️ 2. Fundamentals (Quarterly)
- **File:** `2_fundamentals_quarterly.csv`
- **Records:** 1,021
- **Stocks:** LIMITED (not all 205)
- **Columns:** date, symbol, roe, debt_equity, profit_margin, net_profit
- **Missing:**
  - EPS (Earnings Per Share)
  - ROCE (Return on Capital Employed)
  - P/E Ratio (Price to Earnings)
  - P/B Ratio (Price to Book)
  - Dividend Yield
  - Sales CAGR
  - Complete coverage for all 205 stocks

### ⚠️ 3. Ownership (Quarterly)
- **File:** `3_ownership_quarterly.csv`
- **Records:** 16 (only recent snapshot)
- **Stocks:** LIMITED
- **Columns:** quarter_end, ticker, promoter_hold_pct, promoter_pledge_frac, fii_dii_delta_pp
- **Missing:**
  - FII% (Foreign Institutional Investors)
  - DII% (Domestic Institutional Investors)
  - Retail%
  - Historical quarterly data (2020-2022)
  - Coverage for all 205 stocks

### ✅ 4. Sector Mapping
- **File:** `4_sector_mapping.csv`
- **Stocks:** 9 (sample)
- **Columns:** ticker, sector_id, sector_group
- **Status:** Available but needs expansion to 205 stocks

### ❌ 5. Sector Indices (for Sector Momentum)
- **Status:** NOT AVAILABLE
- **Required:**
  - Nifty Bank Index (weekly/monthly OHLCV)
  - Nifty IT Index
  - Nifty Auto Index
  - Nifty Pharma Index
  - Nifty Metal Index
  - Nifty FMCG Index
  - etc. for all sectors

### ❌ 6. Market Index Data (for Relative Strength)
- **Status:** NOT AVAILABLE
- **Required:**
  - Nifty 50 (daily OHLCV)
  - Nifty 500 (daily OHLCV)
  - Sector indices for RS calculation

---

## 🎯 What Your Developer Needs to Source

### Priority 1: Fundamentals (Quarterly)
**Data Required for 205 stocks (2020-2022):**
- EPS (Earnings Per Share)
- P/E Ratio
- P/B Ratio
- ROE (Return on Equity) - 3Y average
- ROCE (Return on Capital Employed) - 3Y average
- Debt/Equity Ratio
- Dividend Yield
- Sales CAGR (3Y)
- Operating Profit Margin

**Sources:**
1. **NSE India** (Free): https://www.nseindia.com/
   - Corporate announcements
   - Financial results (quarterly)
   
2. **BSE India** (Free): https://www.bseindia.com/
   - Corporate announcements
   
3. **Screener.in** (Free with limits): https://www.screener.in/
   - Quarterly financials
   - Key ratios
   
4. **Money Control** (Free): https://www.moneycontrol.com/
   - Quarterly results
   
5. **APIs (Paid):**
   - AlphaVantage (Fundamental data)
   - Financial Modeling Prep
   - Intrinio

### Priority 2: Ownership (Quarterly)
**Data Required for 205 stocks (2020-2022):**
- Promoter Holding %
- Promoter Pledge %
- FII Holding %
- DII Holding %
- Retail/Public Holding %

**Sources:**
1. **NSE India** (Free): Shareholding pattern reports
2. **BSE India** (Free): Shareholding data
3. **Screener.in** (Free): Shareholding history
4. **SEBI NSDL** (Free): https://www.nsdl.co.in/

### Priority 3: Sector Indices
**Data Required:**
- Nifty sectoral indices (Bank, IT, Auto, Pharma, Metal, FMCG, etc.)
- Daily/Weekly OHLCV (2020-2022)

**Sources:**
1. **NSE India** (Free): https://www.nseindia.com/market-data/live-equity-market
2. **Investing.com** (Free): Historical data download
3. **Yahoo Finance** (Free): Using yfinance library
   ```python
   import yfinance as yf
   # Example: Nifty Bank
   data = yf.download("^NSEBANK", start="2020-01-01", end="2022-12-31")
   ```

### Priority 4: Market Indices
**Data Required:**
- Nifty 50 daily OHLCV (2020-2022)
- Nifty 500 daily OHLCV

**Sources:**
1. **NSE India** (Free)
2. **Yahoo Finance** (Free)
   ```python
   # Nifty 50
   nifty50 = yf.download("^NSEI", start="2020-01-01", end="2022-12-31")
   ```

---

## 📋 Data Format Requirements

### Fundamentals CSV Format:
```csv
ticker,date,eps,pe_ratio,pb_ratio,roe_3y,roce_3y,debt_equity,dividend_yield,sales_cagr_3y,opm
RELIANCE,2020-03-31,62.5,15.2,2.1,12.5,11.8,0.45,0.35,10.2,8.5
RELIANCE,2020-06-30,58.3,16.1,2.0,12.3,11.5,0.48,0.32,9.8,8.2
...
```

### Ownership CSV Format:
```csv
ticker,date,promoter_pct,promoter_pledge_pct,fii_pct,dii_pct,retail_pct
RELIANCE,2020-03-31,50.25,0.0,22.35,18.40,9.00
RELIANCE,2020-06-30,50.30,0.0,23.10,17.80,8.80
...
```

### Sector Indices CSV Format:
```csv
index_name,date,open,high,low,close,volume
NIFTY_BANK,2020-01-01,31500,31800,31400,31750,125000000
NIFTY_IT,2020-01-01,18200,18350,18150,18300,85000000
...
```

---

## 🔧 How to Use This Data

Once you have the complete dataset:

1. **Calculate Technical Indicators** (from price data)
   - RSI, DMAs, ATR, breakouts → Use existing code

2. **Calculate Fundamentals Pillar** (from fundamentals data)
   - Quality score based on ROE, ROCE, margins
   - Growth score based on sales/EPS CAGR
   - Value score based on P/E, P/B ratios

3. **Calculate Ownership Pillar** (from ownership data)
   - Promoter strength
   - Institutional interest
   - Stability metrics

4. **Calculate Relative Strength** (price + index data)
   - Stock vs Nifty 50
   - Stock vs Sector Index

5. **Calculate Sector Momentum** (sector indices)
   - Sector trend strength
   - Sector vs Market

6. **Combine into GreyOak Score**
   - Weight all pillars
   - Apply risk penalties
   - Generate 0-100 score

---

## 🚀 Next Steps

1. **Download this dataset folder to local**
2. **Source missing data** using above sources
3. **Run GreyOak Score calculation** with complete data
4. **Backtest with real scores**

Questions? Check `/app/backend/docs/` for GreyOak Score Engine documentation.
