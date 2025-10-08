"""Unit tests for Relative Strength (R) Pillar."""

import pandas as pd
import pytest
from unittest.mock import Mock
import numpy as np

from greyoak_score.pillars.relative_strength import RelativeStrengthPillar
from greyoak_score.core.config_manager import ConfigManager


class TestRelativeStrengthPillar:
    """Test Relative Strength pillar calculation."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration manager."""
        config = Mock(spec=ConfigManager)
        
        # Mock relative strength configuration
        config.get_relative_strength_config.return_value = {
            "horizon_weights": {
                "1M": 0.45,
                "3M": 0.35,
                "6M": 0.20
            },
            "alpha_weights": {
                "sector": 0.6,
                "market": 0.4
            }
        }
        
        return config

    @pytest.fixture
    def pillar(self, mock_config):
        """Create RelativeStrengthPillar instance."""
        return RelativeStrengthPillar(mock_config)

    @pytest.fixture
    def sample_prices_returns(self):
        """Sample price data with returns and volatility."""
        return pd.DataFrame({
            'ticker': ['WINNER', 'LOSER', 'NEUTRAL', 'VOLATILE'],
            'trading_date': pd.to_datetime(['2024-01-15'] * 4),
            'close': [1000, 900, 1050, 1100],
            
            # Returns (as decimals: 0.10 = 10%)
            'ret_21d': [0.15, -0.10, 0.05, 0.20],   # 1M returns
            'ret_63d': [0.25, -0.15, 0.08, 0.30],   # 3M returns
            'ret_126d': [0.35, -0.20, 0.12, 0.40],  # 6M returns
            
            # Volatility (daily)
            'sigma20': [0.02, 0.03, 0.025, 0.05],   # 20-day vol
            'sigma60': [0.025, 0.035, 0.03, 0.06]   # 60-day vol
        })

    @pytest.fixture
    def sample_sector_map(self):
        """Sample sector mapping."""
        return pd.DataFrame({
            'ticker': ['WINNER', 'LOSER', 'NEUTRAL', 'VOLATILE'],
            'sector_group': ['it', 'it', 'energy', 'metals']
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
        assert pillar.pillar_name == "R"

    def test_basic_relative_strength_scoring(self, pillar, sample_prices_returns,
                                           sample_sector_map, empty_fundamentals, empty_ownership):
        """Test basic relative strength scoring."""
        result = pillar.calculate(
            sample_prices_returns,
            empty_fundamentals,
            empty_ownership,
            sample_sector_map
        )
        
        # Check structure
        assert len(result) == 4
        assert set(result.columns) == {'ticker', 'R_score', 'R_details'}
        
        # Check all tickers present
        assert set(result['ticker']) == {'WINNER', 'LOSER', 'NEUTRAL', 'VOLATILE'}
        
        # Check scores are valid (0-100) - should be percentile ranks
        scores = result['R_score'].values
        assert all(0 <= score <= 100 for score in scores)
        
        # Since we have 4 stocks, percentile ranks should be roughly 25%, 50%, 75%, 100%
        sorted_scores = sorted(scores)
        assert len(set(sorted_scores)) > 1  # Should have different scores

    def test_alpha_calculation_details(self, pillar, sample_prices_returns,
                                     sample_sector_map, empty_fundamentals, empty_ownership):
        """Test detailed alpha calculation components."""
        result = pillar.calculate(
            sample_prices_returns,
            empty_fundamentals,
            empty_ownership,
            sample_sector_map
        )
        
        # Check details structure for one stock
        winner_result = result[result['ticker'] == 'WINNER'].iloc[0]
        details = winner_result['R_details']
        
        # Check required detail components
        assert 'weighted_alpha' in details
        assert 'horizon_alphas' in details
        assert 'horizon_details' in details
        assert 'percentile_rank' in details
        assert 'config_used' in details
        
        # Check horizon alphas
        horizon_alphas = details['horizon_alphas']
        assert set(horizon_alphas.keys()) == {'1M', '3M', '6M'}
        
        # Check horizon details
        horizon_details = details['horizon_details']
        for horizon in ['1M', '3M', '6M']:
            horizon_detail = horizon_details[horizon]
            
            # Should have all components of alpha calculation
            required_keys = [
                'stock_return', 'stock_volatility', 'sector_return', 'market_return',
                'sector_excess', 'market_excess', 'sector_alpha', 'market_alpha',
                'combined_alpha', 'alpha_weights'
            ]
            for key in required_keys:
                assert key in horizon_detail, f"Missing {key} in {horizon} details"

    def test_sector_benchmarks(self, pillar, sample_prices_returns,
                             sample_sector_map, empty_fundamentals, empty_ownership):
        """Test sector benchmark calculation."""
        # Call internal method to test sector benchmarks
        merged_data = pillar.merge_sector_data(sample_prices_returns, sample_sector_map)
        sector_benchmarks = pillar._calculate_sector_benchmarks(merged_data)
        
        # Check benchmark structure
        assert 'it' in sector_benchmarks  # Should have IT sector (WINNER, LOSER)
        assert 'energy' in sector_benchmarks  # Should have energy (NEUTRAL)
        assert 'metals' in sector_benchmarks  # Should have metals (VOLATILE)
        
        # Check IT sector benchmark (average of WINNER and LOSER)
        it_benchmarks = sector_benchmarks['it']
        assert set(it_benchmarks.keys()) == {'1M', '3M', '6M'}
        
        # For 1M: (0.15 + (-0.10)) / 2 = 0.025
        expected_1m = (0.15 + (-0.10)) / 2
        assert abs(it_benchmarks['1M'] - expected_1m) < 1e-10

    def test_market_benchmark(self, pillar, sample_prices_returns,
                            sample_sector_map, empty_fundamentals, empty_ownership):
        """Test market benchmark calculation."""
        # Call internal method to test market benchmark
        merged_data = pillar.merge_sector_data(sample_prices_returns, sample_sector_map)
        market_benchmark = pillar._calculate_market_benchmark(merged_data)
        
        # Check market benchmark structure
        assert set(market_benchmark.keys()) == {'1M', '3M', '6M'}
        
        # Market should be equal-weighted average of all stocks
        # For 1M: (0.15 + (-0.10) + 0.05 + 0.20) / 4 = 0.075
        expected_1m = (0.15 + (-0.10) + 0.05 + 0.20) / 4
        assert abs(market_benchmark['1M'] - expected_1m) < 1e-10

    def test_missing_return_data(self, pillar, sample_sector_map, empty_fundamentals, empty_ownership):
        """Test handling of missing return data."""
        # Price data missing return columns
        incomplete_prices = pd.DataFrame({
            'ticker': ['TEST'],
            'trading_date': pd.to_datetime(['2024-01-15']),
            'close': [1000]
            # Missing return and volatility columns
        })
        
        with pytest.raises(ValueError, match="Missing required return/volatility columns"):
            pillar.calculate(incomplete_prices, empty_fundamentals, empty_ownership, sample_sector_map)

    def test_missing_individual_returns(self, pillar, sample_sector_map, empty_fundamentals, empty_ownership):
        """Test handling when individual stocks have missing returns."""
        prices_with_missing = pd.DataFrame({
            'ticker': ['GOOD', 'BAD'],
            'trading_date': pd.to_datetime(['2024-01-15'] * 2),
            'close': [1000, 900],
            'ret_21d': [0.10, None],    # BAD has missing 1M return
            'ret_63d': [0.15, 0.05],
            'ret_126d': [0.20, 0.08],
            'sigma20': [0.02, 0.03],
            'sigma60': [0.025, 0.035]
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['GOOD', 'BAD'],
            'sector_group': ['test', 'test']
        })
        
        result = pillar.calculate(prices_with_missing, empty_fundamentals, empty_ownership, sector_map)
        
        # Should complete successfully
        assert len(result) == 2
        
        # Check that BAD stock got 0 alpha for missing return horizon
        bad_result = result[result['ticker'] == 'BAD'].iloc[0]
        bad_details = bad_result['R_details']
        
        # 1M horizon should have 0 alpha due to missing data
        assert bad_details['horizon_alphas']['1M'] == 0.0
        assert bad_details['horizon_details']['1M']['reason'] == 'missing_or_invalid_data'

    def test_zero_volatility_handling(self, pillar, sample_sector_map, empty_fundamentals, empty_ownership):
        """Test handling of zero volatility (division by zero protection)."""
        prices_zero_vol = pd.DataFrame({
            'ticker': ['ZERO_VOL'],
            'trading_date': pd.to_datetime(['2024-01-15']),
            'close': [1000],
            'ret_21d': [0.10],
            'ret_63d': [0.15],
            'ret_126d': [0.20],
            'sigma20': [0.0],  # Zero volatility
            'sigma60': [0.0]
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['ZERO_VOL'],
            'sector_group': ['test']
        })
        
        result = pillar.calculate(prices_zero_vol, empty_fundamentals, empty_ownership, sector_map)
        
        # Should complete without division by zero error
        assert len(result) == 1
        
        # All horizon alphas should be 0 due to zero volatility
        details = result.iloc[0]['R_details']
        for horizon in ['1M', '3M', '6M']:
            assert details['horizon_alphas'][horizon] == 0.0

    def test_single_stock_sector(self, pillar, empty_fundamentals, empty_ownership):
        """Test relative strength with single stock in sector."""
        prices = pd.DataFrame({
            'ticker': ['LONELY'],
            'trading_date': pd.to_datetime(['2024-01-15']),
            'close': [1000],
            'ret_21d': [0.10],
            'ret_63d': [0.15],
            'ret_126d': [0.20],
            'sigma20': [0.02],
            'sigma60': [0.025]
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['LONELY'],
            'sector_group': ['singleton']
        })
        
        result = pillar.calculate(prices, empty_fundamentals, empty_ownership, sector_map)
        
        # Should complete successfully
        assert len(result) == 1
        
        # Single stock gets percentile rank of 100 (or 50 if special handling)
        score = result.iloc[0]['R_score']
        assert 0 <= score <= 100

    def test_horizon_weighting(self, pillar, sample_prices_returns,
                             sample_sector_map, empty_fundamentals, empty_ownership):
        """Test that horizon weighting is applied correctly."""
        result = pillar.calculate(
            sample_prices_returns,
            empty_fundamentals,
            empty_ownership,
            sample_sector_map
        )
        
        # Check a specific stock's weighted alpha calculation
        winner_result = result[result['ticker'] == 'WINNER'].iloc[0]
        details = winner_result['R_details']
        
        # Manually calculate weighted alpha
        horizon_alphas = details['horizon_alphas']
        expected_weighted = (
            horizon_alphas['1M'] * 0.45 +  # 1M weight
            horizon_alphas['3M'] * 0.35 +  # 3M weight
            horizon_alphas['6M'] * 0.20    # 6M weight
        )
        
        actual_weighted = details['weighted_alpha']
        assert abs(actual_weighted - expected_weighted) < 1e-10

    def test_alpha_weights_applied(self, pillar, sample_prices_returns,
                                 sample_sector_map, empty_fundamentals, empty_ownership):
        """Test that sector/market alpha weights are applied correctly."""
        result = pillar.calculate(
            sample_prices_returns,
            empty_fundamentals,
            empty_ownership,
            sample_sector_map
        )
        
        # Check alpha weight application in horizon details
        winner_result = result[result['ticker'] == 'WINNER'].iloc[0]
        horizon_detail = winner_result['R_details']['horizon_details']['1M']
        
        # Manually calculate combined alpha
        sector_alpha = horizon_detail['sector_alpha']
        market_alpha = horizon_detail['market_alpha']
        expected_combined = sector_alpha * 0.6 + market_alpha * 0.4  # sector 60%, market 40%
        
        actual_combined = horizon_detail['combined_alpha']
        assert abs(actual_combined - expected_combined) < 1e-10

    def test_percentile_ranking(self, pillar, empty_fundamentals, empty_ownership):
        """Test percentile ranking of alpha scores."""
        # Create prices with known alpha ordering
        prices = pd.DataFrame({
            'ticker': ['FIRST', 'SECOND', 'THIRD', 'FOURTH'],
            'trading_date': pd.to_datetime(['2024-01-15'] * 4),
            'close': [1000] * 4,
            
            # Design returns to create clear alpha ordering
            # Higher return with same volatility = higher alpha
            'ret_21d': [0.20, 0.15, 0.10, 0.05],
            'ret_63d': [0.20, 0.15, 0.10, 0.05],
            'ret_126d': [0.20, 0.15, 0.10, 0.05],
            'sigma20': [0.02] * 4,  # Same volatility
            'sigma60': [0.02] * 4
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['FIRST', 'SECOND', 'THIRD', 'FOURTH'],
            'sector_group': ['test'] * 4
        })
        
        result = pillar.calculate(prices, empty_fundamentals, empty_ownership, sector_map)
        
        # Check percentile ranking order
        result_sorted = result.sort_values('R_score', ascending=False)
        
        # FIRST should have highest score, FOURTH should have lowest
        assert result_sorted.iloc[0]['ticker'] == 'FIRST'
        assert result_sorted.iloc[-1]['ticker'] == 'FOURTH'
        
        # Scores should be in descending order
        scores = result_sorted['R_score'].tolist()
        assert scores == sorted(scores, reverse=True)