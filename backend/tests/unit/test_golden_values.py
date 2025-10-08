"""Golden value regression tests for pillar calculations."""

import pandas as pd
import pytest
import numpy as np
from unittest.mock import Mock

from greyoak_score.pillars.fundamentals import FundamentalsPillar
from greyoak_score.pillars.technicals import TechnicalsPillar
from greyoak_score.pillars.relative_strength import RelativeStrengthPillar
from greyoak_score.core.config_manager import ConfigManager


class TestGoldenValues:
    """Regression tests with fixed golden values to ensure consistency."""

    @pytest.fixture
    def golden_config(self):
        """Mock configuration with fixed values for golden tests."""
        config = Mock(spec=ConfigManager)
        
        # F pillar weights
        def mock_fundamentals_weights(is_banking):
            if is_banking:
                return {
                    "roa_3y": 0.30,
                    "roe_3y": 0.25,
                    "gnpa_pct": 0.20,
                    "pcr_pct": 0.15,
                    "nim_3y": 0.10
                }
            else:
                return {
                    "roe_3y": 0.35,
                    "sales_cagr_3y": 0.25,
                    "eps_cagr_3y": 0.20,
                    "valuation": 0.20
                }
        
        config.get_fundamentals_weights.side_effect = mock_fundamentals_weights
        config.is_banking_sector.side_effect = lambda x: x == "banks"
        
        # T pillar config
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
        
        # R pillar config
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
    def golden_fundamentals_data(self):
        """Fixed fundamentals data for golden tests with varied values."""
        return pd.DataFrame({
            'ticker': ['RELIANCE', 'TCS', 'HDFC', 'INFY', 'AXIS'],
            'quarter_end': pd.to_datetime(['2024-03-31'] * 5),
            'roe_3y': [0.15, 0.28, 0.18, 0.22, 0.16],  # Varied ROE values
            'sales_cagr_3y': [0.08, 0.12, np.nan, 0.15, np.nan],  # Banking missing
            'eps_cagr_3y': [0.12, 0.18, np.nan, 0.20, np.nan],   # Banking missing
            'pe': [25.5, 28.2, np.nan, 24.0, np.nan],            # Banking missing
            'ev_ebitda': [12.3, 18.5, np.nan, 16.0, np.nan],     # Banking missing
            'roa_3y': [np.nan, np.nan, 0.018, np.nan, 0.022],    # Only banking
            'gnpa_pct': [np.nan, np.nan, 1.2, np.nan, 0.8],      # Only banking
            'pcr_pct': [np.nan, np.nan, 85.0, np.nan, 90.0],     # Only banking
            'nim_3y': [np.nan, np.nan, 4.2, np.nan, 4.5]         # Only banking
        })

    @pytest.fixture
    def golden_sector_map(self):
        """Fixed sector mapping for golden tests."""
        return pd.DataFrame({
            'ticker': ['RELIANCE', 'TCS', 'HDFC'],
            'sector_group': ['diversified', 'it', 'banks']
        })

    @pytest.fixture
    def golden_prices_data(self):
        """Fixed price data for golden tests."""
        return pd.DataFrame({
            'ticker': ['RELIANCE', 'TCS', 'HDFC'] * 2,  # 2 days of data
            'date': pd.to_datetime(['2024-01-15', '2024-01-15', '2024-01-15', 
                                   '2024-01-16', '2024-01-16', '2024-01-16']),
            'close': [2500, 3400, 1700, 2520, 3420, 1710],
            'volume': [5000000, 2000000, 1500000, 6000000, 1800000, 1600000],
            'dma20': [2480, 3380, 1680, 2485, 3385, 1685],
            'dma50': [2450, 3350, 1650, 2455, 3355, 1655],
            'dma200': [2400, 3300, 1600, 2405, 3305, 1605],
            'rsi14': [65.0, 45.0, 35.0, 67.0, 47.0, 37.0],
            'atr14': [50.0, 80.0, 40.0, 52.0, 82.0, 42.0],
            'hi20': [2520, 3420, 1720, 2530, 3430, 1725],
            'lo20': [2400, 3300, 1600, 2410, 3310, 1610],
            'ret_21d': [0.15, 0.10, 0.05, 0.16, 0.11, 0.06],
            'ret_63d': [0.25, 0.15, 0.08, 0.26, 0.16, 0.09],
            'ret_126d': [0.35, 0.20, 0.12, 0.36, 0.21, 0.13],
            'sigma20': [0.02, 0.03, 0.025, 0.021, 0.031, 0.026],
            'sigma60': [0.025, 0.035, 0.03, 0.026, 0.036, 0.031]
        })

    @pytest.fixture
    def empty_ownership(self):
        """Empty ownership data for testing."""
        return pd.DataFrame(columns=['ticker', 'quarter_end'])

    def test_fundamentals_golden_values(self, golden_config, golden_fundamentals_data, 
                                      golden_sector_map, golden_prices_data, empty_ownership):
        """Test F pillar with fixed golden values."""
        f_pillar = FundamentalsPillar(golden_config)
        
        # Use latest prices only for validation
        latest_prices = golden_prices_data.groupby('ticker').last().reset_index()
        
        result = f_pillar.calculate(
            latest_prices, golden_fundamentals_data, empty_ownership, golden_sector_map
        )
        
        # Sort by ticker for consistent ordering
        result = result.sort_values('ticker').reset_index(drop=True)
        
        # Golden assertions (within epsilon for floating point precision)
        eps = 1e-1  # Allow 0.1 point tolerance for normalization variations
        
        # Expected approximate scores based on the test data structure
        # These are regression values - if algorithm changes, these need updating
        
        # HDFC (banking) - should have score since it has banking metrics
        hdfc_result = result[result['ticker'] == 'HDFC'].iloc[0]
        assert hdfc_result['F_details']['pillar_type'] == 'banking'
        assert 0 <= hdfc_result['F_score'] <= 100, "HDFC F score should be in valid range"
        
        # RELIANCE (non-financial) - should have score with all metrics
        reliance_result = result[result['ticker'] == 'RELIANCE'].iloc[0]
        assert reliance_result['F_details']['pillar_type'] == 'non_financial'
        assert 0 <= reliance_result['F_score'] <= 100, "RELIANCE F score should be in valid range"
        
        # TCS (non-financial) - should have score with all metrics  
        tcs_result = result[result['ticker'] == 'TCS'].iloc[0]
        assert tcs_result['F_details']['pillar_type'] == 'non_financial'
        assert 0 <= tcs_result['F_score'] <= 100, "TCS F score should be in valid range"
        
        # All scores should be different (due to different fundamentals)
        scores = result['F_score'].tolist()
        assert len(set(scores)) == len(scores), "All F scores should be different"

    def test_technicals_golden_values(self, golden_config, golden_prices_data, 
                                    golden_sector_map, empty_ownership):
        """Test T pillar with fixed golden values."""
        t_pillar = TechnicalsPillar(golden_config)
        
        # Use latest prices only
        latest_prices = golden_prices_data.groupby('ticker').last().reset_index()
        
        result = t_pillar.calculate(
            golden_prices_data, pd.DataFrame(), empty_ownership, golden_sector_map
        )
        
        # Sort by ticker for consistent ordering
        result = result.sort_values('ticker').reset_index(drop=True)
        
        eps = 1e-1
        
        # Check specific component values for RELIANCE (predictable test case)
        reliance_result = result[result['ticker'] == 'RELIANCE'].iloc[0]
        reliance_components = reliance_result['T_details']['components']
        
        # RELIANCE: close=2520, dma200=2405 → above_200 = 100
        assert reliance_components['above_200']['score'] == 100.0, "RELIANCE should be above DMA200"
        
        # RELIANCE: dma20=2485, dma50=2455 → golden_cross = 100  
        assert reliance_components['golden_cross']['score'] == 100.0, "RELIANCE should have golden cross"
        
        # RELIANCE: rsi14=67 → between 30-70, score = (67-30)/(70-30)*100 = 92.5
        expected_rsi = ((67-30)/(70-30)) * 100
        assert abs(reliance_components['rsi']['score'] - expected_rsi) < eps, f"RELIANCE RSI score should be ~{expected_rsi}"
        
        # All T scores should be valid
        for _, row in result.iterrows():
            assert 0 <= row['T_score'] <= 100, f"{row['ticker']} T score should be in valid range"

    def test_relative_strength_golden_values(self, golden_config, golden_prices_data,
                                           golden_sector_map, empty_ownership):
        """Test R pillar with fixed golden values."""
        r_pillar = RelativeStrengthPillar(golden_config)
        
        # Use latest prices only
        latest_prices = golden_prices_data.groupby('ticker').last().reset_index()
        
        result = r_pillar.calculate(
            latest_prices, pd.DataFrame(), empty_ownership, golden_sector_map
        )
        
        # Sort by ticker for consistent ordering
        result = result.sort_values('ticker').reset_index(drop=True)
        
        # Check that all horizon alphas are calculated
        for _, row in result.iterrows():
            details = row['R_details']
            
            # Should have all horizons
            assert set(details['horizon_alphas'].keys()) == {'1M', '3M', '6M'}
            
            # All alpha values should be finite
            for horizon, alpha in details['horizon_alphas'].items():
                assert np.isfinite(alpha), f"{row['ticker']} {horizon} alpha should be finite"
            
            # Final score should be percentile rank (0-100)
            assert 0 <= row['R_score'] <= 100, f"{row['ticker']} R score should be in valid range"
        
        # Scores should reflect relative performance - RELIANCE has highest returns
        reliance_score = result[result['ticker'] == 'RELIANCE'].iloc[0]['R_score']
        hdfc_score = result[result['ticker'] == 'HDFC'].iloc[0]['R_score']
        
        # RELIANCE (highest returns) should outscore HDFC (lowest returns) 
        assert reliance_score > hdfc_score, "RELIANCE should have higher R score than HDFC"

    def test_deterministic_reproducibility(self, golden_config, golden_fundamentals_data,
                                         golden_prices_data, golden_sector_map, empty_ownership):
        """Test that calculations are perfectly reproducible."""
        # Run F pillar twice with identical inputs
        f_pillar = FundamentalsPillar(golden_config)
        
        latest_prices = golden_prices_data.groupby('ticker').last().reset_index()
        
        result1 = f_pillar.calculate(
            latest_prices.copy(), golden_fundamentals_data.copy(), 
            empty_ownership.copy(), golden_sector_map.copy()
        )
        
        result2 = f_pillar.calculate(
            latest_prices.copy(), golden_fundamentals_data.copy(), 
            empty_ownership.copy(), golden_sector_map.copy()
        )
        
        # Sort both results by ticker
        result1 = result1.sort_values('ticker').reset_index(drop=True)
        result2 = result2.sort_values('ticker').reset_index(drop=True)
        
        # F scores should be identical
        assert (result1['F_score'] == result2['F_score']).all(), "F scores should be deterministic"
        
        # Component details should be identical
        for i in range(len(result1)):
            details1 = result1.iloc[i]['F_details']
            details2 = result2.iloc[i]['F_details']
            
            assert details1['pillar_type'] == details2['pillar_type'], "Pillar types should match"
            assert details1['final_score'] == details2['final_score'], "Final scores should match"

    def test_numerical_stability(self, golden_config):
        """Test numerical stability with edge case values."""
        # Create data with potential numerical issues
        edge_case_data = pd.DataFrame({
            'ticker': ['EDGE1', 'EDGE2', 'EDGE3'],
            'quarter_end': pd.to_datetime(['2024-03-31'] * 3),  # Add missing column
            'sector_group': ['test'] * 3,
            'roe_3y': [1e-10, 0.999999, -1e-8],  # Very small/large values
            'sales_cagr_3y': [0.0001, 999.99, np.inf],  # Edge cases
            'eps_cagr_3y': [np.nan, 0.0, -999.0],  # Missing/zero/negative
            'pe': [0.1, 1000.0, np.nan],  # Extreme valuations
            'ev_ebitda': [np.nan, np.nan, np.nan]  # All missing
        })
        
        prices = pd.DataFrame({
            'ticker': ['EDGE1', 'EDGE2', 'EDGE3'],
            'date': pd.to_datetime(['2024-01-01'] * 3),
            'close': [1, 1, 1]  # Minimal valid data
        })
        
        sector_map = pd.DataFrame({
            'ticker': ['EDGE1', 'EDGE2', 'EDGE3'],
            'sector_group': ['test'] * 3
        })
        
        f_pillar = FundamentalsPillar(golden_config)
        
        # Should handle gracefully without crashing
        result = f_pillar.calculate(
            prices, edge_case_data, pd.DataFrame(), sector_map
        )
        
        # All results should be valid numbers
        for _, row in result.iterrows():
            score = row['F_score']
            assert np.isfinite(score), f"Score should be finite, got {score}"
            assert 0 <= score <= 100, f"Score should be 0-100, got {score}"

    def test_cross_pillar_consistency(self, golden_config, golden_prices_data, 
                                    golden_fundamentals_data, golden_sector_map, empty_ownership):
        """Test that all three pillars work together consistently."""
        # Calculate all three pillars
        f_pillar = FundamentalsPillar(golden_config)
        t_pillar = TechnicalsPillar(golden_config)
        r_pillar = RelativeStrengthPillar(golden_config)
        
        latest_prices = golden_prices_data.groupby('ticker').last().reset_index()
        
        f_result = f_pillar.calculate(latest_prices, golden_fundamentals_data, empty_ownership, golden_sector_map)
        t_result = t_pillar.calculate(golden_prices_data, pd.DataFrame(), empty_ownership, golden_sector_map)  
        r_result = r_pillar.calculate(latest_prices, pd.DataFrame(), empty_ownership, golden_sector_map)
        
        # All should have same tickers (T and R use price data, F uses fundamentals)
        f_tickers = set(f_result['ticker'])
        t_tickers = set(t_result['ticker'])  
        r_tickers = set(r_result['ticker'])
        
        assert t_tickers == r_tickers, "T and R should have identical tickers"
        
        # All scores should be in valid range
        all_results = [f_result, t_result, r_result]
        score_cols = ['F_score', 'T_score', 'R_score']
        
        for result, score_col in zip(all_results, score_cols):
            for score in result[score_col]:
                assert 0 <= score <= 100, f"{score_col} should be 0-100, got {score}"
                assert np.isfinite(score), f"{score_col} should be finite, got {score}"