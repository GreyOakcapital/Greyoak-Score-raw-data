"""Unit tests for data ingestion module."""

from pathlib import Path
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from greyoak_score.data.ingestion import (
    load_prices_csv,
    load_fundamentals_csv,
    load_ownership_csv,
    load_sector_map_csv,
    load_all_data,
    get_ticker_sector_map,
)


class TestLoadPricesCSV:
    """Test loading prices CSV data."""

    def test_load_prices_success(self, tmp_path):
        """Test successful loading of prices CSV."""
        # Create sample CSV data
        csv_data = """date,ticker,open,high,low,close,volume,dma20,dma50,dma200,rsi14,atr14,macd_line,macd_signal,hi20,lo20,ret_21d,ret_63d,ret_126d,sigma20,sigma60
2024-01-01,RELIANCE,2450,2500,2400,2480,1000000,2475,2470,2460,55.5,15.2,12.5,10.8,2520,2350,0.05,0.12,0.25,0.02,0.03
2024-01-02,RELIANCE,2480,2520,2460,2500,1200000,2478,2472,2462,58.2,16.1,13.2,11.2,2530,2360,0.06,0.13,0.26,0.021,0.031
"""
        
        csv_file = tmp_path / "prices.csv"
        csv_file.write_text(csv_data)
        
        df = load_prices_csv(csv_file)
        
        # Check basic properties
        assert len(df) == 2
        assert 'ticker' in df.columns
        assert 'close' in df.columns
        
        # Check data types
        assert df['date'].dtype == 'object'  # Will be date objects
        assert df['close'].dtype in ['float64', 'int64']

    def test_load_prices_missing_file(self, tmp_path):
        """Test error handling for missing prices file."""
        missing_file = tmp_path / "nonexistent.csv"
        
        with pytest.raises(FileNotFoundError, match="Prices CSV not found"):
            load_prices_csv(missing_file)

    @patch('greyoak_score.data.ingestion.add_missing_indicators')
    def test_load_prices_calls_indicator_calculation(self, mock_indicators, tmp_path):
        """Test that missing indicators are calculated."""
        # Create minimal CSV
        csv_data = """date,ticker,open,high,low,close,volume
2024-01-01,TEST,100,110,95,105,1000
"""
        
        csv_file = tmp_path / "prices.csv"
        csv_file.write_text(csv_data)
        
        # Mock the indicator function to return the same data
        mock_indicators.return_value = pd.read_csv(csv_file)
        mock_indicators.return_value['date'] = pd.to_datetime(mock_indicators.return_value['date']).dt.date
        
        df = load_prices_csv(csv_file)
        
        # Should call add_missing_indicators
        mock_indicators.assert_called_once()

    def test_load_prices_date_conversion(self, tmp_path):
        """Test that dates are properly converted."""
        csv_data = """date,ticker,open,high,low,close,volume
2024-01-01,TEST,100,105,95,100,1000
2024-01-02,TEST,100,105,95,100,1000
"""
        
        csv_file = tmp_path / "prices.csv"
        csv_file.write_text(csv_data)
        
        # Mock add_missing_indicators to return processed data with proper dates
        def mock_add_indicators(df):
            df['date'] = pd.to_datetime(df['date']).dt.date
            return df
            
        with patch('greyoak_score.data.ingestion.add_missing_indicators', side_effect=mock_add_indicators):
            df = load_prices_csv(csv_file)
        
        # Dates should be converted to date objects
        assert hasattr(df['date'].iloc[0], 'year')  # Should be date object


class TestLoadFundamentalsCSV:
    """Test loading fundamentals CSV data."""

    def test_load_fundamentals_success(self, tmp_path):
        """Test successful loading of fundamentals CSV."""
        csv_data = """ticker,quarter_end,roe_3y,roce_3y,eps_cagr_3y,sales_cagr_3y,pe,ev_ebitda,opm_stdev_12q
RELIANCE,2024-03-31,0.15,0.18,0.12,0.08,25.5,12.3,0.05
TCS,2024-03-31,0.28,0.32,0.18,0.15,28.2,18.5,0.03
"""
        
        csv_file = tmp_path / "fundamentals.csv"
        csv_file.write_text(csv_data)
        
        df = load_fundamentals_csv(csv_file)
        
        # Check basic properties
        assert len(df) == 2
        assert 'ticker' in df.columns
        assert 'roe_3y' in df.columns
        
        # Check quarter_end conversion
        assert hasattr(df['quarter_end'].iloc[0], 'year')

    def test_load_fundamentals_missing_file(self, tmp_path):
        """Test error handling for missing fundamentals file."""
        missing_file = tmp_path / "nonexistent.csv"
        
        with pytest.raises(FileNotFoundError, match="Fundamentals CSV not found"):
            load_fundamentals_csv(missing_file)

    def test_load_fundamentals_banking_exclusion(self, tmp_path):
        """Test that banking-specific columns are handled."""
        csv_data = """ticker,quarter_end,roe_3y,roce_3y,roe_3y_banking
HDFC,2024-03-31,0.15,0.18,0.20
"""
        
        csv_file = tmp_path / "fundamentals.csv"
        csv_file.write_text(csv_data)
        
        # Should not raise error even with banking column
        df = load_fundamentals_csv(csv_file)
        assert len(df) == 1


class TestLoadOwnershipCSV:
    """Test loading ownership CSV data."""

    def test_load_ownership_success(self, tmp_path):
        """Test successful loading of ownership CSV."""
        csv_data = """ticker,quarter_end,promoter_hold_pct,promoter_pledge_frac,fii_dii_delta_pp
RELIANCE,2024-03-31,0.50,0.05,2.5
TCS,2024-03-31,0.72,0.00,-1.2
"""
        
        csv_file = tmp_path / "ownership.csv"
        csv_file.write_text(csv_data)
        
        df = load_ownership_csv(csv_file)
        
        # Check basic properties
        assert len(df) == 2
        assert 'ticker' in df.columns
        assert 'promoter_hold_pct' in df.columns

    def test_load_ownership_missing_file(self, tmp_path):
        """Test error handling for missing ownership file."""
        missing_file = tmp_path / "nonexistent.csv"
        
        with pytest.raises(FileNotFoundError, match="Ownership CSV not found"):
            load_ownership_csv(missing_file)


class TestLoadSectorMapCSV:
    """Test loading sector map CSV data."""

    def test_load_sector_map_success(self, tmp_path):
        """Test successful loading of sector map CSV."""
        csv_data = """ticker,sector_id,sector_group,exchange
RELIANCE,ENERGY,energy,NSE
TCS,IT_SERVICES,it,NSE
HDFC,PRIVATE_BANKS,banks,NSE
"""
        
        csv_file = tmp_path / "sector_map.csv"
        csv_file.write_text(csv_data)
        
        df = load_sector_map_csv(csv_file)
        
        # Check basic properties
        assert len(df) == 3
        assert 'ticker' in df.columns
        assert 'sector_group' in df.columns

    def test_load_sector_map_missing_file(self, tmp_path):
        """Test error handling for missing sector map file."""
        missing_file = tmp_path / "nonexistent.csv"
        
        with pytest.raises(FileNotFoundError, match="Sector map CSV not found"):
            load_sector_map_csv(missing_file)


class TestLoadAllData:
    """Test loading all data files."""

    def create_test_files(self, tmp_path):
        """Helper to create all test CSV files."""
        # Prices CSV
        prices_data = """date,ticker,open,high,low,close,volume
2024-01-01,RELIANCE,2450,2500,2400,2480,1000000
2024-01-01,TCS,3400,3450,3350,3420,500000
"""
        (tmp_path / "prices.csv").write_text(prices_data)
        
        # Fundamentals CSV
        fundamentals_data = """ticker,quarter_end,roe_3y,roce_3y,eps_cagr_3y
RELIANCE,2024-03-31,0.15,0.18,0.12
TCS,2024-03-31,0.28,0.32,0.18
"""
        (tmp_path / "fundamentals.csv").write_text(fundamentals_data)
        
        # Ownership CSV
        ownership_data = """ticker,quarter_end,promoter_hold_pct,promoter_pledge_frac,fii_dii_delta_pp
RELIANCE,2024-03-31,0.50,0.05,2.5
TCS,2024-03-31,0.72,0.00,-1.2
"""
        (tmp_path / "ownership.csv").write_text(ownership_data)
        
        # Sector map CSV
        sector_data = """ticker,sector_id,sector_group,exchange
RELIANCE,ENERGY,energy,NSE
TCS,IT_SERVICES,it,NSE
"""
        (tmp_path / "sector_map.csv").write_text(sector_data)

    @patch('greyoak_score.data.ingestion.add_missing_indicators')
    def test_load_all_data_success(self, mock_indicators, tmp_path):
        """Test successful loading of all data files."""
        self.create_test_files(tmp_path)
        
        # Mock indicator calculation
        mock_indicators.return_value = pd.read_csv(tmp_path / "prices.csv")
        mock_indicators.return_value['date'] = pd.to_datetime(mock_indicators.return_value['date']).dt.date
        
        prices_df, fundamentals_df, ownership_df, sector_map_df = load_all_data(tmp_path)
        
        # Check all DataFrames loaded
        assert len(prices_df) == 2
        assert len(fundamentals_df) == 2
        assert len(ownership_df) == 2
        assert len(sector_map_df) == 2
        
        # Check tickers are consistent
        assert set(prices_df['ticker'].unique()) == {'RELIANCE', 'TCS'}
        assert set(fundamentals_df['ticker'].unique()) == {'RELIANCE', 'TCS'}

    def test_load_all_data_missing_file(self, tmp_path):
        """Test error handling when one file is missing."""
        # Create only some files
        (tmp_path / "prices.csv").write_text("date,ticker,open,high,low,close,volume\n")
        # Don't create fundamentals.csv
        
        with pytest.raises(FileNotFoundError):
            load_all_data(tmp_path)


class TestGetTickerSectorMap:
    """Test ticker to sector mapping utility."""

    def test_get_ticker_sector_map(self):
        """Test creating ticker to sector mapping."""
        sector_df = pd.DataFrame({
            'ticker': ['RELIANCE', 'TCS', 'HDFC'],
            'sector_group': ['energy', 'it', 'banks'],
            'sector_id': ['ENERGY', 'IT_SERVICES', 'PRIVATE_BANKS'],
        })
        
        sector_map = get_ticker_sector_map(sector_df)
        
        # Check mapping
        assert sector_map['RELIANCE'] == 'energy'
        assert sector_map['TCS'] == 'it'
        assert sector_map['HDFC'] == 'banks'
        
        # Check all tickers mapped
        assert len(sector_map) == 3

    def test_get_ticker_sector_map_empty(self):
        """Test with empty DataFrame."""
        empty_df = pd.DataFrame(columns=['ticker', 'sector_group'])
        
        sector_map = get_ticker_sector_map(empty_df)
        
        assert sector_map == {}

    def test_get_ticker_sector_map_duplicates(self):
        """Test handling of duplicate tickers (should take last)."""
        sector_df = pd.DataFrame({
            'ticker': ['TEST', 'TEST', 'OTHER'],
            'sector_group': ['old_sector', 'new_sector', 'other'],
        })
        
        sector_map = get_ticker_sector_map(sector_df)
        
        # Should take the last occurrence
        assert sector_map['TEST'] == 'new_sector'
        assert sector_map['OTHER'] == 'other'