# Sector Indices Data Download Guide

## Overview
This guide helps you download historical data for 9 Nifty sector indices from investing.com for the period **January 1, 2020 to December 31, 2022**.

## Required Data
You need to download the following 9 sector indices:

1. **Nifty Bank** - Banking sector index
2. **Nifty IT** - Information Technology sector index
3. **Nifty Auto** - Automobile sector index
4. **Nifty Pharma** - Pharmaceutical sector index
5. **Nifty FMCG** - Fast Moving Consumer Goods sector index
6. **Nifty Metal** - Metal sector index
7. **Nifty Realty** - Real Estate sector index
8. **Nifty Energy** - Energy sector index
9. **Nifty Media** - Media sector index

## Method 1: Automated Script (Recommended)

### Step 1: View Download Instructions
```bash
cd /app/backend
python download_sector_indices_simple.py
```

### Step 2: Check Download Status
```bash
python download_sector_indices_simple.py --status
```

### Step 3: Combine Downloaded Files
After downloading all 9 CSV files:
```bash
python download_sector_indices_simple.py --combine
```

## Method 2: Manual Download

For each of the 9 sector indices:

### Download Steps:

1. **Open the URL** in your browser (see URLs below)
2. **Locate the date range selector** - It will show something like "22-09-2025 - 22-10-2025"
3. **Click on the date range** to open the date picker
4. **Set Start Date**: 01/01/2020
5. **Set End Date**: 31/12/2022
6. **Click "Apply"** or press Enter
7. **Wait** for the page to reload with historical data
8. **Click the "Download" button** (usually near the date range selector)
9. **Save the file** with the specific filename to `/app/backend/data/`

### URLs and Filenames:

| # | Sector | URL | Save As |
|---|--------|-----|---------|
| 1 | Nifty Bank | https://in.investing.com/indices/bank-nifty-historical-data | `bank-nifty_2020_2022.csv` |
| 2 | Nifty IT | https://in.investing.com/indices/nifty-it-historical-data | `nifty-it_2020_2022.csv` |
| 3 | Nifty Auto | https://in.investing.com/indices/cnx-auto-historical-data | `cnx-auto_2020_2022.csv` |
| 4 | Nifty Pharma | https://in.investing.com/indices/cnx-pharma-historical-data | `cnx-pharma_2020_2022.csv` |
| 5 | Nifty FMCG | https://in.investing.com/indices/cnx-fmcg-historical-data | `cnx-fmcg_2020_2022.csv` |
| 6 | Nifty Metal | https://in.investing.com/indices/cnx-metal-historical-data | `cnx-metal_2020_2022.csv` |
| 7 | Nifty Realty | https://in.investing.com/indices/cnx-realty-historical-data | `cnx-realty_2020_2022.csv` |
| 8 | Nifty Energy | https://in.investing.com/indices/cnx-energy-historical-data | `cnx-energy_2020_2022.csv` |
| 9 | Nifty Media | https://in.investing.com/indices/cnx-media-historical-data | `cnx-media_2020_2022.csv` |

## Expected Data Format

The downloaded CSV files from investing.com should have the following columns:
- **Date** - in DD-MM-YYYY format (e.g., 31-12-2022)
- **Price** - Closing price
- **Open** - Opening price
- **High** - Highest price of the day
- **Low** - Lowest price of the day
- **Vol.** - Trading volume (may have M/K suffixes)
- **Change %** - Percentage change

## Output File

After combining all 9 files, the script will create:
- **File**: `/app/backend/sector_indices_2020_2022.csv`
- **Format**: 
  ```csv
  Date,Sector,Open,High,Low,Close,Volume,Change_Pct
  2020-01-01,Nifty Bank,31234.50,31456.20,31100.30,31367.80,42470000,0.45
  ```

## Verification

After combining, verify the data:
```bash
# Check file size
ls -lh /app/backend/sector_indices_2020_2022.csv

# View first few rows
head -20 /app/backend/sector_indices_2020_2022.csv

# Count total rows
wc -l /app/backend/sector_indices_2020_2022.csv
```

Expected metrics:
- **Date Range**: 2020-01-01 to 2022-12-31 (approximately 750 trading days)
- **Total Rows**: ~6,750 rows (9 sectors × ~750 days)
- **File Size**: ~500 KB - 1 MB

## Troubleshooting

### Problem: Date picker not visible
- Try clicking directly on the displayed date range text
- Some browsers may require JavaScript to be enabled

### Problem: Download button not working
- Ensure the date range is set correctly
- Try refreshing the page and setting the date range again
- Check if the page requires you to scroll down to see the download button

### Problem: File format different
- Investing.com may update their CSV format
- The combine script handles common variations
- If errors occur, check the column names in your downloaded CSV

### Problem: Some URLs don't work
- Investing.com may have changed the URL structure
- Try searching for the index name on investing.com
- Navigate to "Historical Data" section
- Use the URL you find in the browser

## Next Steps

After successfully creating `sector_indices_2020_2022.csv`, you can:

1. **Validate the data**:
   ```bash
   python -c "import pandas as pd; df = pd.read_csv('/app/backend/sector_indices_2020_2022.csv'); print(df.info()); print(df.head())"
   ```

2. **Check for missing data**:
   ```bash
   python -c "import pandas as pd; df = pd.read_csv('/app/backend/sector_indices_2020_2022.csv'); print(df.isnull().sum())"
   ```

3. **Continue with other data collection tasks** (fundamentals, ownership, corporate actions)

## Support

If you encounter issues:
1. Check the `download_sector_indices_simple.py` script logs
2. Verify file names match exactly
3. Ensure all 9 files are downloaded before combining
4. Check that CSV files are not corrupted or empty

## Notes

- **Data Source**: investing.com - Free, public data
- **No API Key Required**: Manual download or web scraping
- **Update Frequency**: Historical data is static (2020-2022)
- **Data Quality**: Investing.com data is generally reliable but should be validated
- **Alternative Sources**: If investing.com doesn't work, consider NSE India official website
