# Sector Indices Data Collection Status

## Task Overview
**Objective**: Download 9 Nifty sector indices historical data (2020-2022) from investing.com and consolidate into `sector_indices_2020_2022.csv`

**Date Started**: October 22, 2025  
**Status**: ⚠️ **AWAITING MANUAL DOWNLOAD**

---

## Files Created

### 1. Download Scripts
- **`download_sector_indices_simple.py`** ✅
  - Primary script for managing downloads
  - Shows download instructions
  - Checks download status
  - Combines downloaded files
  - Usage:
    ```bash
    python download_sector_indices_simple.py          # Show instructions
    python download_sector_indices_simple.py --status # Check status
    python download_sector_indices_simple.py --combine # Combine files
    ```

- **`download_sector_indices_investing.py`** ✅
  - Alternative script with manual download instructions
  - More detailed documentation

- **`download_investing_automated.py`** ✅
  - Experimental: Playwright-based automation (requires additional setup)
  - Not recommended for initial use

### 2. Documentation
- **`SECTOR_INDICES_DOWNLOAD_GUIDE.md`** ✅
  - Complete step-by-step guide
  - Troubleshooting tips
  - Verification steps

### 3. Output Files
- **`sector_indices_2020_2022_template.csv`** ✅
  - Schema template for final output
  - Columns: Date, Sector, Open, High, Low, Close, Volume, Change_Pct

- **`sector_indices_2020_2022.csv`** ⏳ PENDING
  - Will be created after running `--combine`

---

## What You Need to Do

### Option A: Quick Start (Recommended)

1. **View URLs and Instructions**:
   ```bash
   cd /app/backend
   python download_sector_indices_simple.py
   ```

2. **Download Each File Manually**:
   - Open each URL in browser
   - Set date range: 01/01/2020 to 31/12/2022
   - Click Download
   - Save to `/app/backend/data/` with exact filename

3. **Combine All Files**:
   ```bash
   python download_sector_indices_simple.py --combine
   ```

### Option B: Detailed Guide

Follow the complete guide in `SECTOR_INDICES_DOWNLOAD_GUIDE.md`:
```bash
cat SECTOR_INDICES_DOWNLOAD_GUIDE.md
```

---

## 9 Sector Indices Required

| # | Sector Name | URL | Status | Filename |
|---|-------------|-----|--------|----------|
| 1 | Nifty Bank | [Link](https://in.investing.com/indices/bank-nifty-historical-data) | ⏳ Pending | `bank-nifty_2020_2022.csv` |
| 2 | Nifty IT | [Link](https://in.investing.com/indices/nifty-it-historical-data) | ⏳ Pending | `nifty-it_2020_2022.csv` |
| 3 | Nifty Auto | [Link](https://in.investing.com/indices/cnx-auto-historical-data) | ⏳ Pending | `cnx-auto_2020_2022.csv` |
| 4 | Nifty Pharma | [Link](https://in.investing.com/indices/cnx-pharma-historical-data) | ⏳ Pending | `cnx-pharma_2020_2022.csv` |
| 5 | Nifty FMCG | [Link](https://in.investing.com/indices/cnx-fmcg-historical-data) | ⏳ Pending | `cnx-fmcg_2020_2022.csv` |
| 6 | Nifty Metal | [Link](https://in.investing.com/indices/cnx-metal-historical-data) | ⏳ Pending | `cnx-metal_2020_2022.csv` |
| 7 | Nifty Realty | [Link](https://in.investing.com/indices/cnx-realty-historical-data) | ⏳ Pending | `cnx-realty_2020_2022.csv` |
| 8 | Nifty Energy | [Link](https://in.investing.com/indices/cnx-energy-historical-data) | ⏳ Pending | `cnx-energy_2020_2022.csv` |
| 9 | Nifty Media | [Link](https://in.investing.com/indices/cnx-media-historical-data) | ⏳ Pending | `cnx-media_2020_2022.csv` |

---

## Progress Tracking

### Check Your Progress
```bash
python download_sector_indices_simple.py --status
```

This will show:
- ✓ Files successfully downloaded
- ✗ Files still missing
- File sizes for downloaded files

---

## Expected Output

After combining all 9 files successfully:

**File**: `/app/backend/sector_indices_2020_2022.csv`

**Schema**:
```csv
Date,Sector,Open,High,Low,Close,Volume,Change_Pct
2020-01-01,Nifty Bank,31234.50,31456.20,31100.30,31367.80,42470000,0.45
2020-01-01,Nifty IT,18456.30,18567.80,18402.20,18512.40,32100000,0.32
...
```

**Expected Metrics**:
- **Rows**: ~6,750 (9 sectors × ~750 trading days)
- **Date Range**: 2020-01-01 to 2022-12-31
- **Sectors**: 9 unique sector names
- **File Size**: ~500 KB - 1 MB

---

## Why Manual Download?

1. **investing.com uses JavaScript** - Data is loaded dynamically
2. **No public API** - No direct data access
3. **Anti-scraping measures** - May block automated requests
4. **Rate limiting** - Automated downloads may be blocked
5. **Browser-based authentication** - Some features require cookies

**Manual download is the most reliable method** for this task.

---

## Next Steps After Completion

Once `sector_indices_2020_2022.csv` is created:

1. ✅ Validate data quality
2. ✅ Check for missing dates
3. ✅ Verify all 9 sectors are present
4. 🔄 Move to next data collection task:
   - Quarterly Fundamentals (2020-2022)
   - Quarterly Ownership (2020-2022)
   - Corporate Actions (2020-2022)

---

## Support & Troubleshooting

### Common Issues:

**Issue**: Can't find download button
- **Solution**: Scroll down on the page, it's usually below the data table

**Issue**: Date picker not working
- **Solution**: Click directly on the displayed date range text

**Issue**: Wrong file format
- **Solution**: Ensure you're downloading CSV, not Excel or other formats

**Issue**: File has different columns
- **Solution**: The combine script handles common variations. If it fails, check column names.

### Need Help?

1. Check `SECTOR_INDICES_DOWNLOAD_GUIDE.md` for detailed instructions
2. Run `--status` to see which files are missing
3. Verify filenames match exactly (case-sensitive!)
4. Ensure files are saved in `/app/backend/data/` directory

---

## Alternative Approaches (If Investing.com Doesn't Work)

1. **NSE India Official Website**:
   - https://www.nseindia.com/
   - More complex to navigate but official source

2. **Yahoo Finance**:
   - May have limited historical data for Indian indices
   - Requires different approach

3. **Google Finance**:
   - Historical data via Google Sheets
   - May require manual export

**Recommendation**: Stick with investing.com as it's the most straightforward option.

---

## Completion Checklist

- [ ] Downloaded all 9 CSV files to `/app/backend/data/`
- [ ] Verified file names match exactly
- [ ] Run `python download_sector_indices_simple.py --status` shows 9/9 files
- [ ] Run `python download_sector_indices_simple.py --combine`
- [ ] Verify `sector_indices_2020_2022.csv` is created
- [ ] Check data quality (date range, row count, no missing values)
- [ ] Update this document with completion status

---

**Last Updated**: October 22, 2025  
**Current Stage**: Awaiting manual downloads  
**Completion**: 0/9 files downloaded
