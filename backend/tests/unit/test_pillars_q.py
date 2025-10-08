"""Unit tests for Quality (Q) Pillar."""

import pandas as pd
import pytest
from unittest.mock import Mock
import numpy as np

from greyoak_score.pillars.quality import QualityPillar
from greyoak_score.core.config_manager import ConfigManager


class TestQualityPillar:
    """Test Quality pillar calculation."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration manager."""
        config = Mock(spec=ConfigManager)
        
        # Mock quality configuration
        config.get_quality_config.return_value = {
            "roce_3y": 0.65,
            "omp_stability": 0.35
        }
        
        return config

    @pytest.fixture
    def pillar(self, mock_config):
        """Create QualityPillar instance."""
        return QualityPillar(mock_config)

    @pytest.fixture
    def sample_quality_data(self):
        """Sample fundamentals data with quality metrics."""
        return pd.DataFrame({
            'ticker': ['HIGH_Q', 'MED_Q', 'LOW_Q', 'MIXED_Q'],
            'quarter_end': pd.to_datetime(['2024-03-31'] * 4),
            'roce_3y': [0.25, 0.18, 0.12, 0.20],  # Higher is better
            'omp_stdev_12q': [0.02, 0.05, 0.08, 0.12]  # Lower is better (more stable)
        })

    @pytest.fixture
    def sample_sector_map(self):
        """Sample sector mapping."""
        return pd.DataFrame({
            'ticker': ['HIGH_Q', 'MED_Q', 'LOW_Q', 'MIXED_Q'],
            'sector_group': ['it', 'it', 'finance', 'finance']
        })

    @pytest.fixture
    def sample_prices(self):
        """Minimal price data for validation."""
        return pd.DataFrame({
            'ticker': ['HIGH_Q', 'MED_Q', 'LOW_Q', 'MIXED_Q'],
            'date': pd.to_datetime(['2024-01-01'] * 4),
            'close': [1000, 1200, 800, 1500]
        })

    @pytest.fixture
    def empty_ownership(self):
        """Empty ownership data."""
        return pd.DataFrame(columns=['ticker', 'quarter_end'])

    def test_pillar_name(self, pillar):
        """Test pillar name property."""
        assert pillar.pillar_name == "Q"

    def test_basic_quality_scoring(self, pillar, sample_quality_data,
                                 sample_sector_map, sample_prices, empty_ownership):
        """Test basic quality scoring."""
        result = pillar.calculate(
            sample_prices,
            sample_quality_data,
            empty_ownership,
            sample_sector_map
        )
        
        # Check structure
        assert len(result) == 4
        assert set(result.columns) == {'ticker', 'Q_score', 'Q_details'}
        
        # Check all tickers present
        assert set(result['ticker']) == {'HIGH_Q', 'MED_Q', 'LOW_Q', 'MIXED_Q'}
        
        # Check scores are valid (0-100)
        for score in result['Q_score']:
            assert 0 <= score <= 100
        
        # Check details structure
        for details in result['Q_details']:
            assert 'components' in details
            assert 'final_score' in details
            assert 'config_used' in details
            
            # Should have quality components
            components = details['components']
            expected_components = ['roce_3y', 'omp_stability']
            # At least one component should be present
            assert len(set(components.keys()).intersection(expected_components)) > 0

    def test_quality_component_scoring(self, pillar, sample_sector_map, sample_prices, empty_ownership):
        """Test individual quality component scoring."""
        # Test data designed to show clear quality differences
        quality_data = pd.DataFrame({
            'ticker': ['EXCELLENT', 'POOR'],
            'quarter_end': pd.to_datetime(['2024-03-31'] * 2),
            'roce_3y': [0.30, 0.05],  # Excellent vs poor ROCE
            'omp_stdev_12q': [0.01, 0.15]  # Stable vs volatile OPM
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['EXCELLENT', 'POOR'],
            'sector_group': ['test'] * 2
        })
        
        prices = pd.DataFrame({
            'ticker': ['EXCELLENT', 'POOR'],
            'date': pd.to_datetime(['2024-01-01'] * 2),
            'close': [1000] * 2
        })
        
        result = pillar.calculate(prices, quality_data, empty_ownership, sector_map)
        
        # EXCELLENT should have higher Q score than POOR
        excellent = result[result['ticker'] == 'EXCELLENT'].iloc[0]
        poor = result[result['ticker'] == 'POOR'].iloc[0]
        
        assert excellent['Q_score'] > poor['Q_score'], "Higher quality stock should have higher Q score"

    def test_roce_component_higher_better(self, pillar, sample_sector_map, sample_prices, empty_ownership):
        """Test that higher ROCE gives higher component score."""
        quality_data = pd.DataFrame({
            'ticker': ['HIGH_ROCE', 'LOW_ROCE'],
            'quarter_end': pd.to_datetime(['2024-03-31'] * 2),
            'roce_3y': [0.35, 0.10],  # Clear difference in ROCE
            'omp_stdev_12q': [0.05] * 2  # Same OPM stability
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['HIGH_ROCE', 'LOW_ROCE'],
            'sector_group': ['test'] * 2
        })
        
        prices = pd.DataFrame({
            'ticker': ['HIGH_ROCE', 'LOW_ROCE'],
            'date': pd.to_datetime(['2024-01-01'] * 2),
            'close': [1000] * 2
        })
        
        result = pillar.calculate(prices, quality_data, empty_ownership, sector_map)
        
        high_roce = result[result['ticker'] == 'HIGH_ROCE'].iloc[0]
        low_roce = result[result['ticker'] == 'LOW_ROCE'].iloc[0]
        
        # Check ROCE component scores
        high_roce_comp = high_roce['Q_details']['components']['roce_3y']['points']
        low_roce_comp = low_roce['Q_details']['components']['roce_3y']['points']
        
        assert high_roce_comp > low_roce_comp, "Higher ROCE should give higher component score"

    def test_omp_stability_lower_better(self, pillar, sample_sector_map, sample_prices, empty_ownership):
        """Test that lower OPM standard deviation gives higher component score."""
        quality_data = pd.DataFrame({
            'ticker': ['STABLE', 'VOLATILE'],
            'quarter_end': pd.to_datetime(['2024-03-31'] * 2),
            'roce_3y': [0.20] * 2,  # Same ROCE
            'omp_stdev_12q': [0.01, 0.10]  # Different OPM stability
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['STABLE', 'VOLATILE'],
            'sector_group': ['test'] * 2
        })
        
        prices = pd.DataFrame({
            'ticker': ['STABLE', 'VOLATILE'],
            'date': pd.to_datetime(['2024-01-01'] * 2),
            'close': [1000] * 2
        })
        
        result = pillar.calculate(prices, quality_data, empty_ownership, sector_map)
        
        stable = result[result['ticker'] == 'STABLE'].iloc[0]
        volatile = result[result['ticker'] == 'VOLATILE'].iloc[0]
        
        # Check OPM stability component scores
        stable_omp = stable['Q_details']['components']['omp_stability']['points']
        volatile_omp = volatile['Q_details']['components']['omp_stability']['points']
        
        assert stable_omp > volatile_omp, "Lower OPM volatility should give higher component score"

    def test_missing_quality_data(self, pillar, sample_sector_map, sample_prices, empty_ownership):
        """Test handling of missing quality data."""
        quality_with_missing = pd.DataFrame({
            'ticker': ['COMPLETE', 'PARTIAL', 'EMPTY'],
            'quarter_end': pd.to_datetime(['2024-03-31'] * 3),
            'roce_3y': [0.20, np.nan, np.nan],  # COMPLETE has both, PARTIAL missing ROCE
            'omp_stdev_12q': [0.05, 0.08, np.nan]  # EMPTY missing both
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['COMPLETE', 'PARTIAL', 'EMPTY'],
            'sector_group': ['test'] * 3
        })
        
        prices = pd.DataFrame({
            'ticker': ['COMPLETE', 'PARTIAL', 'EMPTY'],
            'date': pd.to_datetime(['2024-01-01'] * 3),
            'close': [1000] * 3
        })
        
        result = pillar.calculate(prices, quality_with_missing, empty_ownership, sector_map)
        
        # Should complete successfully
        assert len(result) == 3
        
        # Check that partial data is handled correctly
        partial_result = result[result['ticker'] == 'PARTIAL'].iloc[0]
        partial_components = partial_result['Q_details']['components']
        
        # Should have OPM stability but not ROCE
        assert 'omp_stability' in partial_components
        assert 'roce_3y' not in partial_components
        
        # Total weight should be adjusted
        total_weight = partial_result['Q_details']['total_weight_used']
        assert total_weight == 0.35, "Should only use OPM stability weight when ROCE is missing"

    def test_component_weights_correct(self, pillar, sample_quality_data,
                                     sample_sector_map, sample_prices, empty_ownership):
        """Test that component weights are correct (65% ROCE, 35% OPM)."""
        result = pillar.calculate(
            sample_prices,
            sample_quality_data,
            empty_ownership,
            sample_sector_map
        )
        
        # Check weights for stocks with complete data
        for _, row in result.iterrows():
            components = row['Q_details']['components']
            if 'roce_3y' in components and 'omp_stability' in components:
                roce_weight = components['roce_3y']['weight']
                omp_weight = components['omp_stability']['weight']
                
                assert roce_weight == 0.65, "ROCE weight should be 65%"
                assert omp_weight == 0.35, "OPM stability weight should be 35%"
                assert abs((roce_weight + omp_weight) - 1.0) < 1e-10, "Weights should sum to 1.0"

    def test_sector_normalization(self, pillar, sample_prices, empty_ownership):
        """Test sector-wise normalization of quality metrics."""
        # Two sectors with different quality distributions
        quality_data = pd.DataFrame({
            'ticker': ['IT_GOOD', 'IT_BAD', 'BANK_GOOD', 'BANK_BAD'],
            'quarter_end': pd.to_datetime(['2024-03-31'] * 4),
            'roce_3y': [0.30, 0.15, 0.20, 0.08],  # IT higher ROCE range than banks
            'omp_stdev_12q': [0.02, 0.08, 0.03, 0.09]  # Similar OPM ranges
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['IT_GOOD', 'IT_BAD', 'BANK_GOOD', 'BANK_BAD'],
            'sector_group': ['it', 'it', 'banks', 'banks']
        })
        
        prices = pd.DataFrame({
            'ticker': ['IT_GOOD', 'IT_BAD', 'BANK_GOOD', 'BANK_BAD'],
            'date': pd.to_datetime(['2024-01-01'] * 4),
            'close': [1000] * 4
        })
        
        result = pillar.calculate(prices, quality_data, empty_ownership, sector_map)
        
        # Within each sector, GOOD should score higher than BAD
        it_good = result[result['ticker'] == 'IT_GOOD'].iloc[0]
        it_bad = result[result['ticker'] == 'IT_BAD'].iloc[0]
        bank_good = result[result['ticker'] == 'BANK_GOOD'].iloc[0]
        bank_bad = result[result['ticker'] == 'BANK_BAD'].iloc[0]
        
        assert it_good['Q_score'] > it_bad['Q_score'], "IT_GOOD should outscore IT_BAD"
        assert bank_good['Q_score'] > bank_bad['Q_score'], "BANK_GOOD should outscore BANK_BAD"

    def test_empty_fundamentals_data(self, pillar, sample_sector_map, sample_prices, empty_ownership):
        """Test with empty fundamentals data."""
        empty_fundamentals = pd.DataFrame(columns=['ticker', 'quarter_end'])
        
        result = pillar.calculate(sample_prices, empty_fundamentals, empty_ownership, sample_sector_map)
        
        # Should return empty result with proper structure
        assert len(result) == 0
        assert list(result.columns) == ['ticker', 'Q_score', 'Q_details']

    def test_no_quality_metrics_in_data(self, pillar, sample_sector_map, sample_prices, empty_ownership, caplog):
        """Test fundamentals data without quality metrics."""
        # Fundamentals data without quality metrics
        no_quality_data = pd.DataFrame({
            'ticker': ['TEST'],
            'quarter_end': pd.to_datetime(['2024-03-31']),
            'roe_3y': [0.15],  # Has other metrics but no quality metrics
            'pe': [25.0]
        })
        
        result = pillar.calculate(sample_prices, no_quality_data, empty_ownership, sample_sector_map)
        
        # Should log warning about missing metrics
        assert "No quality metrics available" in caplog.text
        
        # Should still return result but with no components
        assert len(result) == 1
        components = result.iloc[0]['Q_details']['components']
        assert len(components) == 0

    def test_single_metric_available(self, pillar, sample_sector_map, sample_prices, empty_ownership):
        """Test with only one quality metric available."""
        # Only ROCE available, no OPM stability
        partial_data = pd.DataFrame({
            'ticker': ['PARTIAL1', 'PARTIAL2'],
            'quarter_end': pd.to_datetime(['2024-03-31'] * 2),
            'roce_3y': [0.25, 0.15]  # Only ROCE, no OPM stability
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['PARTIAL1', 'PARTIAL2'],
            'sector_group': ['test'] * 2
        })
        
        prices = pd.DataFrame({
            'ticker': ['PARTIAL1', 'PARTIAL2'],
            'date': pd.to_datetime(['2024-01-01'] * 2),
            'close': [1000] * 2
        })
        
        result = pillar.calculate(prices, partial_data, empty_ownership, sector_map)
        
        # Should complete successfully using only ROCE
        assert len(result) == 2
        
        # Both stocks should have only ROCE component
        for _, row in result.iterrows():
            components = row['Q_details']['components']
            assert 'roce_3y' in components
            assert 'omp_stability' not in components
            
            # Total weight should be adjusted to ROCE weight only
            total_weight = row['Q_details']['total_weight_used']
            assert total_weight == 0.65, "Should use only ROCE weight"