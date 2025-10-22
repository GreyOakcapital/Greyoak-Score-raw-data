# Missing Data - Actionable Plan for 3-Year GreyOak Score

## Data Gaps (Categorized by Action)

### 🟢 CAN GENERATE from Existing Data

#### 1. **Adjusted Prices & Corporate Actions**
**Status:** ⚠️ Our current data is NOT split/bonus/dividend adjusted

**Action Required:**
```python
# Download adjusted data from yfinance (has split/dividend adjustments)
import yfinance as yf
for ticker in ['RELIANCE', 'TCS', ...]:
    df = yf.download(f"{ticker}.NS", start="2020-01-01", end="2022-12-31")
    # df['Adj Close'] is already adjusted
```

**Alternative:** Use NSE corporate action announcements
- Source: https://www.nseindia.com/companies-listing/corporate-filings-actions
- Parse PDF/HTML announcements
- Apply adjustments manually

**Priority:** HIGH (prevents false breakout signals)

---

#### 2. **Sector Indices History (2020-2022)**
**Status:** ❌ Missing

**Can Download NOW (15 minutes):**
```python
import yfinance as yf
import pandas as pd

indices = {
    '^NSEI': 'NIFTY_50',
    '^NSEBANK': 'NIFTY_BANK',
    '^CNXIT': 'NIFTY_IT',
    '^CNXAUTO': 'NIFTY_AUTO',
    '^CNXPHARMA': 'NIFTY_PHARMA',
    '^CNXMETAL': 'NIFTY_METAL',
    '^CNXFMCG': 'NIFTY_FMCG',
    '^CNXENERGY': 'NIFTY_ENERGY',
    '^CNXREALTY': 'NIFTY_REALTY',
    '^CNXINFRA': 'NIFTY_INFRA'
}

all_indices = []
for symbol, name in indices.items():
    df = yf.download(symbol, start="2020-01-01", end="2022-12-31", progress=False)
    df = df.reset_index()
    df['Index'] = name
    all_indices.append(df)

df_indices = pd.concat(all_indices)
df_indices.to_csv('sector_indices_2020_2022.csv', index=False)
```

**Priority:** HIGH (needed for SR+ and Sector Momentum)

---

#### 3. **Liquidity Filters (Turnover)**
**Status:** Can calculate from existing volume data

**Action:**
```python
# We have volume in our data
df['turnover'] = df['Close'] * df['Volume']
df['avg_turnover_20d'] = df.groupby('Ticker')['turnover'].rolling(20).mean()
df['avg_turnover_60d'] = df.groupby('Ticker')['turnover'].rolling(60).mean()

# Filter criteria
LIQUIDITY_THRESHOLD = 10_000_000  # Rs 1 crore minimum
df['is_liquid'] = df['avg_turnover_20d'] > LIQUIDITY_THRESHOLD
```

**Priority:** MEDIUM (risk management)

---

#### 4. **Calendar & Trading Days**
**Status:** Can extract from existing data

**Action:**
```python
# Extract all unique trading days from our data
trading_days = df['Date'].unique()
trading_calendar = pd.DataFrame({
    'date': trading_days,
    'is_trading_day': True
})

# Mark holidays (missing dates)
all_dates = pd.date_range(start='2020-01-01', end='2022-12-31', freq='D')
holidays = set(all_dates) - set(trading_days)
```

**Priority:** LOW (mostly for accuracy)

---

#### 5. **Data Quality Flags**
**Status:** Can generate from existing data

**Action:**
```python
df['has_missing_ohlc'] = df[['Open', 'High', 'Low', 'Close']].isna().any(axis=1)
df['zero_volume'] = df['Volume'] == 0
df['invalid_ohlc'] = (df['High'] < df['Low']) | (df['Close'] > df['High']) | (df['Close'] < df['Low'])
df['quality_flag'] = df['has_missing_ohlc'] | df['zero_volume'] | df['invalid_ohlc']
```

**Priority:** MEDIUM

---

### 🔴 NEEDS EXTERNAL SOURCING

#### 6. **Stable Sector Map (Historical with Effective Dates)**
**Status:** ❌ We only have current mapping

**What's Needed:**
```csv
ticker,sector_id,sector_group,effective_from,effective_to
RELIANCE,ENERGY,energy,2020-01-01,2022-12-31
TCS,IT_SERVICES,it,2020-01-01,2022-12-31
```

**Sources:**
1. **NSE Archives** - Historical index membership
2. **Bloomberg Terminal** (paid)
3. **Manual research** - NSE sector reclassification announcements

**Workaround:** Assume current sector mapping was valid for entire period (acceptable for 3 years)

**Priority:** LOW (sector changes rare over 3 years)

---

#### 7. **Quarterly Fundamentals - Complete Panel**
**Status:** ⚠️ Partial (1,020 records) - Need 205 stocks × 12 quarters = 2,460 records minimum

**What's Needed:**
```csv
ticker,quarter_end,eps,pe_ratio,pb_ratio,roe_3y,roce_3y,debt_equity,dividend_yield,sales_cagr_3y,opm,fcf_margin
RELIANCE,2020-03-31,62.5,15.2,2.1,12.5,11.8,0.45,0.35,10.2,8.5,12.3
RELIANCE,2020-06-30,58.3,16.1,2.0,12.3,11.5,0.48,0.32,9.8,8.2,11.8
...
```

**Sources (Ranked):**

**Option A: Paid APIs** (Fastest, Most Complete)
1. **Financial Modeling Prep** - $29-99/mo
   - API: `https://financialmodelingprep.com/api/v3/income-statement/{ticker}`
   - Covers NSE stocks
   - Quarterly financials back to 2015
   
2. **Alpha Vantage Premium** - $49/mo
   - Good fundamental data
   - Some NSE coverage

3. **Intrinio** - Custom pricing
   - Institutional-grade data

**Option B: Free (Manual/Scraping)**
1. **Screener.in** - https://www.screener.in/
   - Has quarterly data for most NSE stocks
   - Can scrape (check ToS)
   - Example: `https://www.screener.in/company/RELIANCE/consolidated/`

2. **NSE Corporate Filings**
   - https://www.nseindia.com/companies-listing/corporate-filings-financial-results
   - Official quarterly results
   - Requires PDF parsing

3. **BSE Corporate Filings**
   - https://www.bseindia.com/corporates/corporate_comp.aspx
   - Similar to NSE

**Scraping Example:**
```python
import requests
from bs4 import BeautifulSoup

# Screener.in scraper (example)
def scrape_screener(ticker):
    url = f'https://www.screener.in/company/{ticker}/consolidated/'
    # Parse quarterly results table
    # Extract EPS, P/E, ROE, etc.
```

**Priority:** CRITICAL (needed for Fundamentals, Quality, Ownership pillars)

---

#### 8. **Quarterly Ownership - Full History**
**Status:** ⚠️ Minimal (15 records) - Need 205 × 12 = 2,460 records

**What's Needed:**
```csv
ticker,quarter_end,promoter_pct,promoter_pledge_pct,fii_pct,dii_pct,retail_pct,free_float_pct
RELIANCE,2020-03-31,50.25,0.0,22.35,18.40,9.00,49.75
RELIANCE,2020-06-30,50.30,0.0,23.10,17.80,8.80,49.70
...
```

**Sources:**

**Best (Free):**
1. **NSE Shareholding Patterns**
   - https://www.nseindia.com/ → Company → Shareholding Pattern
   - Quarterly PDFs/Excel files
   - Can be parsed

2. **BSE Shareholding Data**
   - Similar to NSE

3. **Screener.in**
   - Has shareholding history
   - Can be scraped

**Parsing Example:**
```python
# NSE shareholding PDFs can be parsed
import pdfplumber

def parse_shareholding_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        # Extract promoter, FII, DII tables
        # Return structured data
```

**Priority:** HIGH (needed for Ownership pillar)

---

#### 9. **Corporate Actions Database**
**Status:** ❌ Missing

**What's Needed:**
```csv
ticker,date,action_type,ratio,details
RELIANCE,2020-09-28,SPLIT,1:1,Stock split 1 for 1
TCS,2020-06-10,DIVIDEND,5.0,Interim dividend Rs 5 per share
INFY,2021-01-13,BONUS,1:1,Bonus issue 1:1
```

**Sources:**
1. **NSE Corporate Actions**
   - https://www.nseindia.com/companies-listing/corporate-filings-actions
   - Historical announcements

2. **BSE Corporate Actions**
   - https://www.bseindia.com/corporates/corporate_act.aspx

3. **APIs:**
   - Financial Modeling Prep has corporate actions API
   - Alpha Vantage has some coverage

**Priority:** HIGH (prevents false signals)

---

#### 10. **Constituent & Survivorship Controls**
**Status:** ❌ Missing

**What's Needed:**
```csv
ticker,index,action,date,reason
ZOMATO,NIFTY_50,ADD,2021-12-24,Replaced WIPRO
PAYTM,NIFTY_50,ADD,2021-11-25,New listing
YESBANK,NIFTY_50,REMOVE,2020-03-01,Delisted
```

**Sources:**
1. **NSE Index Changes Archive**
2. **Manual research** - Index rebalancing announcements

**Priority:** MEDIUM (bias control)

---

#### 11. **Score Snapshot History (Label Truth)**
**Status:** ❌ Not saved historically

**What's Needed:**
- Daily/weekly score snapshots saved during 2020-2022
- Format: `ticker, date, score, band, pillar_scores`

**Action:**
- Once complete data is available, run scoring for each historical date
- Save snapshots for validation

**Priority:** MEDIUM (for validation, not calculation)

---

## 🎯 Recommended Action Plan

### Phase 1: Quick Wins (Can Do TODAY)
1. ✅ Download sector indices (15 min) - Use yfinance
2. ✅ Calculate liquidity metrics from existing volume
3. ✅ Generate data quality flags
4. ✅ Extract trading calendar from dates
5. ✅ Assume stable sector mapping for 3 years

**Result:** Enables Technical + Relative Strength + Sector Momentum pillars

---

### Phase 2: Critical External Data (1-2 weeks)
1. 🔴 **Get adjusted prices** OR corporate actions
   - Option A: Re-download from yfinance with Adj Close
   - Option B: Parse NSE corporate actions

2. 🔴 **Source quarterly fundamentals** (CRITICAL)
   - Option A: Pay $29/mo for Financial Modeling Prep
   - Option B: Scrape Screener.in (manual effort)
   - Target: 205 stocks × 12 quarters = 2,460 records

3. 🔴 **Source quarterly ownership** (HIGH)
   - Parse NSE shareholding PDFs
   - Or scrape Screener.in
   - Target: 205 stocks × 12 quarters = 2,460 records

**Result:** Enables all 6 pillars with defensible data

---

### Phase 3: Polish & Validation (1 week)
1. Add corporate actions database
2. Add index constituent changes
3. Validate scores on historical snapshots
4. Generate quality reports

**Result:** Production-ready, auditable GreyOak Score

---

## 💰 Cost-Benefit Analysis

### Free Approach (Manual/Scraping)
- **Cost:** $0
- **Time:** 2-4 weeks developer time
- **Quality:** Good (requires validation)
- **Legal:** Check ToS for each site

### Paid API Approach
- **Cost:** ~$50-100/mo for APIs
- **Time:** 3-5 days integration
- **Quality:** Excellent (institutional-grade)
- **Legal:** Clear licensing

**Recommendation:** Start with paid APIs for fundamentals/ownership (saves weeks), use free sources for everything else.

---

## 📊 Current Coverage Estimate

| Pillar | Data Required | Current Coverage | After Phase 1 | After Phase 2 |
|--------|---------------|------------------|----------------|---------------|
| **Technicals** | OHLCV, indicators | ✅ 100% | ✅ 100% | ✅ 100% |
| **Relative Strength** | Stock vs Index | ⚠️ 0% (no indices) | ✅ 100% | ✅ 100% |
| **Fundamentals** | Quarterly ratios | ⚠️ 5% (1,020/2,460) | ⚠️ 5% | ✅ 100% |
| **Ownership** | Quarterly holdings | ⚠️ 1% (15/2,460) | ⚠️ 1% | ✅ 100% |
| **Quality** | 3Y metrics | ⚠️ 5% | ⚠️ 5% | ✅ 100% |
| **Sector Momentum** | Sector indices | ⚠️ 0% | ✅ 100% | ✅ 100% |

---

## 🚀 Want to Start Phase 1 Now?

I can immediately create scripts to:
1. Download all sector indices (15 min)
2. Calculate liquidity metrics
3. Generate quality flags
4. Create trading calendar

Then move to Phase 2 sourcing strategy based on your budget/timeline preferences.

Ready to proceed?
