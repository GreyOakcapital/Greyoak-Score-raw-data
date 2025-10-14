"""
GreyOak Predictor - Labeling Module
Triple Barrier Method for generating labels
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict


def triple_barrier(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    U: np.ndarray,
    L: np.ndarray,
    T: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Triple barrier labeling: Up, Down, or Timeout
    
    Args:
        close: Closing prices array
        high: High prices array
        low: Low prices array
        U: Up barrier (return threshold, e.g., 0.08 for 8%)
        L: Down barrier (return threshold, e.g., 0.08 for 8%)
        T: Time horizon in bars
    
    Returns:
        labels: +1 (hit up first), -1 (hit down first), 0 (timeout or same-bar double)
        hit_up: Boolean array indicating if up barrier was touched
        hit_dn: Boolean array indicating if down barrier was touched
    """
    n = len(close)
    labels = np.zeros(n, dtype=int)
    hit_up = np.zeros(n, dtype=bool)
    hit_dn = np.zeros(n, dtype=bool)
    
    for i in range(n):
        if i + T > n:
            # Not enough forward data
            labels[i] = 0
            continue
        
        # Calculate barrier prices
        U_px = close[i] * (1 + U[i])
        L_px = close[i] * (1 - L[i])
        
        # Walk forward up to T bars
        label_set = False
        for j in range(i + 1, min(i + T + 1, n)):
            hit_up_bar = high[j] >= U_px
            hit_dn_bar = low[j] <= L_px
            
            # Same bar double touch = neutral
            if hit_up_bar and hit_dn_bar:
                labels[i] = 0
                hit_up[i] = True
                hit_dn[i] = True
                label_set = True
                break
            
            # Up touched first
            if hit_up_bar:
                labels[i] = +1
                hit_up[i] = True
                label_set = True
                break
            
            # Down touched first
            if hit_dn_bar:
                labels[i] = -1
                hit_dn[i] = True
                label_set = True
                break
        
        # Timeout if no touch within T bars
        if not label_set:
            labels[i] = 0
    
    return labels, hit_up, hit_dn


def calculate_barriers(df: pd.DataFrame, k: float = 1.8) -> pd.DataFrame:
    """
    Calculate ATR-based barriers
    
    Args:
        df: DataFrame with OHLCV data
        k: Multiplier for ATR (default 1.8)
    
    Returns:
        DataFrame with U and L columns (return barriers)
    """
    df = df.copy()
    
    # Calculate ATR14 if not present
    if 'atr14' not in df.columns:
        df['atr14'] = calculate_atr(df, period=14)
    
    # Barrier as percentage return
    df['atr14_pct'] = df['atr14'] / df['close']
    df['U'] = k * df['atr14_pct']
    df['L'] = k * df['atr14_pct']
    
    return df


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()
    
    return atr


def generate_labels_for_stock(
    df: pd.DataFrame,
    horizon: int = 20,
    k: float = 1.8
) -> pd.DataFrame:
    """
    Generate labels for a single stock
    
    Args:
        df: DataFrame with OHLCV data (must be sorted by date)
        horizon: Forward-looking window in bars
        k: Barrier multiplier
    
    Returns:
        DataFrame with labels and barriers
    """
    df = df.copy().sort_values('date').reset_index(drop=True)
    
    # Calculate barriers
    df = calculate_barriers(df, k=k)
    
    # Generate labels
    labels, hit_up, hit_dn = triple_barrier(
        close=df['close'].values,
        high=df['high'].values,
        low=df['low'].values,
        U=df['U'].values,
        L=df['L'].values,
        T=horizon
    )
    
    df['label'] = labels
    df['hit_up'] = hit_up
    df['hit_dn'] = hit_dn
    
    # Remove last T bars (can't label them)
    df = df.iloc[:-horizon].copy()
    
    return df


def apply_eligibility_filters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply eligibility filters to remove problematic rows
    
    Args:
        df: DataFrame with labeled data
    
    Returns:
        Filtered DataFrame
    """
    df = df.copy()
    
    # Remove rows with missing data
    df = df.dropna(subset=['close', 'high', 'low', 'volume'])
    
    # Remove zero volume days (likely suspended)
    df = df[df['volume'] > 0]
    
    # Remove extreme price movements (likely data errors)
    df['pct_change'] = df['close'].pct_change()
    df = df[(df['pct_change'].abs() < 0.30) | df['pct_change'].isna()]
    df = df.drop('pct_change', axis=1)
    
    return df


if __name__ == "__main__":
    # Test the labeling function
    print("Testing triple barrier labeling...")
    
    # Create sample data
    np.random.seed(42)
    n = 100
    close = 100 * np.exp(np.cumsum(np.random.randn(n) * 0.02))
    high = close * (1 + np.abs(np.random.randn(n) * 0.01))
    low = close * (1 - np.abs(np.random.randn(n) * 0.01))
    
    # Static barriers
    U = np.ones(n) * 0.05  # 5% up
    L = np.ones(n) * 0.05  # 5% down
    
    labels, hit_up, hit_dn = triple_barrier(close, high, low, U, L, T=10)
    
    print(f"Labels distribution:")
    print(f"  +1 (Up): {(labels == 1).sum()}")
    print(f"  0 (Neutral): {(labels == 0).sum()}")
    print(f"  -1 (Down): {(labels == -1).sum()}")
    print(f"Coverage: {(labels != 0).mean():.1%}")
    print("\n✅ Labeling test complete")
