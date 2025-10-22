# Corporate Actions Data Collection Plan (2020-2022)

## Overview
Collect corporate actions data for 205 stocks covering the period 2020-2022. This includes:
- Stock splits
- Bonus issues
- Dividends
- Rights issues
- Buybacks

---

## Required Schema

**Target File**: `/app/backend/corporate_actions_2020_2022.csv`

**Schema**:
```csv
Ticker,Date,Action_Type,Details,Ratio,Amount
RELIANCE,2020-06-15,Split,1:1,2.0,0
TCS,2020-09-30,Dividend,Interim,0,18.0
INFY,2021-03-25,Bonus,1:1,2.0,0
HDFCBANK,2021-06-10,Dividend,Final,0,6.5
```

**Column Definitions**:
- **Ticker**: Stock symbol (e.g., RELIANCE, TCS)
- **Date**: Action date (YYYY-MM-DD format)
- **Action_Type**: [Split, Bonus, Dividend, Rights, Buyback]
- **Details**: Additional context (e.g., "Interim", "Final", "1:1")
- **Ratio**: For splits/bonus (e.g., 2.0 for 1:1 split)
- **Amount**: For dividends in INR per share

---

## Data Sources

### Option 1: NSE India (Official - Recommended)
**Advantages**: 
- Official source
- Free and reliable
- Comprehensive data

**URL**: https://www.nseindia.com/companies-listing/corporate-filings-actions

**Process**:
1. Navigate to NSE Corporate Actions page
2. Filter by date range (2020-2022)
3. Filter by action type
4. Download CSV for each quarter
5. Combine all files

**Automation Potential**: Medium (requires handling NSE's anti-bot measures)

---

### Option 2: BSE India
**URL**: https://www.bseindia.com/corporates/corporate_act.aspx

**Process**: Similar to NSE, download quarterly data

---

### Option 3: MoneyControl
**URL**: https://www.moneycontrol.com/stocks/company_info/corporate_action.php

**Process**: 
- Search each stock individually
- Extract corporate actions for 2020-2022
- Compile into CSV

**Note**: More time-consuming, suitable for filling gaps

---

### Option 4: Kaggle / Pre-compiled Datasets
**Search**: "NSE corporate actions" or "Indian stock dividends"

**Advantages**: Pre-compiled, ready to use
**Disadvantages**: May not cover all 205 stocks or full date range

---

## Recommended Approach

### Phase 1: Automated Bulk Collection (NSE/BSE)

Create script to:
1. Download NSE corporate actions data by quarter
2. Filter for our 205 stocks
3. Categorize actions into our schema
4. Validate and combine

**Script**: `download_corporate_actions_nse.py`

---

### Phase 2: Kaggle/Pre-compiled Augmentation

If available:
1. Find pre-compiled corporate actions dataset
2. Filter and merge with NSE data
3. Fill any gaps

---

### Phase 3: Manual Gap-Filling (If Needed)

For missing stocks/actions:
1. Use MoneyControl for individual stock lookup
2. Verify critical actions manually
3. Add to dataset

---

## Implementation Steps

### Step 1: Create Download Script
```bash
# Create NSE corporate actions scraper
python download_corporate_actions_nse.py
```

**Features**:
- Download corporate actions from NSE
- Filter for 2020-2022
- Filter for 205 target stocks
- Format to required schema
- Handle pagination and anti-bot measures

---

### Step 2: Explore Kaggle Options
**Search Queries**:
- "NSE corporate actions India"
- "Indian stock dividends bonus splits"
- "BSE corporate events"

**Validate**:
- Check date coverage (must include 2020-2022)
- Check stock coverage (ideally includes Nifty stocks)
- Verify data quality

---

### Step 3: Validation
```python
# Validate corporate actions data
python validate_corporate_actions.py
```

**Checks**:
- Date range coverage (2020-2022)
- All 205 stocks represented (at least those with actions)
- Action types are valid
- No duplicate entries
- Data format correctness

---

## Data Quality Requirements

### Minimum Requirements:
- ✅ Date range: 2020-01-01 to 2022-12-31
- ✅ Coverage: At least major stocks (Nifty 50/100)
- ✅ Action types: Dividends (minimum), Splits & Bonus (if available)

### Ideal Coverage:
- ✅ All 205 stocks
- ✅ All action types
- ✅ Complete quarterly coverage
- ✅ Verified accuracy

---

## Expected Data Volume

**Estimate**:
- **Dividends**: Most companies pay 1-4 times/year → ~600-2,400 records
- **Splits**: Rare → ~10-30 records
- **Bonus**: Uncommon → ~20-50 records
- **Rights**: Occasional → ~15-40 records
- **Total Expected**: ~650-2,500 records

**Actual may vary** based on market conditions and company policies.

---

## NSE Corporate Actions Download Script Outline

```python
#!/usr/bin/env python3
"""
Download corporate actions from NSE for 205 stocks (2020-2022)
"""

import requests
import pandas as pd
from datetime import datetime, timedelta

# NSE Corporate Actions API
NSE_CA_URL = "https://www.nseindia.com/api/corporates-corporateActions"

def get_nse_corporate_actions(from_date, to_date, symbol=None):
    """
    Fetch corporate actions from NSE
    """
    # NSE requires headers to bypass bot detection
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    params = {
        'from': from_date,  # DD-MM-YYYY
        'to': to_date,
        'index': 'equities'
    }
    
    if symbol:
        params['symbol'] = symbol
    
    response = requests.get(NSE_CA_URL, params=params, headers=headers)
    return response.json()

def process_actions(data):
    """
    Process NSE response into our schema
    """
    # Transform NSE format to our format
    # NSE provides: symbol, company, series, faceVal, exDate, 
    #               purpose, recordDate, bcStartDate, bcEndDate
    pass

# Main execution
# Download quarterly data
# Combine and format
# Save to corporate_actions_2020_2022.csv
```

---

## Alternative: Screener.in Approach

**URL**: https://www.screener.in/

**Process**:
1. Export company list with corporate actions
2. Filter for 2020-2022
3. Format to our schema

**Advantage**: Screener aggregates from multiple sources

---

## Time Estimates

| Approach | Setup | Execution | Total |
|----------|-------|-----------|-------|
| NSE Automated | 30 min | 15 min | 45 min |
| Kaggle Dataset | 5 min | 10 min | 15 min |
| Manual MoneyControl | - | 3-5 hours | 3-5 hours |
| Hybrid (Kaggle + NSE) | 35 min | 25 min | 60 min |

**Recommended**: Start with Kaggle search, supplement with NSE automated download

---

## Next Steps

1. **Search Kaggle** for pre-compiled corporate actions datasets
2. **Create NSE download script** if no suitable dataset found
3. **Validate and format** data to required schema
4. **Save** as `corporate_actions_2020_2022.csv`

---

## Success Criteria

✅ File created: `corporate_actions_2020_2022.csv`  
✅ Date range: 2020-2022  
✅ Schema matches specification  
✅ Minimum: Dividend data for major stocks  
✅ Validated: No duplicates, correct formats  
✅ Documentation: Sources and methodology recorded  

---

## Notes

- **Priority**: Focus on dividends first (most common and impactful)
- **Splits/Bonus**: Critical for price adjustment, must be accurate
- **Rights/Buybacks**: Less common, lower priority
- **Verification**: Cross-check critical actions (large splits) with company announcements

---

## Support

Refer to:
- `download_corporate_actions_nse.py` (to be created)
- NSE Corporate Actions API documentation
- Kaggle datasets for Indian markets
