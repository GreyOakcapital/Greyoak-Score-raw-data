"""Sector normalization engine for GreyOak Score Engine.

Converts raw metrics to 0-100 point scores using sector-aware normalization:
- Z-score method for sectors with ≥6 stocks
- ECDF (percentile rank) method for small sectors (n<6)
- Handles "higher better" vs "lower better" metrics

Section 4: Sector-Aware Normalization and Percentile Mapping
Section 4.1: Z-Score and ECDF Fallback
"""

from typing import Literal

import numpy as np
import pandas as pd

from greyoak_score.data.models import NormalizationResult
from greyoak_score.utils.constants import (
    NORM_CENTER,
    NORM_SCALE,
    SCORE_MAX,
    SCORE_MIN,
    SMALL_SECTOR_THRESHOLD,
    TINY,
)
from greyoak_score.utils.logger import get_logger

logger = get_logger(__name__)


def compute_z_score(
    value: float,
    sector_median: float,
    sector_std: float,
    higher_better: bool,
) -> float:
    """Calculate z-score for sector normalization.
    
    Section 4.1: Sector-aware z-score normalization.
    
    If higher_better: z = (value - median) / stdev
    If lower_better:  z = (median - value) / stdev  (flip direction)
    
    Args:
        value: Raw metric value.
        sector_median: Sector median for this metric.
        sector_std: Sector standard deviation.
        higher_better: True if higher values are better, False if lower is better.
        
    Returns:
        Z-score (can be any value, typically -3 to +3).
    """
    if higher_better:
        z = (value - sector_median) / (sector_std + TINY)
    else:
        # Flip direction for "lower is better" metrics
        z = (sector_median - value) / (sector_std + TINY)
    
    return z


def z_score_to_points(z: float) -> float:
    """Convert z-score to 0-100 point scale.
    
    Section 4.1: Points mapping formula.
    
    points = clamp(50 + 15 × z, 0, 100)
    
    This maps:
    - z = -3.33 → points = 0
    - z = -2.0  → points ≈ 20
    - z = 0.0   → points = 50 (sector median)
    - z = +2.0  → points ≈ 80
    - z = +3.33 → points = 100
    
    Args:
        z: Z-score value.
        
    Returns:
        Points in [0, 100].
    """
    points = NORM_CENTER + NORM_SCALE * z
    return np.clip(points, SCORE_MIN, SCORE_MAX)


def percentile_to_points(rank: int, n: int) -> float:
    """Convert percentile rank to 0-100 points (ECDF method).
    
    Section 4.1: Fallback for small sectors (n < 6) or zero stdev.
    
    When sector size < 6 or stdev ≈ 0, use empirical CDF (percentile rank).
    
    points = (rank / (n + 1)) × 100
    
    Args:
        rank: Rank of value (1 = lowest, n = highest).
        n: Total number of values in sector.
        
    Returns:
        Points in [0, 100].
    """
    if n < 1:
        return NORM_CENTER  # Neutral for empty sector
    
    percentile = rank / (n + 1)
    return percentile * 100.0


def normalize_metric(
    df: pd.DataFrame,
    metric: str,
    sector_col: str,
    higher_better: bool,
) -> pd.Series:
    """Normalize a metric to 0-100 points within sectors.
    
    Section 4.1: Sector-aware normalization with ECDF fallback.
    
    Logic:
    - If sector has ≥ 6 stocks AND stdev > TINY: Use z-score method
    - Otherwise: Use percentile rank method (ECDF)
    
    Args:
        df: DataFrame with data.
        metric: Column name of metric to normalize.
        sector_col: Column name containing sector groups.
        higher_better: True if higher values are better, False if lower is better.
        
    Returns:
        Series of normalized points (0-100) with same index as df.
    """
    if metric not in df.columns:
        logger.warning(f"Metric '{metric}' not found in DataFrame, returning NaN")
        return pd.Series(np.nan, index=df.index)
    
    points = pd.Series(index=df.index, dtype=float)
    method_used = {}
    
    for sector in df[sector_col].unique():
        sector_mask = df[sector_col] == sector
        values = df.loc[sector_mask, metric]
        
        # Drop NaN values for stats calculation
        non_null_values = values.dropna()
        n = len(non_null_values)
        
        if n == 0:
            # No valid values in sector - assign neutral score
            points.loc[sector_mask] = NORM_CENTER
            method_used[sector] = "empty"
            continue
        
        if n == 1:
            # Single value - assign neutral score
            points.loc[sector_mask] = NORM_CENTER
            method_used[sector] = "single"
            continue
        
        # Calculate sector statistics
        sector_median = non_null_values.median()
        sector_std = non_null_values.std()
        
        # Decide method: z-score if n ≥ 6 AND stdev > TINY, else ECDF
        if n >= SMALL_SECTOR_THRESHOLD and sector_std > TINY:
            # Use z-score method
            for idx in values.index:
                val = values[idx]
                if pd.isna(val):
                    points[idx] = np.nan
                else:
                    z = compute_z_score(val, sector_median, sector_std, higher_better)
                    points[idx] = z_score_to_points(z)
            
            method_used[sector] = f"z-score (n={n})"
        else:
            # Use ECDF (percentile rank) method
            # Rank values (1 = lowest, n = highest)
            if higher_better:
                ranks = values.rank(method="average", na_option="keep")
            else:
                # For lower-better, reverse ranks
                ranks = values.rank(method="average", ascending=False, na_option="keep")
            
            points.loc[sector_mask] = ranks.apply(
                lambda r: percentile_to_points(r, n) if not pd.isna(r) else np.nan
            )
            
            reason = f"n<{SMALL_SECTOR_THRESHOLD}" if n < SMALL_SECTOR_THRESHOLD else "stdev≈0"
            method_used[sector] = f"ECDF ({reason}, n={n})"
    
    # Log normalization summary
    logger.debug(f"Normalized '{metric}' (higher_better={higher_better}):")
    for sector, method in method_used.items():
        logger.debug(f"  {sector}: {method}")
    
    return points


def normalize_metric_detailed(
    df: pd.DataFrame,
    metric: str,
    sector_col: str,
    higher_better: bool,
) -> pd.DataFrame:
    """Normalize metric with detailed intermediate values (for debugging).
    
    Returns DataFrame with columns:
    - ticker
    - sector_group
    - value (raw)
    - sector_median
    - sector_std
    - z_score
    - method
    - points (0-100)
    
    Args:
        df: DataFrame with data.
        metric: Column name of metric to normalize.
        sector_col: Column name containing sector groups.
        higher_better: True if higher values are better.
        
    Returns:
        DataFrame with normalization details.
    """
    results = []
    
    for sector in df[sector_col].unique():
        sector_mask = df[sector_col] == sector
        sector_df = df.loc[sector_mask].copy()
        
        values = sector_df[metric]
        non_null = values.dropna()
        n = len(non_null)
        
        if n == 0:
            continue
        
        sector_median = non_null.median()
        sector_std = non_null.std()
        
        # Determine method
        if n >= SMALL_SECTOR_THRESHOLD and sector_std > TINY:
            method = "z_score"
        else:
            method = "percentile"
        
        for idx, row in sector_df.iterrows():
            value = row[metric]
            
            if pd.isna(value):
                z_score = np.nan
                points = np.nan
            elif method == "z_score":
                z_score = compute_z_score(value, sector_median, sector_std, higher_better)
                points = z_score_to_points(z_score)
            else:  # percentile
                if higher_better:
                    rank = values.rank(method="average")[idx]
                else:
                    rank = values.rank(method="average", ascending=False)[idx]
                z_score = np.nan  # Not applicable for percentile
                points = percentile_to_points(rank, n)
            
            results.append({
                "ticker": row.get("ticker"),
                "sector_group": sector,
                "value": value,
                "sector_median": sector_median,
                "sector_std": sector_std,
                "z_score": z_score,
                "method": method,
                "points": points,
            })
    
    return pd.DataFrame(results)


def batch_normalize_metrics(
    df: pd.DataFrame,
    metrics: dict,
    sector_col: str,
) -> pd.DataFrame:
    """Normalize multiple metrics at once.
    
    Args:
        df: DataFrame with data.
        metrics: Dict mapping metric name to higher_better bool.
                e.g., {'roe_3y': True, 'pe': False}
        sector_col: Column name containing sector groups.
        
    Returns:
        DataFrame with original data plus normalized columns (suffix '_points').
    """
    result_df = df.copy()
    
    for metric, higher_better in metrics.items():
        points_col = f"{metric}_points"
        result_df[points_col] = normalize_metric(
            df, metric, sector_col, higher_better
        )
        
        logger.info(
            f"  Normalized {metric}: "
            f"min={result_df[points_col].min():.1f}, "
            f"median={result_df[points_col].median():.1f}, "
            f"max={result_df[points_col].max():.1f}"
        )
    
    return result_df
