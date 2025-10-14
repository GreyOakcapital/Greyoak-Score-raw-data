"""
GreyOak Predictor - Feature Engineering Module
MVP Feature Set: Returns, RSI, ATR, DMAs, Breakout, Volume
"""

import numpy as np
import pandas as pd
from typing import Optional


def calculate_returns(df: pd.DataFrame, periods: list = [1, 5, 10, 20]) -> pd.DataFrame:
    """Calculate simple returns for multiple periods"""
    df = df.copy()
    for period in periods:
        df[f'ret_{period}'] = df['close'].pct_change(period)
    return df


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate RSI (Relative Strength Index)"""
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(span=period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(span=period, adjust=False).mean()
    
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_dma(df: pd.DataFrame, periods: list = [20, 50]) -> pd.DataFrame:
    """Calculate Daily Moving Averages and distance from price"""
    df = df.copy()
    for period in periods:
        dma = df['close'].rolling(window=period).mean()
        df[f'dma{period}'] = dma
        df[f'dist_dma{period}'] = (df['close'] - dma) / df['close']
    return df


def calculate_volume_features(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Calculate volume-based features"""
    df = df.copy()
    
    # Volume surprise (current vol / 20-day avg)
    df['vol_avg20'] = df['volume'].rolling(window=period).mean()
    df['vol_surp'] = df['volume'] / (df['vol_avg20'] + 1)
    
    return df


def calculate_breakout(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Calculate breakout feature (distance from 20-day high)"""
    df = df.copy()
    
    # Calculate ATR if not present
    if 'atr14' not in df.columns:
        from predictor.labels import calculate_atr
        df['atr14'] = calculate_atr(df, period=14)
    
    # 20-day high and low
    df['hi20'] = df['high'].rolling(window=period).max()
    df['lo20'] = df['low'].rolling(window=period).min()
    
    # Breakout above 20-day high
    atr_min = np.maximum(0.75 * df['atr14'], 0.01 * df['close'])
    df['breakout'] = np.maximum(0, df['close'] - df['hi20']) / atr_min
    
    return df


def build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build complete feature frame for MVP
    
    MVP Features:
    - ret_1, ret_5, ret_10, ret_20
    - rsi14
    - atr14_pct (ATR14 / close)
    - dist_dma20, dist_dma50
    - breakout
    - vol_surp
    
    Args:
        df: DataFrame with OHLCV data (sorted by date)
    
    Returns:
        DataFrame with all features
    """
    df = df.copy()
    
    # Returns
    df = calculate_returns(df, periods=[1, 5, 10, 20])
    
    # RSI
    df['rsi14'] = calculate_rsi(df, period=14)
    
    # ATR
    from predictor.labels import calculate_atr
    df['atr14'] = calculate_atr(df, period=14)
    df['atr14_pct'] = df['atr14'] / df['close']
    
    # DMAs
    df = calculate_dma(df, periods=[20, 50])
    
    # Breakout
    df = calculate_breakout(df, period=20)
    
    # Volume
    df = calculate_volume_features(df, period=20)
    
    return df


def standardize_features(
    df: pd.DataFrame,
    feature_cols: list,
    method: str = 'cross_sectional',
    min_stocks: int = 6,
    ts_alpha: float = 0.06
) -> pd.DataFrame:
    """
    Standardize features (z-score normalization)
    
    Args:
        df: DataFrame with features (multi-stock, with 'date' and 'symbol' columns)
        feature_cols: List of feature column names to standardize
        method: 'cross_sectional' or 'time_series'
        min_stocks: Minimum stocks needed for cross-sectional z-score
        ts_alpha: EWMA alpha for time-series z-score
    
    Returns:
        DataFrame with standardized features (original columns overwritten)
    """
    df = df.copy()
    
    if method == 'cross_sectional':
        # Cross-sectional standardization (within each date)
        for date in df['date'].unique():
            date_mask = df['date'] == date
            date_data = df.loc[date_mask, feature_cols]
            
            # Check if enough stocks and variation
            if len(date_data) >= min_stocks and date_data.std().sum() > 1e-6:
                # Cross-sectional z-score
                z_scores = (date_data - date_data.mean()) / (date_data.std() + 1e-9)
                df.loc[date_mask, feature_cols] = z_scores
            else:
                # Fallback to time-series z-score
                for symbol in df.loc[date_mask, 'symbol'].unique():
                    symbol_mask = (df['symbol'] == symbol)
                    for col in feature_cols:
                        ts_data = df.loc[symbol_mask, col]
                        if len(ts_data) > 20:  # Need history
                            ewm_mean = ts_data.ewm(alpha=ts_alpha, adjust=False).mean()
                            ewm_std = ts_data.ewm(alpha=ts_alpha, adjust=False).std()
                            ts_z = (ts_data - ewm_mean) / (ewm_std + 1e-9)
                            df.loc[symbol_mask, col] = ts_z
    
    elif method == 'time_series':
        # Time-series standardization (per stock)
        for symbol in df['symbol'].unique():
            symbol_mask = df['symbol'] == symbol
            for col in feature_cols:
                ts_data = df.loc[symbol_mask, col]
                if len(ts_data) > 20:
                    ewm_mean = ts_data.ewm(alpha=ts_alpha, adjust=False).mean()
                    ewm_std = ts_data.ewm(alpha=ts_alpha, adjust=False).std()
                    ts_z = (ts_data - ewm_mean) / (ewm_std + 1e-9)
                    df.loc[symbol_mask, col] = ts_z
    
    return df


def get_feature_columns() -> list:
    """Return list of MVP feature columns"""
    return [
        'ret_1', 'ret_5', 'ret_10', 'ret_20',
        'rsi14',
        'atr14_pct',
        'dist_dma20', 'dist_dma50',
        'breakout',
        'vol_surp'
    ]


if __name__ == "__main__":
    # Test feature engineering
    print("Testing feature engineering...")
    
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    
    df = pd.DataFrame({
        'date': dates,
        'symbol': 'TEST',
        'open': 100 + np.cumsum(np.random.randn(100) * 2),
        'high': 102 + np.cumsum(np.random.randn(100) * 2),
        'low': 98 + np.cumsum(np.random.randn(100) * 2),
        'close': 100 + np.cumsum(np.random.randn(100) * 2),
        'volume': np.random.randint(1000000, 5000000, 100)
    })
    
    # Build features
    df_feat = build_feature_frame(df)
    
    print(f"\n✅ Generated features:")
    for col in get_feature_columns():
        if col in df_feat.columns:
            print(f"  {col}: {df_feat[col].notna().sum()} valid values")
    
    print("\n✅ Feature engineering test complete")
