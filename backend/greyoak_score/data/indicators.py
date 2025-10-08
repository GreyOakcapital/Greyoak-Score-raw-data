"""Technical indicator calculations for GreyOak Score Engine.

Computes missing indicators from OHLCV data if not present in CSVs.
All indicators follow standard definitions from technical analysis literature.

Indicators computed:
- RSI (Relative Strength Index)
- ATR (Average True Range)
- MACD (Moving Average Convergence Divergence)
- Moving Averages (DMA 20, 50, 200)
- Rolling extremes (hi_20d, lo_20d)
- Returns (21d, 63d, 126d)
- Volatility (sigma20, sigma60)
"""

from typing import Tuple

import numpy as np
import pandas as pd

from greyoak_score.utils.constants import TINY
from greyoak_score.utils.logger import get_logger

logger = get_logger(__name__)


def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI (Relative Strength Index).
    
    RSI = 100 - (100 / (1 + RS))
    where RS = Average Gain / Average Loss over period
    
    Args:
        data: Price series (typically Close).
        period: RSI period (default 14).
        
    Returns:
        RSI values (0-100).
    """
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + TINY)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Calculate ATR (Average True Range).
    
    True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
    ATR = Rolling mean of True Range
    
    Args:
        high: High prices.
        low: Low prices.
        close: Close prices.
        period: ATR period (default 14).
        
    Returns:
        ATR values.
    """
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def calculate_macd(
    data: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[pd.Series, pd.Series]:
    """Calculate MACD (Moving Average Convergence Divergence).
    
    MACD Line = EMA(fast) - EMA(slow)
    Signal Line = EMA(MACD Line, signal)
    
    Args:
        data: Price series (typically Close).
        fast: Fast EMA period (default 12).
        slow: Slow EMA period (default 26).
        signal: Signal line period (default 9).
        
    Returns:
        Tuple of (MACD line, Signal line).
    """
    ema_fast = data.ewm(span=fast, adjust=False).mean()
    ema_slow = data.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def calculate_volatility(data: pd.Series, period: int) -> pd.Series:
    """Calculate volatility (standard deviation of log returns).
    
    Args:
        data: Price series.
        period: Rolling window size.
        
    Returns:
        Daily volatility (not annualized).
    """
    log_returns = np.log(data / (data.shift(1) + TINY))
    volatility = log_returns.rolling(window=period).std()
    return volatility


def add_missing_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add missing technical indicators to price DataFrame.
    
    Computes indicators only if they're missing from the DataFrame.
    Operates on a per-ticker basis (assumes df is sorted by ticker, date).
    
    Args:
        df: DataFrame with OHLCV data (must have columns: ticker, date, open, high, low, close, volume).
        
    Returns:
        DataFrame with all indicators added.
    """
    logger.info("Adding missing technical indicators...")
    
    required_cols = ["ticker", "date", "open", "high", "low", "close", "volume"]
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Work on a copy
    df = df.copy()
    
    # Sort by ticker, date for correct indicator calculation
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    
    # Process each ticker separately
    processed = []
    
    for ticker, group in df.groupby("ticker"):
        # Moving averages
        if "dma20" not in df.columns or group["dma20"].isna().all():
            group["dma20"] = group["close"].rolling(window=20).mean()
        
        if "dma50" not in df.columns or group["dma50"].isna().all():
            group["dma50"] = group["close"].rolling(window=50).mean()
        
        if "dma200" not in df.columns or group["dma200"].isna().all():
            group["dma200"] = group["close"].rolling(window=200).mean()
        
        # RSI
        if "rsi14" not in df.columns or group["rsi14"].isna().all():
            group["rsi14"] = calculate_rsi(group["close"], period=14)
        
        # ATR
        if "atr14" not in df.columns or group["atr14"].isna().all():
            group["atr14"] = calculate_atr(
                group["high"],
                group["low"],
                group["close"],
                period=14,
            )
        
        # MACD
        if "macd_line" not in df.columns or group["macd_line"].isna().all():
            macd_line, macd_signal = calculate_macd(group["close"])
            group["macd_line"] = macd_line
            group["macd_signal"] = macd_signal
        
        # Rolling extremes
        if "hi20" not in df.columns or group["hi20"].isna().all():
            group["hi20"] = group["high"].rolling(window=20).max()
        
        if "lo20" not in df.columns or group["lo20"].isna().all():
            group["lo20"] = group["low"].rolling(window=20).min()
        
        # Returns
        if "ret_21d" not in df.columns or group["ret_21d"].isna().all():
            group["ret_21d"] = group["close"].pct_change(periods=21)
        
        if "ret_63d" not in df.columns or group["ret_63d"].isna().all():
            group["ret_63d"] = group["close"].pct_change(periods=63)
        
        if "ret_126d" not in df.columns or group["ret_126d"].isna().all():
            group["ret_126d"] = group["close"].pct_change(periods=126)
        
        # Volatility
        if "sigma20" not in df.columns or group["sigma20"].isna().all():
            group["sigma20"] = calculate_volatility(group["close"], period=20)
        
        if "sigma60" not in df.columns or group["sigma60"].isna().all():
            group["sigma60"] = calculate_volatility(group["close"], period=60)
        
        processed.append(group)
    
    result = pd.concat(processed, ignore_index=True)
    logger.info(f"✅ Indicators added for {len(df['ticker'].unique())} tickers")
    
    return result
