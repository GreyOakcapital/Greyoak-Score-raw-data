"""Unit tests for Sector Momentum (S) Pillar with S_z tracking."""

import pandas as pd
import pytest
from unittest.mock import Mock
import numpy as np

from greyoak_score.pillars.sector_momentum import SectorMomentumPillar
from greyoak_score.core.config_manager import ConfigManager


class TestSectorMomentumPillar:
    """Test Sector Momentum pillar calculation and S_z tracking."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration manager."""
        config = Mock(spec=ConfigManager)
        
        # Mock sector momentum configuration
        config.get_sector_momentum_config.return_value = {
            "1M": 0.20,
            "3M": 0.30,
            "6M": 0.50
        }
        
        return config

    @pytest.fixture
    def pillar(self, mock_config):
        """Create SectorMomentumPillar instance."""
        return SectorMomentumPillar(mock_config)

    @pytest.fixture
    def sample_sector_momentum_data(self):
        """Sample price data with returns for sector momentum."""
        return pd.DataFrame({
            'ticker': ['IT_A', 'IT_B', 'BANK_A', 'BANK_B', 'METAL_A', 'METAL_B'],
            'date': pd.to_datetime(['2024-01-15'] * 6),
            
            # Returns designed to show sector momentum differences
            'ret_21d': [0.15, 0.12, 0.05, 0.03, -0.05, -0.08],  # IT > Banks > Metals
            'ret_63d': [0.25, 0.22, 0.08, 0.06, -0.02, -0.05],  # IT > Banks > Metals
            'ret_126d': [0.35, 0.32, 0.12, 0.10, 0.02, -0.01], # IT > Banks > Metals
            
            # Volatility for normalization
            'sigma20': [0.02, 0.025, 0.03, 0.035, 0.04, 0.045]
        })

    @pytest.fixture
    def sample_sector_map(self):
        """Sample sector mapping for momentum testing."""
        return pd.DataFrame({
            'ticker': ['IT_A', 'IT_B', 'BANK_A', 'BANK_B', 'METAL_A', 'METAL_B'],
            'sector_group': ['it', 'it', 'banks', 'banks', 'metals', 'metals']
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
        assert pillar.pillar_name == "S"

    def test_basic_sector_momentum_scoring(self, pillar, sample_sector_momentum_data,
                                         sample_sector_map, empty_fundamentals, empty_ownership):
        """Test basic sector momentum scoring with S_z tracking."""
        result = pillar.calculate(
            sample_sector_momentum_data,
            empty_fundamentals,
            empty_ownership,
            sample_sector_map
        )
        
        # Check structure - CRITICAL: Must have S_z column
        assert len(result) == 6
        assert set(result.columns) == {'ticker', 'S_score', 'S_z', 'S_details'}
        
        # Check all tickers present
        expected_tickers = {'IT_A', 'IT_B', 'BANK_A', 'BANK_B', 'METAL_A', 'METAL_B'}
        assert set(result['ticker']) == expected_tickers
        
        # Check scores are valid (0-100)
        for score in result['S_score']:
            assert 0 <= score <= 100
        
        # Check S_z values are finite
        for s_z in result['S_z']:
            assert np.isfinite(s_z), "S_z values should be finite"
        
        # Check details structure
        for details in result['S_details']:
            assert 'sector_group' in details
            assert 'horizon_s_z' in details
            assert 'weighted_s_z' in details
            assert 'final_score' in details

    def test_s_z_calculation_cross_sector(self, pillar, sample_sector_momentum_data,
                                        sample_sector_map, empty_fundamentals, empty_ownership):
        """Test that S_z is calculated cross-sector (not within-sector)."""
        result = pillar.calculate(
            sample_sector_momentum_data,
            empty_fundamentals,
            empty_ownership,
            sample_sector_map
        )
        
        # Get S_z by sector
        sector_s_z = {}
        for _, row in result.iterrows():
            sector = row['S_details']['sector_group']
            if sector not in sector_s_z:
                sector_s_z[sector] = []
            sector_s_z[sector].append(row['S_z'])
        
        # Calculate mean S_z per sector
        mean_s_z_by_sector = {sector: np.mean(values) for sector, values in sector_s_z.items()}
        
        # IT should have highest S_z (best performance), metals lowest
        it_s_z = mean_s_z_by_sector['it']
        metals_s_z = mean_s_z_by_sector['metals']
        
        assert it_s_z > metals_s_z, "IT sector should have higher S_z than metals based on test data"

    def test_sector_momentum_formula(self, pillar):
        """Test the sector momentum formula components."""
        # Test sector aggregates calculation
        test_data = pd.DataFrame({
            'ticker': ['A1', 'A2', 'B1', 'B2'],
            'sector_group': ['sectorA', 'sectorA', 'sectorB', 'sectorB'],
            'ret_21d': [0.10, 0.14, 0.05, 0.07],  # SectorA avg=12%, SectorB avg=6%
            'ret_63d': [0.20, 0.24, 0.10, 0.14],  # SectorA avg=22%, SectorB avg=12%
            'ret_126d': [0.30, 0.34, 0.15, 0.19], # SectorA avg=32%, SectorB avg=17%
            'sigma20': [0.02, 0.03, 0.025, 0.035]  # SectorA avg=2.5%, SectorB avg=3%
        })
        
        sector_aggs = pillar._calculate_sector_aggregates(test_data)
        
        # Check sector aggregates
        assert len(sector_aggs) == 2
        
        sector_a = sector_aggs[sector_aggs['sector_group'] == 'sectorA'].iloc[0]
        sector_b = sector_aggs[sector_aggs['sector_group'] == 'sectorB'].iloc[0]
        
        # Check averages are correct
        assert abs(sector_a['ret_21d'] - 0.12) < 1e-10, "SectorA 1M return should be 12%"
        assert abs(sector_b['ret_21d'] - 0.06) < 1e-10, "SectorB 1M return should be 6%"

    def test_market_benchmark_calculation(self, pillar, sample_sector_momentum_data):
        """Test market benchmark calculation."""
        market_benchmark = pillar._calculate_market_benchmark(sample_sector_momentum_data)
        
        # Should have all horizons
        assert set(market_benchmark.keys()) == {'ret_21d', 'ret_63d', 'ret_126d'}
        
        # Market return should be equal-weighted average
        expected_1m = sample_sector_momentum_data['ret_21d'].mean()
        assert abs(market_benchmark['ret_21d'] - expected_1m) < 1e-10, "Market 1M should be equal-weighted average"

    def test_horizon_weighting(self, pillar, sample_sector_momentum_data,
                             sample_sector_map, empty_fundamentals, empty_ownership):
        """Test that horizon weights (1M:20%, 3M:30%, 6M:50%) are applied correctly."""
        result = pillar.calculate(
            sample_sector_momentum_data,
            empty_fundamentals,
            empty_ownership,
            sample_sector_map
        )
        
        # Check a specific stock's weighted S_z calculation
        it_a_result = result[result['ticker'] == 'IT_A'].iloc[0]
        horizon_s_z = it_a_result['S_details']['horizon_s_z']
        weighted_s_z = it_a_result['S_details']['weighted_s_z']
        
        # Manually calculate expected weighted S_z
        expected_weighted = (
            horizon_s_z.get('1M', 0) * 0.20 +
            horizon_s_z.get('3M', 0) * 0.30 +
            horizon_s_z.get('6M', 0) * 0.50
        )
        
        assert abs(weighted_s_z - expected_weighted) < 1e-10, "Weighted S_z should match manual calculation"

    def test_missing_sector_data(self, pillar, empty_fundamentals, empty_ownership):
        """Test handling of missing sector data."""
        # Price data with missing sector mapping
        prices_with_missing = pd.DataFrame({
            'ticker': ['MAPPED', 'UNMAPPED'],
            'date': pd.to_datetime(['2024-01-15'] * 2),
            'ret_21d': [0.10, 0.15],
            'ret_63d': [0.20, 0.25],
            'ret_126d': [0.30, 0.35],
            'sigma20': [0.02, 0.03]
        })
        
        # Sector map missing one ticker
        incomplete_sector_map = pd.DataFrame({
            'ticker': ['MAPPED'],
            'sector_group': ['test']
        })
        
        result = pillar.calculate(
            prices_with_missing,
            empty_fundamentals,
            empty_ownership,
            incomplete_sector_map
        )
        
        # Should complete successfully
        assert len(result) == 2
        
        # Unmapped stock should get neutral scores
        unmapped_result = result[result['ticker'] == 'UNMAPPED'].iloc[0]
        
        assert unmapped_result['S_score'] == 50.0, "Unmapped stock should get neutral S score"
        assert unmapped_result['S_z'] == 0.0, "Unmapped stock should get neutral S_z"
        assert unmapped_result['S_details']['reason'] == 'missing_sector_data'

    def test_single_sector_case(self, pillar, empty_fundamentals, empty_ownership):
        """Test sector momentum with only one sector."""
        single_sector_data = pd.DataFrame({
            'ticker': ['ONLY1', 'ONLY2'],
            'date': pd.to_datetime(['2024-01-15'] * 2),
            'ret_21d': [0.10, 0.12],
            'ret_63d': [0.20, 0.22],
            'ret_126d': [0.30, 0.32],
            'sigma20': [0.02, 0.03]
        })
        
        single_sector_map = pd.DataFrame({
            'ticker': ['ONLY1', 'ONLY2'],
            'sector_group': ['lonely'] * 2
        })
        
        result = pillar.calculate(
            single_sector_data,
            empty_fundamentals,
            empty_ownership,
            single_sector_map
        )
        
        # Should complete successfully
        assert len(result) == 2
        
        # With single sector, cross-sector z-score should be 0
        for _, row in result.iterrows():
            assert row['S_z'] == 0.0, "Single sector should have S_z = 0"
            assert row['S_score'] == 50.0, "Single sector should have neutral score"

    def test_volatility_protection(self, pillar, empty_fundamentals, empty_ownership):
        """Test protection against zero volatility in sector momentum."""
        # Data with zero/near-zero volatility
        zero_vol_data = pd.DataFrame({
            'ticker': ['ZERO_VOL', 'NORMAL'],
            'date': pd.to_datetime(['2024-01-15'] * 2),
            'ret_21d': [0.10, 0.12],
            'ret_63d': [0.20, 0.22],
            'ret_126d': [0.30, 0.32],
            'sigma20': [0.0, 0.02]  # Zero vs normal volatility
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['ZERO_VOL', 'NORMAL'],
            'sector_group': ['testA', 'testB']  # Different sectors
        })
        
        result = pillar.calculate(zero_vol_data, empty_fundamentals, empty_ownership, sector_map)
        
        # Should complete without division by zero errors
        assert len(result) == 2
        
        # All S_z values should be finite
        for s_z in result['S_z']:
            assert np.isfinite(s_z), "S_z should be finite even with zero volatility"

    def test_s_z_summary_function(self, pillar, sample_sector_momentum_data,
                                sample_sector_map, empty_fundamentals, empty_ownership):
        """Test the S_z summary function for debugging."""
        result = pillar.calculate(
            sample_sector_momentum_data,
            empty_fundamentals,
            empty_ownership,
            sample_sector_map
        )
        
        # Test the summary function
        s_z_summary = pillar.get_sector_s_z_summary(result)
        
        # Should have entries for all sectors
        expected_sectors = {'it', 'banks', 'metals'}
        assert set(s_z_summary.keys()) == expected_sectors
        
        # All values should be finite
        for sector, mean_s_z in s_z_summary.items():
            assert np.isfinite(mean_s_z), f"Mean S_z for {sector} should be finite"

    def test_critical_s_z_output_format(self, pillar, sample_sector_momentum_data,
                                      sample_sector_map, empty_fundamentals, empty_ownership):
        """CRITICAL: Test that S_z is properly output for guardrails system."""
        result = pillar.calculate(
            sample_sector_momentum_data,
            empty_fundamentals,
            empty_ownership,
            sample_sector_map
        )
        
        # CRITICAL: Every row must have S_z value
        assert 'S_z' in result.columns, "Result must include S_z column"
        assert not result['S_z'].isna().any(), "No S_z values should be NaN"
        
        # CRITICAL: S_z should be in reasonable range (typically -3 to +3 for z-scores)
        s_z_values = result['S_z'].values
        assert all(-10 <= s_z <= 10 for s_z in s_z_values), "S_z values should be in reasonable range"
        
        # CRITICAL: S_z should be stored in details for audit trail
        for _, row in result.iterrows():
            details = row['S_details']
            assert 'weighted_s_z' in details, "S_z should be stored in details"
            assert details['weighted_s_z'] == row['S_z'], "S_z in details should match column value"

    def test_cross_sector_normalization_not_within_sector(self, pillar, empty_fundamentals, empty_ownership):
        """CRITICAL: Test that normalization is cross-sector, not within-sector."""
        # Design data where within-sector normalization would give different results
        cross_sector_test_data = pd.DataFrame({
            'ticker': ['STRONG_A', 'WEAK_A', 'STRONG_B', 'WEAK_B'],
            'date': pd.to_datetime(['2024-01-15'] * 4),
            # Sector A: both strong performers, Sector B: both weak performers
            'ret_21d': [0.20, 0.18, 0.05, 0.03],  # A > B clearly
            'ret_63d': [0.30, 0.28, 0.08, 0.06],
            'ret_126d': [0.40, 0.38, 0.12, 0.10],
            'sigma20': [0.02, 0.025, 0.03, 0.035]
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['STRONG_A', 'WEAK_A', 'STRONG_B', 'WEAK_B'],
            'sector_group': ['sectorA', 'sectorA', 'sectorB', 'sectorB']
        })
        
        result = pillar.calculate(cross_sector_test_data, empty_fundamentals, empty_ownership, sector_map)
        
        # Get S_z by sector
        sector_a_s_z = result[result['ticker'].str.endswith('_A')]['S_z'].mean()
        sector_b_s_z = result[result['ticker'].str.endswith('_B')]['S_z'].mean()
        
        # Cross-sector normalization: Sector A should have positive S_z, Sector B negative
        assert sector_a_s_z > sector_b_s_z, "Cross-sector normalization: strong sector should have higher S_z"
        assert sector_a_s_z > 0, "Strong performing sector should have positive S_z"
        assert sector_b_s_z < 0, "Weak performing sector should have negative S_z"

    def test_missing_return_columns(self, pillar, sample_sector_map, empty_fundamentals, empty_ownership):
        """Test error handling for missing return columns."""
        # Price data missing required return columns
        incomplete_prices = pd.DataFrame({
            'ticker': ['TEST'],
            'date': pd.to_datetime(['2024-01-15']),
            'close': [1000]
            # Missing ret_21d, ret_63d, ret_126d, sigma20
        })
        
        with pytest.raises(ValueError, match="Missing required columns for sector momentum"):
            pillar.calculate(incomplete_prices, empty_fundamentals, empty_ownership, sample_sector_map)