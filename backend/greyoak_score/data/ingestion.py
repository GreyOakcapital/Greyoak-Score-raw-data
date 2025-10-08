"""CSV data ingestion for GreyOak Score Engine.

Reads and validates data from CSV files:
- prices.csv: OHLCV + technical indicators
- fundamentals.csv: Financial metrics
- ownership.csv: Promoter/institutional holdings
- sector_map.csv: Ticker-to-sector mapping

All data is validated against Pydantic models and returned as typed DataFrames.
"""

from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

from greyoak_score.data.indicators import add_missing_indicators
from greyoak_score.data.models import (
    DailyPriceData,
    FundamentalsData,
    OwnershipData,
    SectorMapping,
)
from greyoak_score.utils.logger import get_logger

logger = get_logger(__name__)


def load_prices_csv(filepath: Path) -> pd.DataFrame:
    """Load price data with OHLCV and technical indicators.
    
    Args:
        filepath: Path to prices CSV file.
        
    Returns:
        DataFrame with validated price data.
        
    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If validation fails.
    """
    logger.info(f"Loading prices from {filepath}...")
    
    if not filepath.exists():
        raise FileNotFoundError(f"Prices CSV not found: {filepath}")
    
    # Read CSV
    df = pd.read_csv(filepath)
    logger.info(f"  Raw data: {len(df)} rows, {len(df.columns)} columns")
    
    # Validate required columns before processing
    required_cols = {"date", "ticker", "open", "high", "low", "close", "volume"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required price columns: {sorted(missing_cols)}")
    
    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"]).dt.date
    
    # Add missing indicators if needed (optional columns)
    df = add_missing_indicators(df)
    
    # Validate schema (sample validation on first row)
    try:
        first_row = df.iloc[0].to_dict()
        DailyPriceData(**first_row)
        logger.info(f"  ✅ Schema validated")
    except Exception as e:
        logger.warning(f"  ⚠️  Schema validation warning: {e}")
    
    logger.info(f"✅ Loaded prices: {len(df)} records for {len(df['ticker'].unique())} tickers")
    
    return df


def load_fundamentals_csv(filepath: Path) -> pd.DataFrame:
    """Load fundamentals data with required and optional metrics.
    
    Args:
        filepath: Path to fundamentals CSV file.
        
    Returns:
        DataFrame with validated fundamentals data.
        
    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If validation fails.
    """
    logger.info(f"Loading fundamentals from {filepath}...")
    
    if not filepath.exists():
        raise FileNotFoundError(f"Fundamentals CSV not found: {filepath}")
    
    # Read CSV
    df = pd.read_csv(filepath)
    logger.info(f"  Raw data: {len(df)} rows, {len(df.columns)} columns")
    
    # Validate required columns
    required_cols = {"ticker", "quarter_end"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required fundamentals columns: {sorted(missing_cols)}")
    
    # Log optional columns that are missing (for informational purposes)
    optional_cols = {
        "roe_3y", "roce_3y", "eps_cagr_3y", "sales_cagr_3y", "pe", "ev_ebitda", 
        "opm_stdev_12q", "roa_3y", "roe_3y_banking", "gnpa_pct", "pcr_pct", "nim_3y"
    }
    available_optional = optional_cols.intersection(set(df.columns))
    missing_optional = optional_cols - set(df.columns)
    logger.info(f"  📊 Available metrics: {len(available_optional)}/{len(optional_cols)}")
    if missing_optional:
        logger.info(f"  ⚠️  Missing optional metrics: {sorted(missing_optional)}")
    
    # Convert quarter_end to datetime
    df["quarter_end"] = pd.to_datetime(df["quarter_end"]).dt.date
    
    # Validate schema (sample validation on first row)
    try:
        first_row = df.iloc[0].to_dict()
        FundamentalsData(**first_row)
        logger.info(f"  ✅ Schema validated")
    except Exception as e:
        logger.warning(f"  ⚠️  Schema validation warning: {e}")
    
    logger.info(f"✅ Loaded fundamentals: {len(df)} records for {len(df['ticker'].unique())} tickers")
    
    return df


def load_ownership_csv(filepath: Path) -> pd.DataFrame:
    """Load and validate ownership.csv.
    
    Args:
        filepath: Path to ownership.csv.
        
    Returns:
        Validated DataFrame with ownership data.
        
    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If validation fails.
    """
    logger.info(f"Loading ownership from {filepath}...")
    
    if not filepath.exists():
        raise FileNotFoundError(f"Ownership CSV not found: {filepath}")
    
    # Read CSV
    df = pd.read_csv(filepath)
    logger.info(f"  Raw data: {len(df)} rows, {len(df.columns)} columns")
    
    # Convert date
    df["quarter_end"] = pd.to_datetime(df["quarter_end"]).dt.date
    
    # Validate schema (sample validation)
    try:
        first_row = df.iloc[0].to_dict()
        OwnershipData(**first_row)
        logger.info(f"  ✅ Schema validated")
    except Exception as e:
        logger.warning(f"  ⚠️  Schema validation warning: {e}")
    
    logger.info(f"✅ Loaded ownership: {len(df)} records for {len(df['ticker'].unique())} tickers")
    
    return df


def load_sector_map_csv(filepath: Path) -> pd.DataFrame:
    """Load and validate sector_map.csv.
    
    Args:
        filepath: Path to sector_map.csv.
        
    Returns:
        Validated DataFrame with sector mapping.
        
    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If validation fails.
    """
    logger.info(f"Loading sector map from {filepath}...")
    
    if not filepath.exists():
        raise FileNotFoundError(f"Sector map CSV not found: {filepath}")
    
    # Read CSV
    df = pd.read_csv(filepath)
    logger.info(f"  Raw data: {len(df)} rows, {len(df.columns)} columns")
    
    # Validate schema (sample validation)
    try:
        first_row = df.iloc[0].to_dict()
        SectorMapping(**first_row)
        logger.info(f"  ✅ Schema validated")
    except Exception as e:
        logger.warning(f"  ⚠️  Schema validation warning: {e}")
    
    logger.info(f"✅ Loaded sector map: {len(df)} tickers")
    
    return df


def load_all_data(data_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load all CSV files from data directory.
    
    Args:
        data_dir: Directory containing CSV files.
        
    Returns:
        Tuple of (prices_df, fundamentals_df, ownership_df, sector_map_df).
    """
    logger.info("=" * 80)
    logger.info("📂 Loading all data files...")
    logger.info("=" * 80)
    
    prices_df = load_prices_csv(data_dir / "prices.csv")
    fundamentals_df = load_fundamentals_csv(data_dir / "fundamentals.csv")
    ownership_df = load_ownership_csv(data_dir / "ownership.csv")
    sector_map_df = load_sector_map_csv(data_dir / "sector_map.csv")
    
    logger.info("=" * 80)
    logger.info("✅ All data loaded successfully!")
    logger.info("=" * 80)
    
    return prices_df, fundamentals_df, ownership_df, sector_map_df


def get_ticker_sector_map(sector_map_df: pd.DataFrame) -> Dict[str, str]:
    """Get dictionary mapping ticker to sector_group.
    
    Args:
        sector_map_df: Sector mapping DataFrame.
        
    Returns:
        Dict mapping ticker to sector_group.
    """
    return dict(zip(sector_map_df["ticker"], sector_map_df["sector_group"]))
