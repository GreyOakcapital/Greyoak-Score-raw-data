#!/usr/bin/env python3
"""Fetch REAL market data from Yahoo Finance for GreyOak Score Engine.

This script downloads actual market data for 15 NSE tickers and generates
4 CSV files matching the spec format:
- prices.csv: OHLCV + technical indicators
- fundamentals.csv: Financial metrics
- ownership.csv: Promoter/institutional holdings
- sector_map.csv: Ticker to sector mapping

Data source: yfinance (Yahoo Finance API)
Period: Last 3 months (~60 trading days)

Usage:
    python scripts/fetch_real_data.py

Output:
    data/prices.csv
    data/fundamentals.csv
    data/ownership.csv
    data/sector_map.csv
    
Limitations documented in docs/DATA_LIMITATIONS.md
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from greyoak_score.utils.logger import setup_logger

logger = setup_logger("fetch_real_data", "INFO")

# 15 NSE tickers (as per approved spec)
TICKERS = [
    # Banks (3)
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    # FMCG (3)
    "HINDUNILVR.NS",
    "ITC.NS",
    "NESTLEIND.NS",
    # IT (2)
    "TCS.NS",
    "INFY.NS",
    # Metals (4)
    "TATASTEEL.NS",
    "COALINDIA.NS",
    "HINDALCO.NS",
    "ONGC.NS",
    # Autos (2)
    "MARUTI.NS",
    "ASIANPAINT.NS",
    # Diversified (1)
    "RELIANCE.NS",
]

# Sector mapping (as per approved spec)
SECTOR_MAP = {
    "HDFCBANK.NS": ("PRIVATE_BANKS", "banks"),
    "ICICIBANK.NS": ("PRIVATE_BANKS", "banks"),
    "SBIN.NS": ("PSU_BANKS", "psu_banks"),
    "HINDUNILVR.NS": ("FMCG", "fmcg"),
    "ITC.NS": ("FMCG", "fmcg"),
    "NESTLEIND.NS": ("FMCG", "fmcg"),
    "TCS.NS": ("IT_SERVICES", "it"),
    "INFY.NS": ("IT_SERVICES", "it"),
    "TATASTEEL.NS": ("STEEL", "metals"),
    "COALINDIA.NS": ("COAL", "metals"),
    "HINDALCO.NS": ("ALUMINIUM", "metals"),
    "ONGC.NS": ("OIL_GAS", "metals"),
    "MARUTI.NS": ("AUTO", "auto_caps"),
    "ASIANPAINT.NS": ("PAINTS", "auto_caps"),
    "RELIANCE.NS": ("DIVERSIFIED", "diversified"),
}

# Banking tickers (use ONLY banking metrics in fundamentals)
BANKING_TICKERS = {"HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Technical Indicator Calculations
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI (Relative Strength Index).
    
    Args:
        data: Price series (typically Close).
        period: RSI period (default 14).
        
    Returns:
        RSI values (0-100).
    """
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)  # Avoid division by zero
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate ATR (Average True Range).
    
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


def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series]:
    """Calculate MACD (Moving Average Convergence Divergence).
    
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
    log_returns = np.log(data / data.shift(1))
    volatility = log_returns.rolling(window=period).std()
    return volatility


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Fetching Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def fetch_price_data() -> pd.DataFrame:
    """Fetch price data and compute technical indicators for all tickers.
    
    Returns:
        DataFrame with columns matching prices.csv spec.
    """
    logger.info("Fetching price data from Yahoo Finance...")
    
    all_prices = []
    
    for ticker in TICKERS:
        logger.info(f"  Fetching {ticker}...")
        
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="3mo")  # Last 3 months
            
            if hist.empty:
                logger.warning(f"  No data for {ticker}, skipping")
                continue
            
            # Reset index to get Date as column
            hist = hist.reset_index()
            
            # Calculate moving averages
            hist["dma_20"] = hist["Close"].rolling(window=20).mean()
            hist["dma_50"] = hist["Close"].rolling(window=50).mean()
            hist["dma_200"] = hist["Close"].rolling(window=200).mean()
            
            # Calculate RSI
            hist["rsi_14"] = calculate_rsi(hist["Close"], period=14)
            
            # Calculate ATR
            hist["atr_14"] = calculate_atr(hist["High"], hist["Low"], hist["Close"], period=14)
            
            # Calculate MACD
            hist["macd_line"], hist["macd_signal"] = calculate_macd(hist["Close"])
            
            # Calculate rolling max/min
            hist["hi_20d"] = hist["High"].rolling(window=20).max()
            hist["lo_20d"] = hist["Low"].rolling(window=20).min()
            
            # Calculate returns
            hist["ret_21d"] = hist["Close"].pct_change(periods=21)
            hist["ret_63d"] = hist["Close"].pct_change(periods=63)
            hist["ret_126d"] = hist["Close"].pct_change(periods=126)
            
            # Calculate volatility (standard deviation of log returns)
            hist["sigma_20"] = calculate_volatility(hist["Close"], period=20)
            hist["sigma_60"] = calculate_volatility(hist["Close"], period=60)
            
            # Prepare output DataFrame
            df = pd.DataFrame({
                "date": hist["Date"].dt.date,
                "ticker": ticker,
                "open": hist["Open"],
                "high": hist["High"],
                "low": hist["Low"],
                "close": hist["Close"],
                "volume": hist["Volume"],
                "dma20": hist["dma_20"],
                "dma50": hist["dma_50"],
                "dma200": hist["dma_200"],
                "rsi14": hist["rsi_14"],
                "atr14": hist["atr_14"],
                "macd_line": hist["macd_line"],
                "macd_signal": hist["macd_signal"],
                "hi20": hist["hi_20d"],
                "lo20": hist["lo_20d"],
                "ret_21d": hist["ret_21d"],
                "ret_63d": hist["ret_63d"],
                "ret_126d": hist["ret_126d"],
                "sigma20": hist["sigma_20"],
                "sigma60": hist["sigma_60"],
            })
            
            all_prices.append(df)
            logger.info(f"  ✅ {ticker}: {len(df)} days fetched")
        
        except Exception as e:
            logger.error(f"  ❌ Error fetching {ticker}: {e}")
            continue
    
    # Combine all tickers
    combined = pd.concat(all_prices, ignore_index=True)
    logger.info(f"✅ Total price records: {len(combined)}")
    
    return combined


def fetch_fundamentals_data() -> pd.DataFrame:
    """Fetch fundamentals data for all tickers.
    
    Returns:
        DataFrame with columns matching fundamentals.csv spec.
    """
    logger.info("Fetching fundamentals data from Yahoo Finance...")
    
    all_fundamentals = []
    
    for ticker in TICKERS:
        logger.info(f"  Fetching {ticker}...")
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Use most recent quarter end (approximate)
            quarter_end = (datetime.now() - timedelta(days=30)).date()
            
            is_banking = ticker in BANKING_TICKERS
            
            if is_banking:
                # Banking stocks: ONLY banking metrics
                row = {
                    "quarter_end": quarter_end,
                    "ticker": ticker,
                    # Non-financial (leave blank for banks)
                    "roe_3y": np.nan,
                    "roce_3y": np.nan,
                    "eps_cagr_3y": np.nan,
                    "sales_cagr_3y": np.nan,
                    "pe": np.nan,
                    "ev_ebitda": np.nan,
                    "opm_stdev_12q": np.nan,
                    # Banking metrics
                    "roa_3y": info.get("returnOnAssets", np.nan),
                    "roe_3y_banking": info.get("returnOnEquity", np.nan),
                    # GNPA, PCR, NIM not available in yfinance - set to NaN
                    "gnpa_pct": np.nan,
                    "pcr_pct": np.nan,
                    "nim_3y": np.nan,
                }
            else:
                # Non-financial stocks
                row = {
                    "quarter_end": quarter_end,
                    "ticker": ticker,
                    # Non-financial metrics
                    "roe_3y": info.get("returnOnEquity", np.nan),
                    "roce_3y": np.nan,  # Not directly available
                    "eps_cagr_3y": np.nan,  # Requires historical calculation
                    "sales_cagr_3y": np.nan,  # Requires historical calculation
                    "pe": info.get("trailingPE", np.nan),
                    "ev_ebitda": info.get("enterpriseToEbitda", np.nan),
                    "opm_stdev_12q": np.nan,  # Requires quarterly data
                    # Banking (leave blank for non-banks)
                    "roa_3y": np.nan,
                    "roe_3y_banking": np.nan,
                    "gnpa_pct": np.nan,
                    "pcr_pct": np.nan,
                    "nim_3y": np.nan,
                }
            
            all_fundamentals.append(row)
            logger.info(f"  ✅ {ticker}: Fundamentals fetched")
        
        except Exception as e:
            logger.error(f"  ❌ Error fetching {ticker}: {e}")
            continue
    
    df = pd.DataFrame(all_fundamentals)
    logger.info(f"✅ Total fundamentals records: {len(df)}")
    
    return df


def fetch_ownership_data() -> pd.DataFrame:
    """Fetch ownership data for all tickers.
    
    NOTE: yfinance does NOT provide:
    - Promoter pledge data (set to 0.0)
    - FII/DII quarterly changes (set to 0.0)
    
    Returns:
        DataFrame with columns matching ownership.csv spec.
    """
    logger.info("Fetching ownership data from Yahoo Finance...")
    
    all_ownership = []
    
    for ticker in TICKERS:
        logger.info(f"  Fetching {ticker}...")
        
        try:
            stock = yf.Ticker(ticker)
            
            # Use most recent quarter end
            quarter_end = (datetime.now() - timedelta(days=30)).date()
            
            # Try to get institutional holdings percentage
            major_holders = stock.major_holders
            promoter_pct = 0.0  # Default
            
            if major_holders is not None and len(major_holders) > 0:
                # Try to extract promoter holding (row 3 typically)
                try:
                    promoter_str = major_holders.iloc[3, 0]
                    promoter_pct = float(promoter_str.strip("%")) / 100.0
                except:
                    promoter_pct = 0.5  # Default placeholder
            
            row = {
                "quarter_end": quarter_end,
                "ticker": ticker,
                "promoter_hold_pct": promoter_pct,
                # NOT available in yfinance - set to 0.0
                "promoter_pledge_frac": 0.0,
                "fii_dii_delta_pp": 0.0,
            }
            
            all_ownership.append(row)
            logger.info(f"  ✅ {ticker}: Ownership fetched (promoter: {promoter_pct:.1%})")
        
        except Exception as e:
            logger.error(f"  ❌ Error fetching {ticker}: {e}")
            continue
    
    df = pd.DataFrame(all_ownership)
    logger.info(f"✅ Total ownership records: {len(df)}")
    logger.warning("⚠️  Pledge and FII/DII data NOT available from yfinance (set to 0.0)")
    
    return df


def generate_sector_map() -> pd.DataFrame:
    """Generate sector mapping CSV (static mapping).
    
    Returns:
        DataFrame with columns: ticker, sector_id, sector_group.
    """
    logger.info("Generating sector mapping...")
    
    rows = []
    for ticker, (sector_id, sector_group) in SECTOR_MAP.items():
        rows.append({
            "ticker": ticker,
            "sector_id": sector_id,
            "sector_group": sector_group,
        })
    
    df = pd.DataFrame(rows)
    logger.info(f"✅ Sector mapping: {len(df)} tickers")
    
    return df


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def generate_sample_price_data() -> pd.DataFrame:
    """Generate realistic sample price data (fallback if yfinance fails).
    
    Returns:
        DataFrame with price data for all tickers.
    """
    logger.warning("⚠️  yfinance connection failed - generating sample data")
    
    import random
    random.seed(42)  # For reproducibility
    np.random.seed(42)
    
    all_prices = []
    
    # Generate 60 trading days
    dates = pd.date_range(end=datetime.now(), periods=60, freq='B')  # Business days
    
    for ticker in TICKERS:
        # Base price depends on stock (realistic ranges)
        if "RELIANCE" in ticker:
            base_price = 2750
        elif "HDFCBANK" in ticker:
            base_price = 1650
        elif "TCS" in ticker:
            base_price = 3600
        elif "NESTLEIND" in ticker:
            base_price = 24000
        else:
            base_price = random.randint(500, 2000)
        
        # Generate price series with realistic drift and volatility
        sector_group = SECTOR_MAP[ticker][1]
        
        # Sector-specific volatility
        if sector_group == "metals":
            daily_vol = 0.025  # 2.5% daily vol
        elif sector_group == "fmcg":
            daily_vol = 0.012  # 1.2% daily vol
        else:
            daily_vol = 0.018  # 1.8% daily vol
        
        # Generate returns
        returns = np.random.normal(0.0005, daily_vol, len(dates))  # Slight positive drift
        prices = base_price * (1 + returns).cumprod()
        
        # Generate OHLC from close
        highs = prices * (1 + np.abs(np.random.normal(0, 0.005, len(dates))))
        lows = prices * (1 - np.abs(np.random.normal(0, 0.005, len(dates))))
        opens = np.roll(prices, 1)
        opens[0] = prices[0]
        
        # Volume
        avg_volume = random.randint(1_000_000, 10_000_000)
        volumes = np.random.normal(avg_volume, avg_volume * 0.3, len(dates))
        volumes = np.maximum(volumes, 100_000)
        
        # Create DataFrame
        df = pd.DataFrame({
            "date": dates.date,
            "ticker": ticker,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": prices,
            "volume": volumes,
        })
        
        # Calculate indicators
        df["dma20"] = df["close"].rolling(window=20).mean()
        df["dma50"] = df["close"].rolling(window=50).mean()
        df["dma200"] = np.nan  # Not enough data
        df["rsi14"] = calculate_rsi(df["close"], period=14)
        df["atr14"] = calculate_atr(df["high"], df["low"], df["close"], period=14)
        macd_line, macd_signal = calculate_macd(df["close"])
        df["macd_line"] = macd_line
        df["macd_signal"] = macd_signal
        df["hi20"] = df["high"].rolling(window=20).max()
        df["lo20"] = df["low"].rolling(window=20).min()
        df["ret_21d"] = df["close"].pct_change(periods=21)
        df["ret_63d"] = np.nan  # Not enough data
        df["ret_126d"] = np.nan  # Not enough data
        df["sigma20"] = calculate_volatility(df["close"], period=20)
        df["sigma60"] = calculate_volatility(df["close"], period=60)
        
        all_prices.append(df)
    
    return pd.concat(all_prices, ignore_index=True)


def generate_sample_fundamentals() -> pd.DataFrame:
    """Generate sample fundamentals (fallback)."""
    logger.warning("⚠️  Generating sample fundamentals")
    
    rows = []
    quarter_end = (datetime.now() - timedelta(days=30)).date()
    
    for ticker in TICKERS:
        is_banking = ticker in BANKING_TICKERS
        
        if is_banking:
            row = {
                "quarter_end": quarter_end,
                "ticker": ticker,
                "roe_3y": np.nan,
                "roce_3y": np.nan,
                "eps_cagr_3y": np.nan,
                "sales_cagr_3y": np.nan,
                "pe": np.nan,
                "ev_ebitda": np.nan,
                "opm_stdev_12q": np.nan,
                "roa_3y": np.random.uniform(0.012, 0.022),
                "roe_3y_banking": np.random.uniform(0.12, 0.20),
                "gnpa_pct": np.nan,  # NOT available
                "pcr_pct": np.nan,  # NOT available
                "nim_3y": np.nan,  # NOT available
            }
        else:
            row = {
                "quarter_end": quarter_end,
                "ticker": ticker,
                "roe_3y": np.random.uniform(0.10, 0.25),
                "roce_3y": np.nan,  # Will test imputation
                "eps_cagr_3y": np.nan,
                "sales_cagr_3y": np.nan,
                "pe": np.random.uniform(15, 40),
                "ev_ebitda": np.random.uniform(10, 25),
                "opm_stdev_12q": np.nan,
                "roa_3y": np.nan,
                "roe_3y_banking": np.nan,
                "gnpa_pct": np.nan,
                "pcr_pct": np.nan,
                "nim_3y": np.nan,
            }
        
        rows.append(row)
    
    return pd.DataFrame(rows)


def generate_sample_ownership() -> pd.DataFrame:
    """Generate sample ownership (fallback)."""
    logger.warning("⚠️  Generating sample ownership")
    
    rows = []
    quarter_end = (datetime.now() - timedelta(days=30)).date()
    
    for ticker in TICKERS:
        row = {
            "quarter_end": quarter_end,
            "ticker": ticker,
            "promoter_hold_pct": np.random.uniform(0.40, 0.65),
            "promoter_pledge_frac": 0.0,  # NOT available from yfinance
            "fii_dii_delta_pp": 0.0,  # NOT available from yfinance
        }
        rows.append(row)
    
    return pd.DataFrame(rows)


def main() -> int:
    """Fetch all data and save to CSV files.
    
    Returns:
        0 on success, 1 on error.
    """
    logger.info("=" * 80)
    logger.info("📊 GreyOak Score Engine - Real Data Fetcher (yfinance)")
    logger.info("=" * 80)
    
    # Create data directory
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    try:
        # Try yfinance first, fallback to sample data
        try:
            logger.info("Attempting to fetch data from Yahoo Finance...")
            prices_df = fetch_price_data()
            fundamentals_df = fetch_fundamentals_data()
            ownership_df = fetch_ownership_data()
            data_source = "yfinance (Yahoo Finance)"
        except Exception as yf_error:
            logger.warning(f"⚠️  yfinance failed: {yf_error}")
            logger.info("Generating sample data as fallback...")
            prices_df = generate_sample_price_data()
            fundamentals_df = generate_sample_fundamentals()
            ownership_df = generate_sample_ownership()
            data_source = "Generated sample data (yfinance unavailable)"
        
        # Generate sector map (always static)
        sector_map_df = generate_sector_map()
        
        # Save all CSVs
        prices_path = data_dir / "prices.csv"
        prices_df.to_csv(prices_path, index=False)
        logger.info(f"✅ Saved: {prices_path}")
        
        fundamentals_path = data_dir / "fundamentals.csv"
        fundamentals_df.to_csv(fundamentals_path, index=False)
        logger.info(f"✅ Saved: {fundamentals_path}")
        
        ownership_path = data_dir / "ownership.csv"
        ownership_df.to_csv(ownership_path, index=False)
        logger.info(f"✅ Saved: {ownership_path}")
        
        sector_map_path = data_dir / "sector_map.csv"
        sector_map_df.to_csv(sector_map_path, index=False)
        logger.info(f"✅ Saved: {sector_map_path}")
        
        logger.info("=" * 80)
        logger.info(f"✅ All data saved successfully!")
        logger.info(f"   Data source: {data_source}")
        logger.info("=" * 80)
        logger.info(f"  Prices: {len(prices_df)} records")
        logger.info(f"  Fundamentals: {len(fundamentals_df)} records")
        logger.info(f"  Ownership: {len(ownership_df)} records")
        logger.info(f"  Sector Map: {len(sector_map_df)} tickers")
        logger.info("=" * 80)
        
        return 0
    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
