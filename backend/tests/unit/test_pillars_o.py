"""Unit tests for Ownership (O) Pillar."""

import pandas as pd
import pytest
from unittest.mock import Mock
import numpy as np

from greyoak_score.pillars.ownership import OwnershipPillar
from greyoak_score.core.config_manager import ConfigManager


class TestOwnershipPillar:
    """Test Ownership pillar calculation."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration manager."""
        config = Mock(spec=ConfigManager)
        
        # Mock ownership configuration
        config.get_ownership_config.return_value = {
            "weights": {
                "promoter_hold": 0.30,
                "pledge": 0.30,
                "fii_dii_change": 0.40
            },
            "pledge_penalty_curve": [
                {"fraction": 0.00, "penalty": 0},
                {"fraction": 0.05, "penalty": 5},
                {"fraction": 0.10, "penalty": 10},
                {"fraction": 0.20, "penalty": 20},
                {"fraction": 1.00, "penalty": 30}
            ]
        }
        
        return config

    @pytest.fixture
    def pillar(self, mock_config):
        """Create OwnershipPillar instance."""
        return OwnershipPillar(mock_config)

    @pytest.fixture
    def sample_ownership_data(self):
        """Sample ownership data."""
        return pd.DataFrame({
            'ticker': ['STOCK_A', 'STOCK_B', 'STOCK_C', 'STOCK_D'],
            'quarter_end': pd.to_datetime(['2024-03-31'] * 4),
            'promoter_hold_pct': [0.60, 0.45, 0.75, 0.50],  # Varied promoter holdings
            'promoter_pledge_frac': [0.00, 0.08, 0.15, 0.25],  # Different pledge levels
            'fii_dii_delta_pp': [2.5, -1.0, 0.5, 3.0]  # FII/DII changes
        })

    @pytest.fixture
    def sample_sector_map(self):
        """Sample sector mapping."""
        return pd.DataFrame({
            'ticker': ['STOCK_A', 'STOCK_B', 'STOCK_C', 'STOCK_D'],
            'sector_group': ['it', 'it', 'banks', 'banks']
        })

    @pytest.fixture
    def sample_prices(self):
        """Minimal price data for validation."""
        return pd.DataFrame({
            'ticker': ['STOCK_A', 'STOCK_B', 'STOCK_C', 'STOCK_D'],
            'date': pd.to_datetime(['2024-01-01'] * 4),
            'close': [1000, 1200, 800, 1500]
        })

    @pytest.fixture
    def empty_fundamentals(self):
        """Empty fundamentals data."""
        return pd.DataFrame(columns=['ticker', 'quarter_end'])

    def test_pillar_name(self, pillar):
        """Test pillar name property."""
        assert pillar.pillar_name == "O"

    def test_basic_ownership_scoring(self, pillar, sample_ownership_data, 
                                   sample_sector_map, sample_prices, empty_fundamentals):
        """Test basic ownership scoring."""
        result = pillar.calculate(
            sample_prices,
            empty_fundamentals,
            sample_ownership_data,
            sample_sector_map
        )
        
        # Check structure
        assert len(result) == 4
        assert set(result.columns) == {'ticker', 'O_score', 'O_details'}
        
        # Check all tickers present
        assert set(result['ticker']) == {'STOCK_A', 'STOCK_B', 'STOCK_C', 'STOCK_D'}
        
        # Check scores are valid (0-100)
        for score in result['O_score']:
            assert 0 <= score <= 100
        
        # Check details structure
        for details in result['O_details']:
            assert 'components' in details
            assert 'final_score' in details
            assert 'config_used' in details
            
            # Check all 3 components present
            components = details['components']
            expected_components = ['promoter_hold', 'pledge', 'fii_dii_change']
            assert set(components.keys()) == set(expected_components)
            
            # Check component structure
            for comp_name, comp_data in components.items():
                assert 'score' in comp_data
                assert 'weight' in comp_data
                assert 0 <= comp_data['score'] <= 100

    def test_pledge_penalty_curve(self, pillar):
        """Test pledge penalty curve calculation."""
        # Test curve points
        curve = [
            {"fraction": 0.00, "penalty": 0},
            {"fraction": 0.05, "penalty": 5},
            {"fraction": 0.10, "penalty": 10},
            {"fraction": 0.20, "penalty": 20},
            {"fraction": 1.00, "penalty": 30}
        ]
        
        test_cases = [
            (0.00, 0.0),    # Exactly at curve point
            (0.025, 2.5),   # Midway between 0% and 5%
            (0.075, 7.5),   # Midway between 5% and 10%
            (0.15, 15.0),   # Midway between 10% and 20%
            (0.60, 30.0),   # Beyond curve - use last penalty
            (1.50, 30.0),   # Way beyond curve
        ]
        
        for pledge_frac, expected_penalty in test_cases:
            penalty = pillar._calculate_pledge_penalty(pledge_frac, curve)
            assert abs(penalty - expected_penalty) < 1e-10, f"Pledge {pledge_frac:.1%} should have penalty {expected_penalty}, got {penalty}"

    def test_pledge_component_with_penalty(self, pillar, sample_sector_map, sample_prices, empty_fundamentals):
        """Test pledge component with penalty curve application."""
        # Test data with known pledge levels
        ownership_data = pd.DataFrame({
            'ticker': ['LOW', 'MEDIUM', 'HIGH'],
            'quarter_end': pd.to_datetime(['2024-03-31'] * 3),
            'promoter_hold_pct': [0.60] * 3,  # Same promoter holding
            'promoter_pledge_frac': [0.00, 0.10, 0.25],  # Different pledge levels
            'fii_dii_delta_pp': [0.0] * 3  # Same FII/DII
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['LOW', 'MEDIUM', 'HIGH'],
            'sector_group': ['test'] * 3
        })
        
        prices = pd.DataFrame({
            'ticker': ['LOW', 'MEDIUM', 'HIGH'],
            'date': pd.to_datetime(['2024-01-01'] * 3),
            'close': [1000] * 3
        })
        
        result = pillar.calculate(prices, empty_fundamentals, ownership_data, sector_map)
        
        # LOW pledge (0%) should have highest pledge score due to no penalty
        # HIGH pledge (25%) should have lowest score due to 30 penalty
        low_pledge = result[result['ticker'] == 'LOW'].iloc[0]
        high_pledge = result[result['ticker'] == 'HIGH'].iloc[0]
        
        low_pledge_score = low_pledge['O_details']['components']['pledge']['score']
        high_pledge_score = high_pledge['O_details']['components']['pledge']['score']
        
        assert low_pledge_score > high_pledge_score, "Lower pledge should result in higher score"

    def test_promoter_component_sector_normalization(self, pillar, sample_prices, empty_fundamentals):
        """Test promoter component sector normalization."""
        # Two sectors with different promoter holding distributions
        ownership_data = pd.DataFrame({
            'ticker': ['IT_HIGH', 'IT_LOW', 'BANK_HIGH', 'BANK_LOW'],
            'quarter_end': pd.to_datetime(['2024-03-31'] * 4),
            'promoter_hold_pct': [0.80, 0.40, 0.70, 0.30],  # IT: 80%/40%, Banks: 70%/30%
            'promoter_pledge_frac': [0.0] * 4,  # No pledge effect
            'fii_dii_delta_pp': [0.0] * 4  # No FII/DII effect
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['IT_HIGH', 'IT_LOW', 'BANK_HIGH', 'BANK_LOW'],
            'sector_group': ['it', 'it', 'banks', 'banks']
        })
        
        prices = pd.DataFrame({
            'ticker': ['IT_HIGH', 'IT_LOW', 'BANK_HIGH', 'BANK_LOW'],
            'date': pd.to_datetime(['2024-01-01'] * 4),
            'close': [1000] * 4
        })
        
        result = pillar.calculate(prices, empty_fundamentals, ownership_data, sector_map)
        
        # Within each sector, higher promoter holding should score higher
        it_high = result[result['ticker'] == 'IT_HIGH'].iloc[0]
        it_low = result[result['ticker'] == 'IT_LOW'].iloc[0]
        
        it_high_promoter = it_high['O_details']['components']['promoter_hold']['score']
        it_low_promoter = it_low['O_details']['components']['promoter_hold']['score']
        
        assert it_high_promoter > it_low_promoter, "Higher promoter holding should score higher within sector"

    def test_fii_dii_component(self, pillar, sample_prices, empty_fundamentals):
        """Test FII/DII change component."""
        ownership_data = pd.DataFrame({
            'ticker': ['POSITIVE', 'NEGATIVE', 'NEUTRAL'],
            'quarter_end': pd.to_datetime(['2024-03-31'] * 3),
            'promoter_hold_pct': [0.60] * 3,  # Same promoter
            'promoter_pledge_frac': [0.0] * 3,  # No pledge
            'fii_dii_delta_pp': [5.0, -3.0, 0.0]  # Different FII/DII changes
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['POSITIVE', 'NEGATIVE', 'NEUTRAL'],
            'sector_group': ['test'] * 3
        })
        
        prices = pd.DataFrame({
            'ticker': ['POSITIVE', 'NEGATIVE', 'NEUTRAL'],
            'date': pd.to_datetime(['2024-01-01'] * 3),
            'close': [1000] * 3
        })
        
        result = pillar.calculate(prices, empty_fundamentals, ownership_data, sector_map)
        
        # Positive FII/DII change should score highest
        positive = result[result['ticker'] == 'POSITIVE'].iloc[0]
        negative = result[result['ticker'] == 'NEGATIVE'].iloc[0]
        
        positive_fii = positive['O_details']['components']['fii_dii_change']['score']
        negative_fii = negative['O_details']['components']['fii_dii_change']['score']
        
        assert positive_fii > negative_fii, "Positive FII/DII change should score higher"

    def test_missing_ownership_data(self, pillar, sample_prices, sample_sector_map, empty_fundamentals):
        """Test handling of missing ownership data."""
        # Ownership data with missing values
        ownership_with_missing = pd.DataFrame({
            'ticker': ['COMPLETE', 'MISSING'],
            'quarter_end': pd.to_datetime(['2024-03-31'] * 2),
            'promoter_hold_pct': [0.60, np.nan],
            'promoter_pledge_frac': [0.05, np.nan],
            'fii_dii_delta_pp': [2.0, np.nan]
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['COMPLETE', 'MISSING'],
            'sector_group': ['test'] * 2
        })
        
        prices = pd.DataFrame({
            'ticker': ['COMPLETE', 'MISSING'],
            'date': pd.to_datetime(['2024-01-01'] * 2),
            'close': [1000] * 2
        })
        
        result = pillar.calculate(prices, empty_fundamentals, ownership_with_missing, sector_map)
        
        # Should complete successfully
        assert len(result) == 2
        
        # Missing data stock should get neutral scores (50.0)
        missing_result = result[result['ticker'] == 'MISSING'].iloc[0]
        missing_components = missing_result['O_details']['components']
        
        for comp_name, comp_data in missing_components.items():
            assert comp_data['score'] == 50.0, f"Missing {comp_name} should get neutral score 50.0"

    def test_component_weights_sum(self, pillar, sample_ownership_data, 
                                 sample_sector_map, sample_prices, empty_fundamentals):
        """Test that component weights sum to 1.0."""
        result = pillar.calculate(
            sample_prices,
            empty_fundamentals,
            sample_ownership_data,
            sample_sector_map
        )
        
        # Check weights sum for each stock
        for _, row in result.iterrows():
            components = row['O_details']['components']
            total_weight = sum(comp['weight'] for comp in components.values())
            assert abs(total_weight - 1.0) < 1e-10, "Component weights should sum to 1.0"

    def test_single_stock_sector(self, pillar, sample_prices, empty_fundamentals):
        """Test ownership calculation with single stock in sector."""
        ownership_data = pd.DataFrame({
            'ticker': ['LONELY'],
            'quarter_end': pd.to_datetime(['2024-03-31']),
            'promoter_hold_pct': [0.60],
            'promoter_pledge_frac': [0.10],
            'fii_dii_delta_pp': [1.5]
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['LONELY'],
            'sector_group': ['singleton']
        })
        
        prices = pd.DataFrame({
            'ticker': ['LONELY'],
            'date': pd.to_datetime(['2024-01-01']),
            'close': [1000]
        })
        
        result = pillar.calculate(prices, empty_fundamentals, ownership_data, sector_map)
        
        # Should complete successfully with neutral sector-normalized scores
        assert len(result) == 1
        
        lonely_result = result.iloc[0]
        components = lonely_result['O_details']['components']
        
        # Promoter and FII/DII should be neutral due to insufficient sector data
        assert components['promoter_hold']['score'] == 50.0
        assert components['fii_dii_change']['score'] == 50.0
        
        # Pledge should still apply penalty
        pledge_score = components['pledge']['score']
        assert pledge_score <= 40.0, "Pledge penalty should still be applied even in single stock sector"

    def test_extreme_pledge_values(self, pillar):
        """Test pledge penalty with extreme values."""
        curve = [
            {"fraction": 0.00, "penalty": 0},
            {"fraction": 0.05, "penalty": 5},
            {"fraction": 0.10, "penalty": 10},
            {"fraction": 0.20, "penalty": 20},
            {"fraction": 1.00, "penalty": 30}
        ]
        
        # Test extreme values
        test_cases = [
            (-0.1, 0.0),   # Negative pledge
            (0.0, 0.0),    # Zero pledge
            (2.0, 30.0),   # 200% pledge (beyond curve)
            (np.nan, 0.0), # NaN pledge
        ]
        
        for pledge_frac, expected_penalty in test_cases:
            penalty = pillar._calculate_pledge_penalty(pledge_frac, curve)
            assert penalty == expected_penalty, f"Pledge {pledge_frac} should have penalty {expected_penalty}, got {penalty}"