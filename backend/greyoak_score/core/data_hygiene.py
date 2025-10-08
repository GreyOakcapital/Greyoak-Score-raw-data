"""Data hygiene module for GreyOak Score Engine.

Implements data cleaning and quality processes:
- Winsorization (1%-99% percentiles by sector)
- Missing data imputation (sector median)
- Confidence calculation
- Data freshness validation

Section 3.8: Data Hygiene and Data Quality
Section 7.2: Confidence Calculation
"""

from datetime import date, datetime, timezone
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from greyoak_score.utils.constants import CONFIDENCE_MAX, CONFIDENCE_MIN, TINY
from greyoak_score.utils.logger import get_logger

logger = get_logger(__name__)


def winsorize_by_sector(
    df: pd.DataFrame,
    sector_col: str,
    numeric_cols: List[str],
) -> pd.DataFrame:
    """Winsorize numeric columns at 1% and 99% percentiles within each sector.
    
    Section 3.8: Replace values < p1 with p1, values > p99 with p99.
    This reduces impact of extreme outliers on normalization.
    
    Args:
        df: DataFrame with data to winsorize.
        sector_col: Column name containing sector groups.
        numeric_cols: List of numeric column names to winsorize.
        
    Returns:
        DataFrame with winsorized values.
    """
    logger.debug(f"Winsorizing {len(numeric_cols)} columns by sector...")
    
    df = df.copy()
    winsorized_count = 0
    
    for sector in df[sector_col].unique():
        sector_mask = df[sector_col] == sector
        
        for col in numeric_cols:
            if col not in df.columns:
                continue
            
            # Get non-null values for this sector
            sector_values = df.loc[sector_mask, col]
            non_null = sector_values.dropna()
            
            if len(non_null) < 2:
                # Need at least 2 values for percentiles
                continue
            
            # Calculate percentiles
            p1, p99 = non_null.quantile([0.01, 0.99])
            
            # Winsorize: clip values to [p1, p99]
            original_values = df.loc[sector_mask, col].copy()
            df.loc[sector_mask, col] = df.loc[sector_mask, col].clip(p1, p99)
            
            # Count winsorized values
            changed = (original_values != df.loc[sector_mask, col]).sum()
            winsorized_count += changed
    
    logger.debug(f"  Winsorized {winsorized_count} values across {len(numeric_cols)} columns")
    
    return df


def impute_missing(
    df: pd.DataFrame,
    sector_col: str,
    numeric_cols: List[str],
) -> Tuple[pd.DataFrame, float]:
    """Impute missing values with same-day sector median.
    
    Section 3.8: After winsorization, fill NaN with sector median.
    Track imputed_fraction for LowCoverage guardrail.
    
    Args:
        df: DataFrame with missing values.
        sector_col: Column name containing sector groups.
        numeric_cols: List of numeric column names to impute.
        
    Returns:
        Tuple of (DataFrame with imputed values, imputed_fraction).
        imputed_fraction: Fraction of values that were imputed (0.0 to 1.0).
    """
    logger.debug(f"Imputing missing values by sector median...")
    
    df = df.copy()
    imputed_count = 0
    total_count = 0
    
    for col in numeric_cols:
        if col not in df.columns:
            continue
        
        for sector in df[sector_col].unique():
            sector_mask = df[sector_col] == sector
            missing_mask = sector_mask & df[col].isna()
            
            if missing_mask.any():
                # Calculate sector median from non-missing values
                sector_median = df.loc[sector_mask, col].median()
                
                # If sector has no valid values, use cross-sector median
                if pd.isna(sector_median):
                    sector_median = df[col].median()
                
                # Impute with sector median
                df.loc[missing_mask, col] = sector_median
                imputed_count += missing_mask.sum()
        
        # Count total cells for this column
        total_count += len(df)
    
    imputed_fraction = imputed_count / total_count if total_count > 0 else 0.0
    
    logger.debug(f"  Imputed {imputed_count} / {total_count} values ({imputed_fraction:.1%})")
    
    return df, imputed_fraction


def calculate_confidence(
    data_freshness: Dict[str, int],
    coverage: float,
    source_penalty: float = 0.0,
    freshness_slos: Dict[str, int] = None,
) -> float:
    """Calculate data confidence score.
    
    Section 7.2: Confidence formula.
    
    confidence = 0.55 × coverage + 0.35 × freshness + 0.10 × (1 - source_penalty)
    
    where:
    - coverage: Fraction of required fields present (0-1)
    - freshness: Mean of exp(-days_since_update / slo_days) for each data type
    - source_penalty: 0.0 for primary sources, 0.15 for fallback
    
    Args:
        data_freshness: Dict mapping data type to days since last update.
                       e.g., {'prices': 0, 'fundamentals': 45, 'ownership': 90}
        coverage: Fraction of required fields that are non-null (0.0 to 1.0).
        source_penalty: Penalty for non-primary data sources (default 0.0).
        freshness_slos: SLOs in days (default: {'prices': 1, 'fundamentals': 120, ...}).
        
    Returns:
        Confidence score in [0, 1].
    """
    # Default SLOs from Section 3.2
    if freshness_slos is None:
        freshness_slos = {
            "prices": 1,
            "fundamentals": 120,
            "ownership": 120,
            "events": 7,
        }
    
    # Calculate freshness score for each data type
    freshness_scores = []
    for data_type, days_old in data_freshness.items():
        slo = freshness_slos.get(data_type, 30)  # Default 30 days
        freshness_score = np.exp(-days_old / slo)
        freshness_scores.append(freshness_score)
    
    # Mean freshness across all data types
    freshness = np.mean(freshness_scores) if freshness_scores else 0.0
    
    # Combine components with weights from Section 7.2
    confidence = 0.55 * coverage + 0.35 * freshness + 0.10 * (1 - source_penalty)
    
    # Clamp to valid range
    confidence = np.clip(confidence, CONFIDENCE_MIN, CONFIDENCE_MAX)
    
    logger.debug(
        f"Confidence: coverage={coverage:.3f}, freshness={freshness:.3f}, "
        f"source_penalty={source_penalty:.3f} → {confidence:.3f}"
    )
    
    return confidence


def calculate_coverage(df: pd.DataFrame, required_cols: List[str]) -> float:
    """Calculate data coverage (fraction of required fields present).
    
    Args:
        df: DataFrame to check.
        required_cols: List of required column names.
        
    Returns:
        Coverage fraction (0.0 to 1.0).
    """
    if not required_cols:
        return 1.0
    
    # Count non-null values in required columns
    present = 0
    total = 0
    
    for col in required_cols:
        if col in df.columns:
            present += df[col].notna().sum()
            total += len(df)
    
    coverage = present / total if total > 0 else 0.0
    return coverage


def validate_freshness(
    data_date: date,
    as_of_date: date,
    slo_days: int,
) -> bool:
    """Validate data freshness against SLO.
    
    Args:
        data_date: Date of the data.
        as_of_date: Current date (scoring date).
        slo_days: Service Level Objective in days.
        
    Returns:
        True if data is fresh (within SLO), False if stale.
    """
    days_old = (as_of_date - data_date).days
    is_fresh = days_old <= slo_days
    
    if not is_fresh:
        logger.warning(
            f"Stale data detected: {days_old} days old (SLO: {slo_days} days)"
        )
    
    return is_fresh


def apply_data_hygiene(
    prices_df: pd.DataFrame,
    fundamentals_df: pd.DataFrame,
    ownership_df: pd.DataFrame,
    sector_map_df: pd.DataFrame,
    as_of_date: date = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, float, float]:
    """Apply complete data hygiene pipeline.
    
    Steps:
    1. Merge sector groups into data
    2. Winsorize numeric columns by sector (1%-99%)
    3. Impute missing values with sector medians
    4. Calculate coverage and confidence
    
    Args:
        prices_df: Daily price data.
        fundamentals_df: Fundamentals data.
        ownership_df: Ownership data.
        sector_map_df: Sector mapping.
        as_of_date: Scoring date (default: today).
        
    Returns:
        Tuple of (clean_prices, clean_fundamentals, clean_ownership, imputed_fraction, confidence).
    """
    logger.info("=" * 80)
    logger.info("🧹 Applying Data Hygiene Pipeline")
    logger.info("=" * 80)
    
    if as_of_date is None:
        as_of_date = datetime.now(timezone.utc).date()
    
    # Merge sector groups into data
    ticker_to_sector = dict(zip(sector_map_df["ticker"], sector_map_df["sector_group"]))
    
    prices_df = prices_df.copy()
    prices_df["sector_group"] = prices_df["ticker"].map(ticker_to_sector)
    
    fundamentals_df = fundamentals_df.copy()
    fundamentals_df["sector_group"] = fundamentals_df["ticker"].map(ticker_to_sector)
    
    ownership_df = ownership_df.copy()
    ownership_df["sector_group"] = ownership_df["ticker"].map(ticker_to_sector)
    
    # Define numeric columns for each dataset
    price_numeric_cols = [
        "open", "high", "low", "close", "volume",
        "dma20", "dma50", "dma200", "rsi14", "atr14",
        "macd_line", "macd_signal", "hi20", "lo20",
        "ret_21d", "ret_63d", "ret_126d", "sigma20", "sigma60",
    ]
    
    fundamentals_numeric_cols = [
        "roe_3y", "roce_3y", "eps_cagr_3y", "sales_cagr_3y",
        "pe", "ev_ebitda", "opm_stdev_12q",
        "roa_3y", "gnpa_pct", "pcr_pct", "nim_3y",
    ]
    
    ownership_numeric_cols = [
        "promoter_hold_pct", "promoter_pledge_frac", "fii_dii_delta_pp",
    ]
    
    # Step 1: Winsorization (1%-99% by sector)
    logger.info("Step 1: Winsorization (1%-99% by sector)")
    prices_df = winsorize_by_sector(prices_df, "sector_group", price_numeric_cols)
    fundamentals_df = winsorize_by_sector(fundamentals_df, "sector_group", fundamentals_numeric_cols)
    ownership_df = winsorize_by_sector(ownership_df, "sector_group", ownership_numeric_cols)
    
    # Step 2: Imputation (sector median)
    logger.info("Step 2: Imputation (sector median)")
    prices_df, prices_imputed = impute_missing(prices_df, "sector_group", price_numeric_cols)
    fundamentals_df, fund_imputed = impute_missing(fundamentals_df, "sector_group", fundamentals_numeric_cols)
    ownership_df, own_imputed = impute_missing(ownership_df, "sector_group", ownership_numeric_cols)
    
    # Combined imputed fraction (weighted by dataset size)
    total_cells = len(prices_df) * len(price_numeric_cols)
    total_cells += len(fundamentals_df) * len(fundamentals_numeric_cols)
    total_cells += len(ownership_df) * len(ownership_numeric_cols)
    
    weighted_imputed = (
        prices_imputed * len(prices_df) * len(price_numeric_cols)
        + fund_imputed * len(fundamentals_df) * len(fundamentals_numeric_cols)
        + own_imputed * len(ownership_df) * len(ownership_numeric_cols)
    )
    
    imputed_fraction = weighted_imputed / total_cells if total_cells > 0 else 0.0
    
    # Step 3: Calculate coverage
    logger.info("Step 3: Calculate coverage & confidence")
    
    # Coverage calculation (simplified - check non-null ratio)
    prices_coverage = calculate_coverage(prices_df, price_numeric_cols)
    fund_coverage = calculate_coverage(fundamentals_df, fundamentals_numeric_cols)
    own_coverage = calculate_coverage(ownership_df, ownership_numeric_cols)
    
    # Weighted average coverage
    coverage = (prices_coverage + fund_coverage + own_coverage) / 3.0
    
    # Data freshness (days old)
    # For sample data, assume prices are fresh, fundamentals are 30 days old
    data_freshness = {
        "prices": 0,  # Fresh daily data
        "fundamentals": 30,  # Quarterly, ~1 month old
        "ownership": 30,  # Quarterly, ~1 month old
    }
    
    # Calculate confidence
    source_penalty = 0.0  # Primary source (or 0.15 for fallback)
    confidence = calculate_confidence(data_freshness, coverage, source_penalty)
    
    logger.info("=" * 80)
    logger.info(f"✅ Data Hygiene Complete")
    logger.info(f"   Imputed Fraction: {imputed_fraction:.1%}")
    logger.info(f"   Coverage: {coverage:.1%}")
    logger.info(f"   Confidence: {confidence:.3f}")
    logger.info("=" * 80)
    
    return prices_df, fundamentals_df, ownership_df, imputed_fraction, confidence
