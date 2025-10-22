# Complete GreyOak Dataset - Offline Ready

## ✅ Dataset Status: COMPLETE & VALIDATED

All required data for 3-year GreyOak Score computation (2020-2022) is now available for **offline, local testing** without any API dependencies.

---

## 📦 Complete File List

### Core Data Files

| File | Size | Records | Description | Data Quality |
|------|------|---------|-------------|--------------|
| **HISTORICAL_DATA_3_YEARS_205_STOCKS.csv** | 6.9 MB | 158,716 | Daily OHLCV for 205 stocks | ✅ Real NSE data |
| **sector_indices_2020_2022.csv** | 0.7 MB | 7,480 | 10 sector indices (daily) | ⚠️ Synthetic (from constituents) |
| **fundamentals_quarterly_2020_2022.csv** | 0.6 MB | 2,460 | Quarterly financials (12 quarters) | ⚠️ Synthetic (realistic ranges) |
| **ownership_quarterly_2020_2022.csv** | 0.2 MB | 2,460 | Quarterly shareholding patterns | ⚠️ Synthetic (realistic patterns) |
| **stable_sector_map_2020_2022.csv** | 10 KB | 205 | Stock→Sector mapping | ✅ Real mapping |
| **trading_calendar_2020_2022.csv** | 33 KB | 1,096 | Trading days calendar | ✅ Real NSE calendar |
| **data_quality_flags_2020_2022.csv** | 10.6 MB | 158,716 | Quality validation flags | ✅ Generated |

**Total Dataset Size:** ~19 MB (7 files)

---

## 📊 Data Coverage

### ✅ Complete Coverage

- **Stocks:** 205 NSE stocks
- **Period:** January 1, 2020 → December 30, 2022 (3 years)
- **Trading Days:** 748 days
- **Quarters:** 12 quarters
- **Sector Indices:** 10 indices (Nifty 50, Bank, IT, Auto, Pharma, Metal, FMCG, Energy, PSU Banks, Diversified)

### 📈 By Pillar

| Pillar | Data Required | Status | Coverage |
|--------|---------------|--------|----------|
| **Technicals** | Daily OHLCV + indicators | ✅ Complete | 100% (Real) |
| **Relative Strength** | Stock vs Index/Sector | ✅ Complete | 100% (Synthetic indices) |
| **Fundamentals** | Quarterly ratios | ✅ Complete | 100% (Synthetic) |
| **Ownership** | Quarterly holdings | ✅ Complete | 100% (Synthetic) |
| **Quality** | 3Y stability metrics | ✅ Complete | 100% (Synthetic) |
| **Sector Momentum** | Sector performance | ✅ Complete | 100% (Synthetic indices) |

---

## ⚠️ Data Quality Notes

### Real Data (Production Quality)
- ✅ **Price Data (OHLCV):** Actual NSE historical data via nsepython
- ✅ **Sector Mapping:** Real sector classifications
- ✅ **Trading Calendar:** Real NSE trading days

### Synthetic Data (Testing Proxy)
- ⚠️ **Sector Indices:** Calculated from constituent stock averages (deterministic, realistic)
- ⚠️ **Fundamentals:** Generated with realistic ranges for Indian equities (deterministic per stock)
- ⚠️ **Ownership:** Generated with typical NSE patterns (deterministic per stock)

**Why Synthetic?**
- Free sources (Investing.com, NSE) require manual download or block automation
- yfinance doesn't reliably cover NSE indices/fundamentals
- Paid APIs (Financial Modeling Prep) cost $29-99/mo
- **Synthetic data enables immediate testing** while maintaining realistic distributions

**For Production:**
Replace synthetic data with:
1. **Indices:** Manual download from Investing.com or NSE
2. **Fundamentals:** Scrape Screener.in or use paid API
3. **Ownership:** Parse NSE shareholding PDFs

---

## 🚀 Quick Start

### 1. Load All Data

```python
import pandas as pd

# Price data (Real NSE data)
df_prices = pd.read_csv('HISTORICAL_DATA_3_YEARS_205_STOCKS.csv')
df_prices['Date'] = pd.to_datetime(df_prices['Date'])

# Sector indices (Synthetic)
df_indices = pd.read_csv('sector_indices_2020_2022.csv')
df_indices['Date'] = pd.to_datetime(df_indices['Date'])

# Fundamentals (Synthetic)
df_fund = pd.read_csv('fundamentals_quarterly_2020_2022.csv')
df_fund['quarter_end'] = pd.to_datetime(df_fund['quarter_end'])

# Ownership (Synthetic)
df_own = pd.read_csv('ownership_quarterly_2020_2022.csv')
df_own['quarter_end'] = pd.to_datetime(df_own['quarter_end'])

# Sector mapping
df_sectors = pd.read_csv('stable_sector_map_2020_2022.csv')

# Trading calendar
df_calendar = pd.read_csv('trading_calendar_2020_2022.csv')
df_calendar['Date'] = pd.to_datetime(df_calendar['Date'])
```

### 2. Calculate GreyOak Score (Example)

```python
def get_greyoak_score(ticker, date):
    """Calculate GreyOak Score for a stock on a specific date"""
    
    # 1. Get price history up to date
    price_hist = df_prices[
        (df_prices['Ticker'] == ticker) & 
        (df_prices['Date'] <= date)
    ].sort_values('Date')
    
    if len(price_hist) < 200:
        return None  # Insufficient history
    
    # 2. Calculate technical indicators
    close = price_hist['Close']
    
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
    
    # Current values
    current = price_hist.iloc[-1]
    current_rsi = rsi.iloc[-1]
    current_dma20 = dma20.iloc[-1]
    
    # 3. Get fundamentals (latest quarter before date)
    fund = df_fund[
        (df_fund['ticker'] == ticker) & 
        (df_fund['quarter_end'] <= date)
    ]
    
    if len(fund) == 0:
        return None
    
    latest_fund = fund.iloc[-1]
    
    # 4. Get ownership
    own = df_own[
        (df_own['ticker'] == ticker) & 
        (df_own['quarter_end'] <= date)
    ]
    
    if len(own) == 0:
        return None
    
    latest_own = own.iloc[-1]
    
    # 5. Calculate pillar scores (simplified example)
    
    # Technical pillar (0-100)
    tech_score = 50 + (current_rsi - 50)  # Simplified
    
    # Fundamental pillar (0-100)
    fund_score = (
        latest_fund['roe_3y'] * 2 +  # ROE weight
        latest_fund['roce_3y'] * 1.5 +  # ROCE weight
        (50 - latest_fund['debt_equity'] * 10)  # Penalize debt
    )
    fund_score = max(0, min(100, fund_score))
    
    # Ownership pillar (0-100)
    own_score = (
        latest_own['promoter_pct'] * 0.5 +  # Promoter strength
        (100 - latest_own['promoter_pledge_pct']) * 0.3 +  # Low pledge good
        (latest_own['fii_pct'] + latest_own['dii_pct']) * 0.2  # Institutional
    )
    own_score = max(0, min(100, own_score))
    
    # 6. Combine pillars (equal weight example)
    greyoak_score = (tech_score + fund_score + own_score) / 3
    
    return {
        'ticker': ticker,
        'date': date,
        'score': round(greyoak_score, 1),
        'tech_score': round(tech_score, 1),
        'fund_score': round(fund_score, 1),
        'own_score': round(own_score, 1),
        'current_price': current['Close'],
        'rsi': round(current_rsi, 1)
    }


# Test
result = get_greyoak_score('RELIANCE', '2022-06-30')
print(result)
```

### 3. Backtest Example

```python
# Get all stocks
stocks = df_prices['Ticker'].unique()

# Test date
test_date = pd.to_datetime('2022-06-30')

# Calculate scores for all stocks
scores = []
for ticker in stocks:
    result = get_greyoak_score(ticker, test_date)
    if result:
        scores.append(result)

df_scores = pd.DataFrame(scores)

# Filter high-quality stocks (score >= 70)
high_quality = df_scores[df_scores['score'] >= 70]
print(f"High-quality stocks (score ≥ 70): {len(high_quality)}")
print(high_quality[['ticker', 'score', 'current_price']].to_string())
```

---

## 📋 Data Schema

### 1. Price Data

```csv
Ticker,Date,Open,High,Low,Close
RELIANCE,2020-01-01,1535.0,1544.0,1520.0,1537.8
```

**Columns:**
- `Ticker`: Stock symbol
- `Date`: Trading date (YYYY-MM-DD)
- `Open, High, Low, Close`: Prices (INR)

### 2. Sector Indices

```csv
Index,Date,Open,High,Low,Close,Volume
NIFTY_50,2020-01-01,12100.0,12150.0,12050.0,12120.0,0
```

**Indices Available:**
- NIFTY_50, NIFTY_BANK, NIFTY_IT, NIFTY_AUTO
- NIFTY_PHARMA, NIFTY_METAL, NIFTY_FMCG, NIFTY_ENERGY
- NIFTY_PSU_BANKS, NIFTY_DIVERSIFIED

### 3. Fundamentals

```csv
ticker,quarter_end,pe_ratio,pb_ratio,roe_3y,roce_3y,debt_equity,eps,...
RELIANCE,2020-03-31,18.5,2.3,12.8,14.2,0.52,68.3,...
```

**Key Columns:**
- `pe_ratio, pb_ratio`: Valuation ratios
- `roe_3y, roce_3y, roa_3y`: Profitability (%)
- `debt_equity`: Leverage ratio
- `eps_cagr_3y, sales_cagr_3y`: Growth (%)
- `opm`: Operating margin (%)
- `market_cap_cr`: Market cap (crores)

### 4. Ownership

```csv
ticker,quarter_end,promoter_pct,fii_pct,dii_pct,retail_pct,...
RELIANCE,2020-03-31,50.5,22.3,18.2,9.0,...
```

**Columns:**
- `promoter_pct`: Promoter shareholding (%)
- `promoter_pledge_pct`: Pledged shares (%)
- `fii_pct`: Foreign institutional investors (%)
- `dii_pct`: Domestic institutional investors (%)
- `retail_pct`: Retail/public (%)
- `free_float_pct`: Free float (%)

---

## 🔄 Updating with Real Data

### Replace Fundamentals

```python
# Your real fundamentals (from Screener.in or API)
df_real_fund = pd.read_csv('real_fundamentals_from_screener.csv')

# Merge with existing structure
df_real_fund = df_real_fund[[
    'ticker', 'quarter_end', 'pe_ratio', 'pb_ratio', 
    'roe_3y', 'roce_3y', 'debt_equity', 'eps'
]]

# Save
df_real_fund.to_csv('fundamentals_quarterly_2020_2022.csv', index=False)
```

### Replace Ownership

```python
# Your real ownership (from NSE PDFs)
df_real_own = pd.read_csv('real_ownership_from_nse.csv')

# Save
df_real_own.to_csv('ownership_quarterly_2020_2022.csv', index=False)
```

### Replace Indices

```python
# Downloaded from Investing.com
df_real_indices = pd.read_csv('nifty_indices_downloaded.csv')

# Save
df_real_indices.to_csv('sector_indices_2020_2022.csv', index=False)
```

---

## ✅ Validation

Run validation script to confirm all data is properly formatted:

```bash
python3 validate_complete_dataset.py
```

Expected output:
```
✅ Passed: 7/7
🎉 ALL VALIDATIONS PASSED!
```

---

## 📊 Coverage Summary

### Complete (100%)
- ✅ 205 stocks with 3 years daily price data
- ✅ 10 sector indices (synthetic but functional)
- ✅ 12 quarters of fundamentals per stock
- ✅ 12 quarters of ownership per stock
- ✅ Sector mapping for all stocks
- ✅ Trading calendar with 748 trading days

### Data Quality
- ✅ **Zero quality issues** in price data (0/158,716 records)
- ✅ All OHLC data validated (no invalid prices)
- ✅ Complete date coverage (no gaps)

---

## 🎯 Next Steps for Production

1. **Replace synthetic indices** (15-30 min manual download)
   - Visit: https://in.investing.com/indices/
   - Download each sector index CSV

2. **Replace synthetic fundamentals** (1-2 weeks)
   - Option A: Scrape Screener.in
   - Option B: Pay $29/mo for Financial Modeling Prep

3. **Replace synthetic ownership** (1-2 weeks)
   - Parse NSE shareholding PDFs
   - Or scrape Screener.in

4. **Validate scores** on real data
   - Backtest with real fundamentals
   - Compare signals with market reality

---

## 📞 Support

- **Validation Issues:** Run `validate_complete_dataset.py` for detailed errors
- **Data Format Questions:** See schema section above
- **GreyOak Score Calculation:** See Quick Start examples

---

## ✅ Bottom Line

**You now have a COMPLETE, OFFLINE-READY dataset for GreyOak Score testing!**

- 📊 All 6 pillars covered
- 💾 19 MB total (fits in GitHub easily)
- 🚀 No API dependencies
- ✅ Validated and ready to use

The synthetic data (indices/fundamentals/ownership) provides realistic distributions for **testing the GreyOak Score framework**. Once the framework is validated, replace with real data for production deployment.
