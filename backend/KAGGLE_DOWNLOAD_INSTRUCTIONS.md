# Kaggle Dataset Download Instructions

## Dataset Information
**Source**: [Stock Market Index Data India 1990-2022](https://www.kaggle.com/datasets/debashis74017/stock-market-index-data-india-1990-2022)  
**Size**: ~50 MB  
**Format**: CSV  
**Content**: Historical data for Indian stock market indices including Nifty sector indices

---

## Quick Start

### Option 1: Direct Web Download (Easiest)

1. **Go to Kaggle Dataset Page**:
   ```
   https://www.kaggle.com/datasets/debashis74017/stock-market-index-data-india-1990-2022
   ```

2. **Download the Dataset**:
   - Click the **"Download"** button (top right)
   - You may need to create a free Kaggle account if you don't have one
   - The file will download as a ZIP (~50 MB)

3. **Extract and Place the File**:
   ```bash
   # Extract the ZIP file
   unzip archive.zip
   
   # Copy the CSV to the processing directory
   cp *.csv /app/backend/data/kaggle_raw/
   ```

4. **Run the Processing Script**:
   ```bash
   cd /app/backend
   python process_kaggle_sector_indices.py
   ```

---

### Option 2: Using Kaggle API (Advanced)

If you have Kaggle API credentials set up:

1. **Setup Kaggle API** (one-time):
   ```bash
   # Install kaggle library (already done)
   pip install kaggle
   
   # Create Kaggle config directory
   mkdir -p ~/.kaggle
   
   # Download your API token from Kaggle:
   # Go to: https://www.kaggle.com/settings/account
   # Click "Create New API Token"
   # Save kaggle.json to ~/.kaggle/
   
   chmod 600 ~/.kaggle/kaggle.json
   ```

2. **Run the Script** (it will auto-download):
   ```bash
   cd /app/backend
   python process_kaggle_sector_indices.py
   ```

---

## What the Script Does

The `process_kaggle_sector_indices.py` script will:

1. ✅ Load the Kaggle dataset
2. ✅ Filter for 2020-2022 period
3. ✅ Extract these 9 sector indices:
   - Nifty Bank
   - Nifty IT
   - Nifty Auto
   - Nifty Pharma
   - Nifty FMCG
   - Nifty Metal
   - Nifty Realty
   - Nifty Energy
   - Nifty Media
4. ✅ Format to schema: `Index,Date,Open,High,Low,Close,Volume`
5. ✅ Save as: `/app/backend/sector_indices_2020_2022.csv`

---

## Expected Output

**File**: `/app/backend/sector_indices_2020_2022.csv`

**Schema**:
```csv
Index,Date,Open,High,Low,Close,Volume
Nifty Bank,2020-01-01,31234.50,31456.20,31100.30,31367.80,42470000
Nifty IT,2020-01-01,18456.30,18567.80,18402.20,18512.40,32100000
...
```

**Expected Metrics**:
- **Rows**: ~6,750 (9 indices × ~750 trading days)
- **Date Range**: 2020-01-01 to 2022-12-31
- **Indices**: 9 sector indices
- **File Size**: ~800 KB - 1.5 MB

---

## Troubleshooting

### Issue: "Dataset file not found"
**Solution**: 
- Ensure the CSV file is extracted to `/app/backend/data/kaggle_raw/`
- Check the filename matches what the script expects
- Run `ls -la /app/backend/data/kaggle_raw/` to verify

### Issue: "Kaggle requires authentication"
**Solution**: 
- You need a free Kaggle account to download datasets
- Sign up at: https://www.kaggle.com/account/login

### Issue: "Some sector indices missing from dataset"
**Solution**: 
- The script will report which indices are found
- It will still create the output file with available indices
- Check the console output for details

---

## Verification

After processing, verify the output:

```bash
# Check if file exists and size
ls -lh /app/backend/sector_indices_2020_2022.csv

# View first 20 rows
head -20 /app/backend/sector_indices_2020_2022.csv

# Count rows
wc -l /app/backend/sector_indices_2020_2022.csv

# Check data quality with pandas
python -c "
import pandas as pd
df = pd.read_csv('/app/backend/sector_indices_2020_2022.csv')
print(f'Total rows: {len(df):,}')
print(f'Date range: {df[\"Date\"].min()} to {df[\"Date\"].max()}')
print(f'Indices: {df[\"Index\"].nunique()}')
print(f'\nIndices found:')
print(df['Index'].value_counts())
"
```

---

## Next Steps

Once `sector_indices_2020_2022.csv` is created successfully:

✅ Sector Indices - COMPLETE  
⏭️ Move to: **Corporate Actions Data Collection**

---

## Time Estimate

- **Option 1** (Manual Download): ~10-15 minutes
  - 5 min: Kaggle account + download
  - 2 min: Extract and copy file
  - 3-8 min: Script processing

- **Option 2** (API): ~5-10 minutes
  - 3 min: One-time API setup
  - 2-7 min: Auto-download + processing

---

## Support

If you encounter any issues:
1. Check the script's console output for detailed error messages
2. Verify the Kaggle dataset URL is still active
3. Ensure you have enough disk space (~100 MB free)
4. Try manual download if API method fails
