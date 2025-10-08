# Data Limitations - Yahoo Finance (yfinance)

**Phase 1 Data Source**: Yahoo Finance via `yfinance` Python library  
**Date**: 2025-10-08  
**Version**: yfinance 0.2.32

---

## ✅ What yfinance PROVIDES

### Price Data (Excellent)
- ✅ **OHLCV**: Open, High, Low, Close, Volume (daily)
- ✅ **Historical data**: Up to several years
- ✅ **Adjusted prices**: Splits, bonuses, dividends accounted for
- ✅ **Coverage**: All NSE/BSE stocks with .NS suffix
- ✅ **Reliability**: Good for technical analysis

### Basic Fundamentals (Partial)
- ✅ **PE Ratio**: `info['trailingPE']`
- ✅ **ROE**: `info['returnOnEquity']`
- ✅ **ROA**: `info['returnOnAssets']`
- ✅ **EV/EBITDA**: `info['enterpriseToEbitda']`
- ✅ **Profit Margins**: `info['profitMargins']`
- ✅ **Market Cap**: `info['marketCap']`

### Ownership (Very Limited)
- ⚠️ **Major Holders**: Some institutional data
- ⚠️ **Promoter Holdings**: Approximate (not always accurate)

---

## ❌ What yfinance DOES NOT PROVIDE

### Critical Missing Data

#### 1. **Promoter Pledge Data** ❌
**Spec Requirement**: `promoter_pledge_frac` (0-1)  
**yfinance Status**: **NOT AVAILABLE**  
**Impact**:
- Cannot test O pillar pledge penalty curve (Section 5.4)
- Cannot trigger PledgeCap guardrail (Section 7.5)
- RP pledge bins won't activate (Section 7.1)

**Workaround**: Set to `0.0` for all stocks in Phase 1

**Future Solution**: 
- Use Trendlyne API (enterprise)
- NSE/BSE regulatory filings
- Screener.in data

---

#### 2. **FII/DII Quarterly Changes** ❌
**Spec Requirement**: `fii_dii_delta_pp` (percentage point change)  
**yfinance Status**: **NOT AVAILABLE**  
**Impact**:
- O pillar will be incomplete (missing 40% weight component)
- Institutional flow signals won't work

**Workaround**: Set to `0.0` for all stocks in Phase 1

**Future Solution**: 
- Trendlyne API
- NSE bulk deals data
- SEBI filings

---

#### 3. **Banking Sector Metrics** ❌
**Spec Requirement** (Section 5.1 - Banking F Pillar):
- `gnpa_pct`: Gross Non-Performing Assets %
- `pcr_pct`: Provision Coverage Ratio %
- `nim_3y`: Net Interest Margin (3-year average)

**yfinance Status**: **NOT AVAILABLE**  
**Impact**:
- Banking F pillar cannot be calculated correctly
- Banks (HDFCBANK.NS, ICICIBANK.NS, SBIN.NS) scores will be inaccurate

**Workaround**: Set to `NaN` in Phase 1 (will test imputation logic)

**Future Solution**: 
- RBI regulatory data
- Annual reports (via web scraping)
- Trendlyne/Screener.in APIs

---

#### 4. **Historical Financial Metrics for CAGR** ⚠️
**Spec Requirement**:
- `eps_cagr_3y`: 3-year EPS CAGR
- `sales_cagr_3y`: 3-year Sales CAGR
- `opm_stdev_12q`: Operating Profit Margin stdev over 12 quarters

**yfinance Status**: **PARTIAL** (some historical data via `stock.financials`, but incomplete)  
**Impact**:
- F pillar will be incomplete
- Quality pillar (OPM stability) cannot be calculated

**Workaround**: Use available ROE, PE, margins from `info` dict

**Future Solution**: 
- Quarterly financial statements (NSE/BSE)
- Calculate CAGR from historical data
- Trendlyne API

---

#### 5. **ROCE (Return on Capital Employed)** ❌
**Spec Requirement**: `roce_3y` (3-year average)  
**yfinance Status**: **NOT AVAILABLE**  
**Impact**:
- Q pillar will be incomplete (missing 65% weight component)

**Workaround**: Set to `NaN` (will test imputation)

**Future Solution**: 
- Calculate from balance sheet data
- Trendlyne/Screener.in APIs

---

#### 6. **Event Data (Earnings Calendar)** ⚠️
**Spec Requirement** (Section 3.2.3):
- Upcoming earnings/board meeting dates
- RP penalty if within ±2 days

**yfinance Status**: Limited (`stock.calendar` may have earnings dates)  
**Impact**:
- Event window RP penalty won't trigger

**Workaround**: Skip event penalty in Phase 1

**Future Solution**: 
- NSE announcements API
- Trendlyne events feed

---

#### 7. **Governance Flags** ❌
**Spec Requirement** (Section 7.1):
- Auditor qualified opinion
- Board resignation

**yfinance Status**: **NOT AVAILABLE**  
**Impact**:
- Governance RP penalties won't trigger

**Workaround**: Set to `False` for all stocks

**Future Solution**: 
- NSE corporate actions
- Annual report analysis
- Media monitoring

---

## 📊 Data Quality Comparison

| Data Type | yfinance Quality | Production Requirement |
|-----------|------------------|------------------------|
| **OHLCV Price Data** | ⭐⭐⭐⭐⭐ Excellent | NSE/BSE feeds |
| **Technical Indicators** | ⭐⭐⭐⭐⭐ (computed) | Same |
| **Basic Fundamentals** | ⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Trendlyne |
| **Promoter Pledge** | ❌ None | ⭐⭐⭐⭐⭐ Trendlyne/NSE |
| **FII/DII Flows** | ❌ None | ⭐⭐⭐⭐⭐ Trendlyne/NSE |
| **Banking Metrics** | ❌ None | ⭐⭐⭐⭐ RBI/Annual Reports |
| **CAGR Metrics** | ⭐⭐ Partial | ⭐⭐⭐⭐⭐ Quarterly Data |
| **Event Calendar** | ⭐⭐ Limited | ⭐⭐⭐⭐ NSE Announcements |
| **Governance** | ❌ None | ⭐⭐⭐ Annual Reports |

---

## 🧪 Testing Impact

### What CAN Be Tested with yfinance Data

✅ **Technical Pillar (T)**: Fully testable
- DMA, RSI, Breakout, Volume Surprise all work
- Real volatility data for testing

✅ **Sector Normalization**: Fully testable
- Small sectors naturally occur (n ≤ 4)
- Z-scores, ECDF fallback all work

✅ **Data Hygiene**: Fully testable
- Real missing data (NaN) for imputation
- Winsorization on real distributions

✅ **Relative Strength (R)**: Fully testable
- Real returns vs sector/market
- Risk-adjusted alpha calculations

✅ **Volatility RP Penalty**: Testable
- Real sigma20 data

✅ **Liquidity RP Penalty**: Testable
- Real volume data for MTV calculation

### What CANNOT Be Tested with yfinance Data

❌ **Ownership Pillar (O)**: Partially broken
- Promoter holding approximate
- Pledge penalty curve untested (all 0.0)
- FII/DII component missing (40% weight)

❌ **Fundamentals Pillar (F)**: Incomplete
- Banking stocks broken (no GNPA/PCR/NIM)
- CAGR metrics missing
- Only ROE and PE available

❌ **Quality Pillar (Q)**: Incomplete
- ROCE missing (65% weight)
- OPM stability untestable

❌ **PledgeCap Guardrail**: Untestable (all pledge = 0.0)

❌ **Event Window RP**: Untestable (no calendar data)

❌ **Governance RP**: Untestable (no flags)

---

## 🔄 Migration Path to Production Data

### Phase 1 (Current): yfinance
- ✅ Build core engine
- ✅ Test technical analysis
- ✅ Test data hygiene
- ✅ Test normalization
- ⚠️ Accept incomplete F, O, Q pillars

### Phase 2 (Next): Trendlyne API
- ✅ Add promoter pledge data
- ✅ Add FII/DII flows
- ✅ Add CAGR metrics (EPS, Sales, OPM)
- ✅ Complete ownership pillar
- ✅ Test PledgeCap guardrail

### Phase 3 (Production): Multiple Sources
- ✅ NSE/BSE official feeds (prices)
- ✅ Trendlyne API (fundamentals, ownership)
- ✅ RBI data (banking metrics)
- ✅ NSE announcements (events, governance)
- ✅ Complete all pillars and guardrails

---

## 📝 Developer Notes

### Using yfinance Data in Tests

```python
# Example: Load prices.csv
prices = pd.read_csv("data/prices.csv")

# Expect NaN values (test imputation)
assert prices["ret_126d"].isna().any()  # First 126 days will be NaN

# Banking fundamentals will be NaN
fundamentals = pd.read_csv("data/fundamentals.csv")
banks = fundamentals[fundamentals["ticker"].isin(["HDFCBANK.NS", "ICICIBANK.NS"])]
assert banks["gnpa_pct"].isna().all()  # All banks have NaN for GNPA

# Pledge always 0.0
ownership = pd.read_csv("data/ownership.csv")
assert (ownership["promoter_pledge_frac"] == 0.0).all()
```

### Configuration Adjustments for Phase 1

Since pledge data is missing, consider:
1. **Test with pledge = 0.0**: PledgeCap won't trigger
2. **Document in test reports**: "PledgeCap guardrail not tested in Phase 1"
3. **Use RELIANCE golden test**: May need adjusted expectations for O pillar

---

## 🎯 Acceptance Criteria for Phase 1

### What Must Work
- [x] Price data loading (OHLCV)
- [x] Technical indicator calculations (RSI, ATR, MACD)
- [x] Data hygiene (winsorization, imputation)
- [x] Sector normalization (z-scores, ECDF)
- [x] T pillar (Technicals) - full functionality
- [x] R pillar (Relative Strength) - full functionality
- [x] Liquidity RP penalty
- [x] Volatility RP penalty
- [x] SectorBear guardrail

### What Will Be Partial/Mocked
- [ ] F pillar (Fundamentals) - incomplete due to missing CAGR, ROCE
- [ ] O pillar (Ownership) - incomplete due to missing pledge, FII/DII
- [ ] Q pillar (Quality) - incomplete due to missing ROCE, OPM stdev
- [ ] PledgeCap guardrail - untestable (all pledge = 0.0)
- [ ] Event window RP - untestable (no calendar)
- [ ] Governance RP - untestable (no flags)

### Success Definition
**Phase 1 is successful if**:
1. Core engine works end-to-end
2. T and R pillars calculate correctly
3. Data hygiene and normalization proven
4. Framework ready for better data in Phase 2

**Phase 1 is NOT about**:
- Complete pillar accuracy
- Testing all guardrails
- Production-ready scores

---

## 🔗 Data Source References

### yfinance
- GitHub: https://github.com/ranaroussi/yfinance
- Docs: https://pypi.org/project/yfinance/
- License: Apache 2.0

### Future Sources (Phase 2+)
- **Trendlyne API**: https://trendlyne.com/api/
- **NSE API**: https://www.nseindia.com/api
- **BSE API**: https://www.bseindia.com/
- **RBI Database**: https://dbie.rbi.org.in/

---

*Last Updated: 2025-10-08*  
*Status: Phase 1 - Development with yfinance*
