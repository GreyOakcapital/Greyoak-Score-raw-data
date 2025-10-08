"""Unit tests for technical indicators module."""

import numpy as np
import pandas as pd
import pytest
from datetime import date

from greyoak_score.data.indicators import (
    calculate_rsi,
    calculate_atr,
    calculate_macd,
    calculate_volatility,
    add_missing_indicators,
)


class TestRSI:
    """Test RSI calculation."""

    def test_rsi_calculation_basic(self):
        """Test RSI calculation with simple price series."""
        # Create a simple price series with known patterns
        prices = pd.Series([100, 105, 102, 108, 104, 110, 107, 112])
        
        rsi = calculate_rsi(prices, period=6)
        
        # RSI should be between 0 and 100
        assert rsi.min() >= 0
        assert rsi.max() <= 100
        
        # Should have NaN for first few values (warmup period)
        assert pd.isna(rsi.iloc[0])
        
        # Last value should be valid
        assert not pd.isna(rsi.iloc[-1])

    def test_rsi_uptrend(self):
        """Test RSI in strong uptrend should be high."""
        # Strong uptrend
        prices = pd.Series([100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120, 122, 124, 126, 128])
        
        rsi = calculate_rsi(prices, period=14)
        
        # In strong uptrend, RSI should be high (>70 typically overbought)
        assert rsi.iloc[-1] > 70

    def test_rsi_downtrend(self):
        """Test RSI in strong downtrend should be low."""
        # Strong downtrend
        prices = pd.Series([128, 126, 124, 122, 120, 118, 116, 114, 112, 110, 108, 106, 104, 102, 100])
        
        rsi = calculate_rsi(prices, period=14)
        
        # In strong downtrend, RSI should be low (<30 typically oversold)
        assert rsi.iloc[-1] < 30

    def test_rsi_zero_gains_protection(self):
        """Test RSI handles zero gains correctly (division by zero protection)."""
        # Flat prices (no movement)
        prices = pd.Series([100] * 20)
        
        rsi = calculate_rsi(prices, period=14)
        
        # RSI should be 0 when no movement (no gains or losses)
        assert rsi.iloc[-1] == 0.0 or pd.isna(rsi.iloc[-1])


class TestATR:
    """Test ATR calculation."""

    def test_atr_calculation_basic(self):
        """Test basic ATR calculation."""
        # Create sample OHLC data
        df = pd.DataFrame({
            'high': [102, 104, 101, 106, 108],
            'low': [98, 101, 96, 102, 105],
            'close': [100, 103, 98, 105, 107],
        })
        
        atr = calculate_atr(df['high'], df['low'], df['close'], period=3)
        
        # ATR should be positive
        assert (atr >= 0).all()
        
        # Should have NaN for first value
        assert pd.isna(atr.iloc[0])
        
        # Last values should be valid
        assert not pd.isna(atr.iloc[-1])

    def test_atr_high_volatility(self):
        """Test ATR is higher for volatile periods."""
        # High volatility OHLC
        volatile_data = {
            'high': [110, 120, 105, 130, 125],
            'low': [90, 95, 80, 110, 100],
            'close': [100, 115, 85, 125, 115],
        }
        
        # Low volatility OHLC
        stable_data = {
            'high': [101, 102, 101, 102, 101],
            'low': [99, 100, 99, 100, 99],
            'close': [100, 101, 100, 101, 100],
        }
        
        atr_volatile = calculate_atr(
            pd.Series(volatile_data['high']),
            pd.Series(volatile_data['low']),
            pd.Series(volatile_data['close']),
            period=3
        )
        
        atr_stable = calculate_atr(
            pd.Series(stable_data['high']),
            pd.Series(stable_data['low']),
            pd.Series(stable_data['close']),
            period=3
        )
        
        # Volatile period should have higher ATR
        assert atr_volatile.iloc[-1] > atr_stable.iloc[-1]


class TestMACD:
    """Test MACD calculation."""

    def test_macd_calculation_basic(self):
        """Test basic MACD calculation."""
        # Create trending price series
        prices = pd.Series(range(100, 150))  # Uptrend
        
        macd_line, signal_line = calculate_macd(prices, fast=5, slow=10, signal=3)
        
        # Should return two series
        assert isinstance(macd_line, pd.Series)
        assert isinstance(signal_line, pd.Series)
        
        # Series should be same length
        assert len(macd_line) == len(signal_line) == len(prices)
        
        # Initial values should be NaN (warmup)
        assert pd.isna(macd_line.iloc[0])
        assert pd.isna(signal_line.iloc[0])

    def test_macd_uptrend(self):
        """Test MACD behavior in uptrend."""
        # Strong uptrend
        prices = pd.Series(np.linspace(100, 150, 50))
        
        macd_line, signal_line = calculate_macd(prices)
        
        # In uptrend, MACD line should generally be above signal line
        # Check last few values (after warmup)
        assert macd_line.iloc[-1] > signal_line.iloc[-1]


class TestVolatility:
    """Test volatility calculation."""

    def test_volatility_calculation(self):
        """Test volatility calculation."""
        # Create price series with known volatility characteristics
        prices = pd.Series([100, 102, 98, 105, 95, 110, 90, 115])
        
        volatility = calculate_volatility(prices, period=5)
        
        # Volatility should be non-negative
        assert (volatility >= 0).all()
        
        # Should have NaN for first few values
        assert pd.isna(volatility.iloc[0])
        
        # Should have valid values after warmup
        assert not pd.isna(volatility.iloc[-1])

    def test_volatility_comparison(self):
        """Test that higher price variation gives higher volatility."""
        # Stable prices
        stable_prices = pd.Series([100 + i * 0.1 for i in range(20)])
        
        # Volatile prices
        volatile_prices = pd.Series([100 + 10 * np.sin(i) for i in range(20)])
        
        vol_stable = calculate_volatility(stable_prices, period=10)
        vol_volatile = calculate_volatility(volatile_prices, period=10)
        
        # Volatile series should have higher volatility
        assert vol_volatile.iloc[-1] > vol_stable.iloc[-1]


class TestAddMissingIndicators:
    """Test the main function for adding missing indicators."""

    def test_add_indicators_basic(self):
        """Test adding indicators to basic OHLCV DataFrame."""
        # Create sample OHLCV data
        df = pd.DataFrame({
            'ticker': ['RELIANCE'] * 30,
            'date': pd.date_range('2024-01-01', periods=30),
            'open': np.random.uniform(2400, 2500, 30),
            'high': np.random.uniform(2450, 2550, 30),
            'low': np.random.uniform(2350, 2450, 30),
            'close': np.random.uniform(2400, 2500, 30),
            'volume': np.random.uniform(1000000, 5000000, 30),
        })
        
        # Ensure high >= low
        df['high'] = np.maximum(df['high'], df['low'])
        df['close'] = np.clip(df['close'], df['low'], df['high'])
        df['open'] = np.clip(df['open'], df['low'], df['high'])
        
        result = add_missing_indicators(df)
        
        # Should add all missing indicators
        expected_cols = [
            'dma20', 'dma50', 'dma200', 'rsi14', 'atr14',
            'macd_line', 'macd_signal', 'hi20', 'lo20',
            'ret_21d', 'ret_63d', 'ret_126d', 'sigma20', 'sigma60'
        ]
        
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"
        
        # Should preserve original data
        assert len(result) == len(df)
        assert (result['ticker'] == df['ticker']).all()

    def test_add_indicators_multiple_tickers(self):
        """Test adding indicators for multiple tickers."""
        tickers = ['RELIANCE', 'TCS', 'INFY']
        data = []
        
        for ticker in tickers:
            ticker_data = {
                'ticker': [ticker] * 25,
                'date': pd.date_range('2024-01-01', periods=25),
                'open': np.random.uniform(100, 200, 25),
                'high': np.random.uniform(150, 250, 25),
                'low': np.random.uniform(50, 150, 25),
                'close': np.random.uniform(100, 200, 25),
                'volume': np.random.uniform(100000, 1000000, 25),
            }
            data.append(pd.DataFrame(ticker_data))
        
        df = pd.concat(data, ignore_index=True)
        
        # Fix OHLC relationships
        df['high'] = np.maximum(df['high'], df['low'])
        df['close'] = np.clip(df['close'], df['low'], df['high'])
        df['open'] = np.clip(df['open'], df['low'], df['high'])
        
        result = add_missing_indicators(df)
        
        # Should have indicators for all tickers
        assert len(result) == len(df)
        assert set(result['ticker'].unique()) == set(tickers)
        
        # Each ticker should have indicators
        for ticker in tickers:
            ticker_data = result[result['ticker'] == ticker]
            assert not ticker_data['dma20'].isna().all()
            assert not ticker_data['rsi14'].isna().all()

    def test_skip_existing_indicators(self):
        """Test that existing indicators are not overwritten."""
        df = pd.DataFrame({
            'ticker': ['TEST'] * 20,
            'date': pd.date_range('2024-01-01', periods=20),
            'open': [100] * 20,
            'high': [105] * 20,
            'low': [95] * 20,
            'close': [100] * 20,
            'volume': [1000000] * 20,
            'dma20': [99.5] * 20,  # Pre-existing indicator
        })
        
        result = add_missing_indicators(df)
        
        # Pre-existing indicator should be preserved
        assert (result['dma20'] == 99.5).all()

    def test_missing_required_columns(self):
        """Test error handling for missing required columns."""
        df = pd.DataFrame({
            'ticker': ['TEST'] * 10,
            'open': [100] * 10,
            # Missing other required columns
        })
        
        with pytest.raises(ValueError, match="Missing required columns"):
            add_missing_indicators(df)

    def test_proper_sorting(self):
        """Test that data is properly sorted by ticker and date."""
        # Create unsorted data
        df = pd.DataFrame({
            'ticker': ['B', 'A', 'B', 'A'] * 5,
            'date': pd.to_datetime(['2024-01-03', '2024-01-01', '2024-01-01', '2024-01-02'] * 5),
            'open': [100] * 20,
            'high': [105] * 20,
            'low': [95] * 20,
            'close': [100] * 20,
            'volume': [1000000] * 20,
        })
        
        result = add_missing_indicators(df)
        
        # Should be sorted by ticker, then date
        expected_order = result.groupby('ticker')['date'].apply(lambda x: x.is_monotonic_increasing)
        assert expected_order.all(), "Data should be sorted by date within each ticker"