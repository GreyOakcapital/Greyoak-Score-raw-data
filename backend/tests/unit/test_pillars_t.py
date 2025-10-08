"""Unit tests for Technicals (T) Pillar."""

import pandas as pd
import pytest
from unittest.mock import Mock

from greyoak_score.pillars.technicals import TechnicalsPillar
from greyoak_score.core.config_manager import ConfigManager


class TestTechnicalsPillar:
    """Test Technicals pillar calculation."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration manager."""
        config = Mock(spec=ConfigManager)
        
        # Mock technicals configuration
        config.get_technicals_config.return_value = {
            "weights": {
                "above_200": 0.20,
                "golden_cross": 0.15,
                "rsi": 0.20,
                "breakout": 0.25,
                "volume": 0.20
            },
            "rsi_bands": {
                "oversold": 30,
                "overbought": 70
            },
            "breakout": {
                "atr_multiplier": 0.75,
                "close_pct": 0.01
            }
        }
        
        return config

    @pytest.fixture
    def pillar(self, mock_config):
        """Create TechnicalsPillar instance."""
        return TechnicalsPillar(mock_config)

    @pytest.fixture
    def sample_prices_technical(self):
        """Sample price data with technical indicators."""
        return pd.DataFrame({
            'ticker': ['RELIANCE', 'TCS', 'INFY'],
            'trading_date': pd.to_datetime(['2024-01-15', '2024-01-15', '2024-01-15']),
            'close': [2500, 3400, 1600],
            'volume': [5000000, 2000000, 3000000],
            'dma20': [2480, 3380, 1580],
            'dma50': [2450, 3350, 1550],
            'dma200': [2400, 3300, 1520],
            'rsi14': [65, 45, 75],
            'atr14': [50, 80, 60],
            'hi20': [2520, 3420, 1620],
            'lo20': [2400, 3300, 1500]
        })

    @pytest.fixture
    def sample_prices_history(self):
        """Sample price history for volume calculation."""
        dates = pd.date_range('2024-01-01', '2024-01-15', freq='D')
        data = []
        
        for ticker in ['RELIANCE', 'TCS', 'INFY']:
            for i, date in enumerate(dates):
                # Base volumes with some variation
                base_volumes = {'RELIANCE': 3000000, 'TCS': 1500000, 'INFY': 2000000}
                volume = base_volumes[ticker] * (0.8 + 0.4 * (i % 3) / 2)  # Vary 0.8-1.2x
                
                data.append({
                    'ticker': ticker,
                    'trading_date': date,
                    'close': [2500, 3400, 1600][['RELIANCE', 'TCS', 'INFY'].index(ticker)],
                    'volume': volume,
                    'dma20': [2480, 3380, 1580][['RELIANCE', 'TCS', 'INFY'].index(ticker)],
                    'dma50': [2450, 3350, 1550][['RELIANCE', 'TCS', 'INFY'].index(ticker)],
                    'dma200': [2400, 3300, 1520][['RELIANCE', 'TCS', 'INFY'].index(ticker)],
                    'rsi14': [65, 45, 75][['RELIANCE', 'TCS', 'INFY'].index(ticker)],
                    'atr14': [50, 80, 60][['RELIANCE', 'TCS', 'INFY'].index(ticker)],
                    'hi20': [2520, 3420, 1620][['RELIANCE', 'TCS', 'INFY'].index(ticker)],
                    'lo20': [2400, 3300, 1500][['RELIANCE', 'TCS', 'INFY'].index(ticker)]
                })
        
        return pd.DataFrame(data)

    @pytest.fixture
    def sample_sector_map(self):
        """Sample sector mapping."""
        return pd.DataFrame({
            'ticker': ['RELIANCE', 'TCS', 'INFY'],
            'sector_group': ['diversified', 'it', 'it']
        })

    @pytest.fixture
    def empty_fundamentals(self):
        """Empty fundamentals data."""
        return pd.DataFrame(columns=['ticker', 'quarter_end'])

    @pytest.fixture
    def empty_ownership(self):
        """Empty ownership data."""
        return pd.DataFrame(columns=['ticker', 'quarter_end'])

    def test_pillar_name(self, pillar):
        """Test pillar name property."""
        assert pillar.pillar_name == "T"

    def test_basic_technicals_scoring(self, pillar, sample_prices_history, 
                                    sample_sector_map, empty_fundamentals, empty_ownership):
        """Test basic technicals scoring with full price history."""
        result = pillar.calculate(
            sample_prices_history,
            empty_fundamentals,
            empty_ownership,
            sample_sector_map
        )
        
        # Check structure
        assert len(result) == 3
        assert set(result.columns) == {'ticker', 'T_score', 'T_details'}
        
        # Check all tickers present
        assert set(result['ticker']) == {'RELIANCE', 'TCS', 'INFY'}
        
        # Check scores are valid (0-100)
        for score in result['T_score']:
            assert 0 <= score <= 100
        
        # Check details structure
        for details in result['T_details']:
            assert 'components' in details
            assert 'final_score' in details
            assert 'config_used' in details
            
            # Check all 5 components present
            components = details['components']
            expected_components = ['above_200', 'golden_cross', 'rsi', 'breakout', 'volume']
            assert set(components.keys()) == set(expected_components)
            
            # Check component structure
            for comp_name, comp_data in components.items():
                assert 'score' in comp_data
                assert 'weight' in comp_data
                assert 0 <= comp_data['score'] <= 100

    def test_above_200_component(self, pillar, sample_sector_map, empty_fundamentals, empty_ownership):
        """Test Above200 component calculation."""
        # Test data with different close vs DMA200 relationships
        prices = pd.DataFrame({
            'ticker': ['ABOVE', 'BELOW', 'MISSING'],
            'trading_date': pd.to_datetime(['2024-01-15'] * 3),
            'close': [2500, 2300, 2400],
            'volume': [1000000] * 3,
            'dma20': [2400] * 3,
            'dma50': [2350] * 3,
            'dma200': [2400, 2400, None],  # ABOVE > 2400, BELOW < 2400, MISSING = NaN
            'rsi14': [50] * 3,
            'atr14': [30] * 3,
            'hi20': [2450] * 3,
            'lo20': [2350] * 3
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['ABOVE', 'BELOW', 'MISSING'],
            'sector_group': ['test'] * 3
        })
        
        result = pillar.calculate(prices, empty_fundamentals, empty_ownership, sector_map)
        
        # Check Above200 scores
        for _, row in result.iterrows():
            ticker = row['ticker']
            above_200_score = row['T_details']['components']['above_200']['score']
            
            if ticker == 'ABOVE':
                assert above_200_score == 100.0  # close > dma200
            elif ticker == 'BELOW':
                assert above_200_score == 0.0    # close < dma200
            elif ticker == 'MISSING':
                assert above_200_score == 0.0    # missing dma200

    def test_golden_cross_component(self, pillar, sample_sector_map, empty_fundamentals, empty_ownership):
        """Test GoldenCross component calculation."""
        # Test data with different DMA relationships
        prices = pd.DataFrame({
            'ticker': ['GOLDEN', 'DEATH', 'MISSING'],
            'trading_date': pd.to_datetime(['2024-01-15'] * 3),
            'close': [2500] * 3,
            'volume': [1000000] * 3,
            'dma20': [2450, 2350, None],  # GOLDEN: 2450 > 2400, DEATH: 2350 < 2400
            'dma50': [2400, 2400, 2400],
            'dma200': [2300] * 3,
            'rsi14': [50] * 3,
            'atr14': [30] * 3,
            'hi20': [2450] * 3,
            'lo20': [2350] * 3
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['GOLDEN', 'DEATH', 'MISSING'],
            'sector_group': ['test'] * 3
        })
        
        result = pillar.calculate(prices, empty_fundamentals, empty_ownership, sector_map)
        
        # Check GoldenCross scores
        for _, row in result.iterrows():
            ticker = row['ticker']
            golden_cross_score = row['T_details']['components']['golden_cross']['score']
            
            if ticker == 'GOLDEN':
                assert golden_cross_score == 100.0  # dma20 > dma50
            elif ticker == 'DEATH':
                assert golden_cross_score == 0.0    # dma20 < dma50
            elif ticker == 'MISSING':
                assert golden_cross_score == 0.0    # missing dma20

    def test_rsi_component(self, pillar, sample_sector_map, empty_fundamentals, empty_ownership):
        """Test RSI component calculation."""
        # Test RSI at different levels
        prices = pd.DataFrame({
            'ticker': ['OVERSOLD', 'NEUTRAL', 'OVERBOUGHT', 'MISSING'],
            'trading_date': pd.to_datetime(['2024-01-15'] * 4),
            'close': [2500] * 4,
            'volume': [1000000] * 4,
            'dma20': [2400] * 4,
            'dma50': [2350] * 4,
            'dma200': [2300] * 4,
            'rsi14': [20, 50, 80, None],  # Oversold, neutral, overbought, missing
            'atr14': [30] * 4,
            'hi20': [2450] * 4,
            'lo20': [2350] * 4
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['OVERSOLD', 'NEUTRAL', 'OVERBOUGHT', 'MISSING'],
            'sector_group': ['test'] * 4
        })
        
        result = pillar.calculate(prices, empty_fundamentals, empty_ownership, sector_map)
        
        # Check RSI scores
        for _, row in result.iterrows():
            ticker = row['ticker']
            rsi_score = row['T_details']['components']['rsi']['score']
            
            if ticker == 'OVERSOLD':
                assert rsi_score == 0.0     # RSI 20 <= 30 (oversold)
            elif ticker == 'NEUTRAL':
                assert rsi_score == 50.0    # RSI 50 is middle of 30-70 range
            elif ticker == 'OVERBOUGHT':
                assert rsi_score == 100.0   # RSI 80 >= 70 (overbought)
            elif ticker == 'MISSING':
                assert rsi_score == 50.0    # Missing RSI defaults to neutral

    def test_breakout_component(self, pillar, sample_sector_map, empty_fundamentals, empty_ownership):
        """Test Breakout component calculation."""
        # Test breakout scenarios
        prices = pd.DataFrame({
            'ticker': ['BREAKOUT', 'NO_BREAKOUT', 'MISSING'],
            'trading_date': pd.to_datetime(['2024-01-15'] * 3),
            'close': [2500, 2400, 2450],
            'volume': [1000000] * 3,
            'dma20': [2450, 2450, None],
            'dma50': [2400] * 3,
            'dma200': [2350] * 3,
            'rsi14': [60] * 3,
            'atr14': [40, 40, None],  # ATR for threshold calculation
            'hi20': [2450, 2450, 2450],  # 20-day high
            'lo20': [2350] * 3
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['BREAKOUT', 'NO_BREAKOUT', 'MISSING'],
            'sector_group': ['test'] * 3
        })
        
        result = pillar.calculate(prices, empty_fundamentals, empty_ownership, sector_map)
        
        # Check breakout scores
        for _, row in result.iterrows():
            ticker = row['ticker']
            breakout_score = row['T_details']['components']['breakout']['score']
            
            # All should be numeric and in valid range
            assert 0 <= breakout_score <= 100
            
            if ticker == 'BREAKOUT':
                # close=2500 vs resistance=max(2450,2450)=2450, gap=50
                # threshold=max(0.75*40, 0.01*2500)=max(30,25)=30
                # score = min(100, 50/30*100) = 100
                assert breakout_score == 100.0
            elif ticker == 'NO_BREAKOUT':
                # close=2400 vs resistance=2450, gap=0 (no breakout)
                assert breakout_score == 0.0
            elif ticker == 'MISSING':
                # Missing ATR data
                assert breakout_score == 0.0

    def test_volume_component_with_history(self, pillar, sample_prices_history, 
                                         sample_sector_map, empty_fundamentals, empty_ownership):
        """Test Volume component with price history."""
        # Modify latest day to have high volume
        modified_history = sample_prices_history.copy()
        
        # Set RELIANCE's latest volume to be 3x normal (high volume surprise)
        latest_date = modified_history['trading_date'].max()
        reliance_mask = (modified_history['ticker'] == 'RELIANCE') & (modified_history['trading_date'] == latest_date)
        avg_reliance_volume = modified_history[modified_history['ticker'] == 'RELIANCE']['volume'].mean()
        modified_history.loc[reliance_mask, 'volume'] = avg_reliance_volume * 3.0
        
        result = pillar.calculate(modified_history, empty_fundamentals, empty_ownership, sample_sector_map)
        
        # Check volume scores
        reliance_result = result[result['ticker'] == 'RELIANCE'].iloc[0]
        volume_score = reliance_result['T_details']['components']['volume']['score']
        
        # Should have high volume score due to 3x volume spike
        assert volume_score >= 80.0  # Should be near 100 for 3x ratio

    def test_missing_technical_data(self, pillar, sample_sector_map, empty_fundamentals, empty_ownership):
        """Test handling of missing technical data."""
        # Price data missing required technical columns
        incomplete_prices = pd.DataFrame({
            'ticker': ['TEST'],
            'trading_date': pd.to_datetime(['2024-01-15']),
            'close': [2500],
            'volume': [1000000]
            # Missing technical indicators
        })
        
        with pytest.raises(ValueError, match="Missing required technical columns"):
            pillar.calculate(incomplete_prices, empty_fundamentals, empty_ownership, sample_sector_map)

    def test_single_day_data(self, pillar, sample_prices_technical, 
                           sample_sector_map, empty_fundamentals, empty_ownership):
        """Test technicals calculation with single day of data."""
        result = pillar.calculate(
            sample_prices_technical,
            empty_fundamentals,
            empty_ownership,
            sample_sector_map
        )
        
        # Should complete successfully even with single day
        assert len(result) == 3
        
        # Volume scores should default to neutral (50) due to insufficient history
        for _, row in result.iterrows():
            volume_score = row['T_details']['components']['volume']['score']
            assert volume_score == 50.0  # Neutral due to insufficient history

    def test_component_weights_sum_correctly(self, pillar, sample_prices_technical,
                                           sample_sector_map, empty_fundamentals, empty_ownership):
        """Test that component weights sum to 1.0."""
        result = pillar.calculate(
            sample_prices_technical,
            empty_fundamentals,
            empty_ownership,
            sample_sector_map
        )
        
        # Check weights sum for each stock
        for _, row in result.iterrows():
            components = row['T_details']['components']
            total_weight = sum(comp['weight'] for comp in components.values())
            assert abs(total_weight - 1.0) < 1e-10  # Should sum to 1.0

    def test_extreme_values_handled(self, pillar, sample_sector_map, empty_fundamentals, empty_ownership):
        """Test handling of extreme technical indicator values."""
        # Extreme values
        prices = pd.DataFrame({
            'ticker': ['EXTREME'],
            'trading_date': pd.to_datetime(['2024-01-15']),
            'close': [1000],
            'volume': [999999999],  # Very high volume
            'dma20': [900],
            'dma50': [800],
            'dma200': [700],
            'rsi14': [0],    # Extreme RSI
            'atr14': [500],  # Very high ATR
            'hi20': [950],
            'lo20': [750]
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['EXTREME'],
            'sector_group': ['test']
        })
        
        result = pillar.calculate(prices, empty_fundamentals, empty_ownership, sector_map)
        
        # Should complete without errors
        assert len(result) == 1
        
        # All component scores should be valid
        components = result.iloc[0]['T_details']['components']
        for comp_name, comp_data in components.items():
            assert 0 <= comp_data['score'] <= 100