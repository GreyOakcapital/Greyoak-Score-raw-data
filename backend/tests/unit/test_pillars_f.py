"""Unit tests for Fundamentals (F) Pillar."""

import pandas as pd
import pytest
from unittest.mock import Mock

from greyoak_score.pillars.fundamentals import FundamentalsPillar
from greyoak_score.core.config_manager import ConfigManager


class TestFundamentalsPillar:
    """Test Fundamentals pillar calculation."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration manager."""
        config = Mock(spec=ConfigManager)
        
        # Mock non-financial weights
        config.get_non_financial_fundamentals_weights.return_value = {
            "roe_3y": 0.35,
            "sales_cagr_3y": 0.25,
            "eps_cagr_3y": 0.20,
            "valuation": 0.20
        }
        
        # Mock banking weights
        config.get_banking_fundamentals_weights.return_value = {
            "roa_3y": 0.30,
            "roe_3y": 0.25,
            "gnpa_pct": 0.20,
            "pcr_pct": 0.15,
            "nim_3y": 0.10
        }
        
        # Mock sector classification
        config.is_banking_sector.side_effect = lambda x: x in ["banks", "psu_banks"]
        
        return config

    @pytest.fixture
    def pillar(self, mock_config):
        """Create FundamentalsPillar instance."""
        return FundamentalsPillar(mock_config)

    @pytest.fixture
    def sample_fundamentals_non_financial(self):
        """Sample fundamentals data for non-financial stocks."""
        return pd.DataFrame({
            'ticker': ['RELIANCE', 'TCS', 'INFY'],
            'quarter_end': pd.to_datetime(['2024-03-31'] * 3),
            'roe_3y': [0.15, 0.28, 0.25],
            'sales_cagr_3y': [0.08, 0.12, 0.10],
            'eps_cagr_3y': [0.12, 0.18, 0.15],
            'pe': [25.5, 28.2, 24.8],
            'ev_ebitda': [12.3, 18.5, 16.2]
        })

    @pytest.fixture
    def sample_fundamentals_banking(self):
        """Sample fundamentals data for banking stocks."""
        return pd.DataFrame({
            'ticker': ['HDFC', 'ICICI'],
            'quarter_end': pd.to_datetime(['2024-03-31'] * 2),
            'roa_3y': [0.018, 0.021],
            'roe_3y': [0.15, 0.18],
            'gnpa_pct': [1.2, 0.8],
            'pcr_pct': [85.0, 90.0],
            'nim_3y': [4.2, 4.5]
        })

    @pytest.fixture
    def sample_sector_map(self):
        """Sample sector mapping."""
        return pd.DataFrame({
            'ticker': ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'ICICI'],
            'sector_group': ['diversified', 'it', 'it', 'banks', 'banks']
        })

    @pytest.fixture
    def sample_prices(self):
        """Minimal price data for validation."""
        return pd.DataFrame({
            'ticker': ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'ICICI'],
            'trading_date': pd.to_datetime(['2024-01-01'] * 5),
            'close': [2500, 3400, 1600, 1700, 1200]
        })

    @pytest.fixture
    def empty_ownership(self):
        """Empty ownership data."""
        return pd.DataFrame(columns=['ticker', 'quarter_end'])

    def test_pillar_name(self, pillar):
        """Test pillar name property."""
        assert pillar.pillar_name == "F"

    def test_non_financial_scoring(self, pillar, sample_fundamentals_non_financial, 
                                 sample_sector_map, sample_prices, empty_ownership):
        """Test fundamentals scoring for non-financial stocks."""
        result = pillar.calculate(
            sample_prices,
            sample_fundamentals_non_financial,
            empty_ownership,
            sample_sector_map
        )
        
        # Check structure
        assert len(result) == 3
        assert set(result.columns) == {'ticker', 'F_score', 'F_details'}
        
        # Check all tickers present
        assert set(result['ticker']) == {'RELIANCE', 'TCS', 'INFY'}
        
        # Check scores are valid (0-100)
        for score in result['F_score']:
            assert 0 <= score <= 100
        
        # Check details structure
        for details in result['F_details']:
            assert 'pillar_type' in details
            assert details['pillar_type'] == 'non_financial'
            assert 'components' in details
            assert 'final_score' in details

    def test_banking_scoring(self, pillar, sample_fundamentals_banking,
                           sample_sector_map, sample_prices, empty_ownership):
        """Test fundamentals scoring for banking stocks."""
        # Filter data to banking stocks only
        banking_fundamentals = sample_fundamentals_banking.copy()
        banking_sector_map = sample_sector_map[
            sample_sector_map['ticker'].isin(['HDFC', 'ICICI'])
        ].copy()
        banking_prices = sample_prices[
            sample_prices['ticker'].isin(['HDFC', 'ICICI'])
        ].copy()
        
        result = pillar.calculate(
            banking_prices,
            banking_fundamentals,
            empty_ownership,
            banking_sector_map
        )
        
        # Check structure
        assert len(result) == 2
        assert set(result['ticker']) == {'HDFC', 'ICICI'}
        
        # Check scores are valid (0-100)
        for score in result['F_score']:
            assert 0 <= score <= 100
        
        # Check details structure for banking
        for details in result['F_details']:
            assert 'pillar_type' in details
            assert details['pillar_type'] == 'banking'
            assert 'components' in details

    def test_mixed_banking_non_financial(self, pillar, sample_fundamentals_non_financial,
                                       sample_fundamentals_banking, sample_sector_map,
                                       sample_prices, empty_ownership):
        """Test fundamentals scoring with mixed banking and non-financial stocks."""
        # Combine datasets
        combined_fundamentals = pd.concat([
            sample_fundamentals_non_financial,
            sample_fundamentals_banking
        ], ignore_index=True)
        
        result = pillar.calculate(
            sample_prices,
            combined_fundamentals,
            empty_ownership,
            sample_sector_map
        )
        
        # Check all 5 stocks scored
        assert len(result) == 5
        assert set(result['ticker']) == {'RELIANCE', 'TCS', 'INFY', 'HDFC', 'ICICI'}
        
        # Check pillar types are correct
        for _, row in result.iterrows():
            ticker = row['ticker']
            details = row['F_details']
            
            if ticker in ['HDFC', 'ICICI']:
                assert details['pillar_type'] == 'banking'
            else:
                assert details['pillar_type'] == 'non_financial'

    def test_missing_fundamentals_data(self, pillar, sample_sector_map, 
                                     sample_prices, empty_ownership):
        """Test error handling with missing fundamentals data."""
        empty_fundamentals = pd.DataFrame(columns=['ticker', 'quarter_end'])
        
        result = pillar.calculate(
            sample_prices,
            empty_fundamentals,
            empty_ownership,
            sample_sector_map
        )
        
        # Should return empty result with proper structure
        assert len(result) == 0
        assert list(result.columns) == ['ticker', 'F_score', 'F_details']

    def test_missing_required_columns(self, pillar, sample_sector_map,
                                    sample_prices, empty_ownership):
        """Test validation of required columns."""
        # Fundamentals data missing required columns
        bad_fundamentals = pd.DataFrame({
            'ticker': ['TEST'],
            # Missing quarter_end
            'roe_3y': [0.15]
        })
        
        with pytest.raises(ValueError, match="Missing required fundamentals columns"):
            pillar.calculate(
                sample_prices,
                bad_fundamentals,
                empty_ownership,
                sample_sector_map
            )

    def test_valuation_fallback(self, pillar, sample_sector_map, sample_prices, empty_ownership):
        """Test valuation metric fallback from EV/EBITDA to PE."""
        # Fundamentals with missing EV/EBITDA
        fundamentals = pd.DataFrame({
            'ticker': ['TEST1', 'TEST2'],
            'quarter_end': pd.to_datetime(['2024-03-31'] * 2),
            'roe_3y': [0.15, 0.20],
            'sales_cagr_3y': [0.10, 0.12],
            'eps_cagr_3y': [0.15, 0.18],
            'pe': [25.0, 30.0],
            'ev_ebitda': [12.0, None]  # One missing EV/EBITDA
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['TEST1', 'TEST2'],
            'sector_group': ['it', 'it']
        })
        
        prices = pd.DataFrame({
            'ticker': ['TEST1', 'TEST2'],
            'trading_date': pd.to_datetime(['2024-01-01'] * 2),
            'close': [1000, 1200]
        })
        
        result = pillar.calculate(prices, fundamentals, empty_ownership, sector_map)
        
        # Should complete successfully using PE fallback
        assert len(result) == 2
        
        # Check that valuation was used in components
        for _, row in result.iterrows():
            components = row['F_details']['components']
            assert 'valuation' in components

    def test_partial_missing_metrics(self, pillar, sample_sector_map, sample_prices, empty_ownership):
        """Test handling of partial missing metrics in fundamentals."""
        # Some metrics missing
        fundamentals = pd.DataFrame({
            'ticker': ['TEST'],
            'quarter_end': pd.to_datetime(['2024-03-31']),
            'roe_3y': [0.15],
            'sales_cagr_3y': [None],  # Missing
            'eps_cagr_3y': [0.12],
            'pe': [25.0]
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['TEST'],
            'sector_group': ['it']
        })
        
        prices = pd.DataFrame({
            'ticker': ['TEST'],
            'trading_date': pd.to_datetime(['2024-01-01']),
            'close': [1000]
        })
        
        result = pillar.calculate(prices, fundamentals, empty_ownership, sector_map)
        
        # Should complete successfully with available metrics
        assert len(result) == 1
        
        # Check that weight adjustment occurred
        details = result.iloc[0]['F_details']
        assert details['total_weight_used'] < 1.0  # Less than full weight due to missing metric

    def test_multiple_quarters_takes_latest(self, pillar, sample_sector_map, sample_prices, empty_ownership):
        """Test that latest quarter data is used when multiple quarters available."""
        # Multiple quarters for same ticker
        fundamentals = pd.DataFrame({
            'ticker': ['TEST', 'TEST'],
            'quarter_end': pd.to_datetime(['2023-12-31', '2024-03-31']),
            'roe_3y': [0.10, 0.15],  # Different values
            'sales_cagr_3y': [0.05, 0.08],
            'eps_cagr_3y': [0.08, 0.12],
            'pe': [20.0, 25.0]
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['TEST'],
            'sector_group': ['it']
        })
        
        prices = pd.DataFrame({
            'ticker': ['TEST'],
            'trading_date': pd.to_datetime(['2024-01-01']),
            'close': [1000]
        })
        
        result = pillar.calculate(prices, fundamentals, empty_ownership, sector_map)
        
        # Should use latest quarter (2024-03-31) data
        assert len(result) == 1
        
        # Verify latest data was used by checking if ROE component reflects latest value
        # (This is indirect since we can't directly check raw values after normalization)
        details = result.iloc[0]['F_details']
        assert 'roe_3y' in details['components']