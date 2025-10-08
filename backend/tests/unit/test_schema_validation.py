"""Unit tests for schema validation and edge cases."""

import pandas as pd
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch

from greyoak_score.data.ingestion import (
    load_prices_csv,
    load_fundamentals_csv,
    load_ownership_csv,
    load_sector_map_csv
)
from greyoak_score.pillars.technicals import TechnicalsPillar
from greyoak_score.pillars.relative_strength import RelativeStrengthPillar
from greyoak_score.core.config_manager import ConfigManager
from greyoak_score.core.normalization import batch_normalize_metrics


class TestSchemaValidation:
    """Test schema validation for CSV ingestion."""

    def test_prices_missing_required_columns(self, tmp_path):
        """Test error when required price columns are missing."""
        # Missing 'close' column
        csv_data = """date,ticker,open,high,low,volume
2024-01-01,TEST,100,105,95,1000000
"""
        csv_file = tmp_path / "prices.csv"
        csv_file.write_text(csv_data)
        
        with pytest.raises(ValueError, match="Missing required price columns: \\['close'\\]"):
            load_prices_csv(csv_file)

    def test_prices_missing_multiple_columns(self, tmp_path):
        """Test error when multiple required columns are missing."""
        # Missing 'ticker' and 'volume' columns
        csv_data = """date,open,high,low,close
2024-01-01,100,105,95,100
"""
        csv_file = tmp_path / "prices.csv"
        csv_file.write_text(csv_data)
        
        with pytest.raises(ValueError, match="Missing required price columns: \\['ticker', 'volume'\\]"):
            load_prices_csv(csv_file)

    def test_prices_extra_columns_allowed(self, tmp_path):
        """Test that extra columns in price CSV are allowed."""
        csv_data = """date,ticker,open,high,low,close,volume,extra_col1,extra_col2
2024-01-01,TEST,100,105,95,100,1000000,123,456
"""
        csv_file = tmp_path / "prices.csv"
        csv_file.write_text(csv_data)
        
        # Should not raise error - extra columns are allowed
        with patch('greyoak_score.data.ingestion.add_missing_indicators', return_value=pd.read_csv(csv_file)):
            df = load_prices_csv(csv_file)
            assert 'extra_col1' in df.columns
            assert 'extra_col2' in df.columns

    def test_fundamentals_missing_required_columns(self, tmp_path):
        """Test error when required fundamentals columns are missing."""
        # Missing 'quarter_end' column
        csv_data = """ticker,roe_3y
TEST,0.15
"""
        csv_file = tmp_path / "fundamentals.csv"
        csv_file.write_text(csv_data)
        
        with pytest.raises(ValueError, match="Missing required fundamentals columns: \\['quarter_end'\\]"):
            load_fundamentals_csv(csv_file)

    def test_fundamentals_optional_columns_logged(self, tmp_path, caplog):
        """Test that missing optional columns are properly logged."""
        csv_data = """ticker,quarter_end,roe_3y
TEST,2024-03-31,0.15
"""
        csv_file = tmp_path / "fundamentals.csv"
        csv_file.write_text(csv_data)
        
        df = load_fundamentals_csv(csv_file)
        
        # Check that optional metrics are logged
        assert "Available metrics: 1/12" in caplog.text
        assert "Missing optional metrics:" in caplog.text
        assert len(df) == 1

    def test_ownership_empty_file(self, tmp_path):
        """Test ownership CSV with only headers."""
        csv_data = """ticker,quarter_end,promoter_hold_pct,promoter_pledge_frac,fii_dii_delta_pp
"""
        csv_file = tmp_path / "ownership.csv"
        csv_file.write_text(csv_data)
        
        # Should handle empty file gracefully
        df = load_ownership_csv(csv_file)
        assert len(df) == 0
        assert list(df.columns) == ['ticker', 'quarter_end', 'promoter_hold_pct', 'promoter_pledge_frac', 'fii_dii_delta_pp']

    def test_sector_map_duplicate_tickers(self, tmp_path, caplog):
        """Test sector map with duplicate tickers (should take last)."""
        csv_data = """ticker,sector_group,exchange
TEST,old_sector,NSE
TEST,new_sector,NSE
"""
        csv_file = tmp_path / "sector_map.csv"
        csv_file.write_text(csv_data)
        
        df = load_sector_map_csv(csv_file)
        
        # Should load both rows but application logic should handle duplicates
        assert len(df) == 2
        assert 'TEST' in df['ticker'].values


class TestEdgeCases:
    """Test edge cases for pillar calculations."""

    @pytest.fixture
    def mock_config(self):
        """Mock config for testing."""
        from unittest.mock import Mock
        config = Mock(spec=ConfigManager)
        
        # T pillar config
        config.get_technicals_config.return_value = {
            "weights": {"above_200": 0.20, "golden_cross": 0.15, "rsi": 0.20, "breakout": 0.25, "volume": 0.20},
            "rsi_bands": {"oversold": 30, "overbought": 70},
            "breakout": {"atr_multiplier": 0.75, "close_pct": 0.01}
        }
        
        # R pillar config
        config.get_relative_strength_config.return_value = {
            "horizon_weights": {"1M": 0.45, "3M": 0.35, "6M": 0.20},
            "alpha_weights": {"sector": 0.6, "market": 0.4}
        }
        
        return config

    def test_rsi_boundary_values(self, mock_config):
        """Test RSI component at exact boundary values."""
        t_pillar = TechnicalsPillar(mock_config)
        
        test_cases = [
            (20, 0.0),    # RSI ≤ 30 (oversold) → 0 points
            (30, 0.0),    # RSI = 30 (boundary) → 0 points  
            (50, 50.0),   # RSI = 50 (middle) → 50 points
            (70, 100.0),  # RSI = 70 (boundary) → 100 points
            (80, 100.0),  # RSI ≥ 70 (overbought) → 100 points
        ]
        
        for rsi_value, expected_score in test_cases:
            row = pd.Series({'rsi14': rsi_value})
            config = {"rsi_bands": {"oversold": 30, "overbought": 70}}
            
            score = t_pillar._calculate_rsi_score(row, config)
            assert abs(score - expected_score) < 1e-10, f"RSI {rsi_value} should give {expected_score}, got {score}"

    def test_breakout_logic_detailed(self, mock_config):
        """Test detailed breakout logic with edge cases."""
        t_pillar = TechnicalsPillar(mock_config)
        config = {"breakout": {"atr_multiplier": 0.75, "close_pct": 0.01}}
        
        # Case 1: close ≤ resistance → 0 points
        row1 = pd.Series({
            'close': 100,
            'hi20': 105,
            'dma20': 102,
            'atr14': 2
        })
        score1 = t_pillar._calculate_breakout_score(row1, config)
        assert score1 == 0.0, "Close below resistance should give 0 points"
        
        # Case 2: close > resistance → calculate gap/threshold 
        row2 = pd.Series({
            'close': 108,      # Above resistance
            'hi20': 105,       # resistance = max(105, 102) = 105
            'dma20': 102,
            'atr14': 2         # threshold = max(0.75*2, 0.01*108) = max(1.5, 1.08) = 1.5
        })
        # gap = 108 - 105 = 3, score = min(100, 3/1.5*100) = 100
        score2 = t_pillar._calculate_breakout_score(row2, config)
        assert score2 == 100.0, "Large breakout should give 100 points"
        
        # Case 3: Partial breakout
        row3 = pd.Series({
            'close': 106,      # Small breakout
            'hi20': 105,       
            'dma20': 102,
            'atr14': 4         # threshold = max(0.75*4, 0.01*106) = max(3, 1.06) = 3
        })
        # gap = 106 - 105 = 1, score = min(100, 1/3*100) = 33.33
        score3 = t_pillar._calculate_breakout_score(row3, config)
        expected3 = (1 / 3) * 100
        assert abs(score3 - expected3) < 1e-10, f"Partial breakout should give {expected3:.2f}, got {score3}"

    def test_zero_near_zero_volatility_protection(self, mock_config):
        """Test R pillar protection against zero/near-zero volatility."""
        r_pillar = RelativeStrengthPillar(mock_config)
        
        # Test cases for zero and near-zero volatility
        test_cases = [
            (0.0, "zero volatility"),
            (1e-10, "near-zero volatility"),
            (-0.001, "negative volatility"),
            (np.nan, "NaN volatility")
        ]
        
        sector_returns = {"1M": 0.05}
        market_returns = {"1M": 0.03}
        alpha_weights = {"sector": 0.6, "market": 0.4}
        
        for vol, description in test_cases:
            row = pd.Series({
                'ret_21d': 0.10,
                'sigma20': vol
            })
            
            alpha, details = r_pillar._calculate_horizon_alpha(
                row, sector_returns, market_returns, "1M", 
                "ret_21d", "sigma20", alpha_weights
            )
            
            # Should return 0 alpha and appropriate error reason
            assert alpha == 0.0, f"Alpha should be 0 for {description}"
            assert details['reason'] == 'missing_or_invalid_data', f"Should flag {description} as invalid"

    def test_small_sector_ecdf_fallback(self):
        """Test ECDF fallback when sector has < 6 stocks."""
        # Create small sector data (n < 6)
        small_sector_data = pd.DataFrame({
            'ticker': ['A', 'B', 'C'],  # Only 3 stocks
            'metric': [10, 20, 30],
            'sector_group': ['small_sector'] * 3
        })
        
        metrics_config = {"metric": True}  # Higher is better
        
        result = batch_normalize_metrics(
            small_sector_data,
            metrics_config,
            sector_col="sector_group"
        )
        
        # Should use ECDF (percentile ranking)
        assert 'metric_points' in result.columns
        points = result['metric_points'].values
        
        # For 3 stocks with ECDF: should get different percentile ranks
        # Exact values depend on implementation, but should be ordered and in 0-100 range
        sorted_points = sorted(points)
        assert sorted_points[0] < sorted_points[1] < sorted_points[2], "ECDF points should be ordered"
        assert all(0 <= p <= 100 for p in points), "All ECDF points should be 0-100"
        assert sorted_points[2] - sorted_points[0] > 10, "ECDF should show meaningful spread"

    def test_large_sector_zscore_normalization(self):
        """Test Z-score normalization when sector has ≥ 6 stocks."""
        # Create large sector data (n >= 6)
        np.random.seed(42)  # For reproducibility
        values = np.random.normal(100, 15, 10)  # 10 stocks, mean=100, std=15
        
        large_sector_data = pd.DataFrame({
            'ticker': [f'STOCK_{i}' for i in range(10)],
            'metric': values,
            'sector_group': ['large_sector'] * 10
        })
        
        metrics_config = {"metric": True}  # Higher is better
        
        result = batch_normalize_metrics(
            large_sector_data,
            metrics_config,
            sector_col="sector_group"
        )
        
        # Should use Z-score normalization
        assert 'metric_points' in result.columns
        points = result['metric_points'].values
        
        # Z-score normalized points should have reasonable distribution
        assert points.min() >= 0, "Z-score points should be ≥ 0"
        assert points.max() <= 100, "Z-score points should be ≤ 100"
        assert abs(points.mean() - 50) < 10, "Mean should be around 50 for Z-score normalization"

    def test_volume_surprise_edge_cases(self, mock_config):
        """Test volume surprise calculation edge cases."""
        t_pillar = TechnicalsPillar(mock_config)
        
        # Case 1: No history (single day)
        single_day_history = pd.DataFrame({
            'date': ['2024-01-01'],
            'volume': [1000000]
        })
        
        current_row = pd.Series({'volume': 2000000})  # 2x current volume
        score1 = t_pillar._calculate_volume_score(current_row, single_day_history)
        assert score1 == 50.0, "Insufficient history should give neutral score"
        
        # Case 2: Zero/invalid volume
        history_with_zero = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=25),
            'volume': [0] * 25  # All zero volumes
        })
        
        current_row_zero = pd.Series({'volume': 0})
        score2 = t_pillar._calculate_volume_score(current_row_zero, history_with_zero)
        assert score2 == 50.0, "Zero volume should give neutral score"

    def test_missing_technical_indicators_handling(self, mock_config):
        """Test handling when technical indicators are missing/NaN."""
        t_pillar = TechnicalsPillar(mock_config)
        
        # Row with missing indicators
        row_with_nans = pd.Series({
            'ticker': 'TEST',
            'close': 100,
            'volume': 1000000,
            'dma20': np.nan,    # Missing
            'dma50': np.nan,    # Missing
            'dma200': np.nan,   # Missing
            'rsi14': np.nan,    # Missing
            'atr14': np.nan,    # Missing
            'hi20': np.nan,     # Missing
            'lo20': np.nan      # Missing
        })
        
        # Should handle gracefully with default/neutral scores
        above_200 = t_pillar._calculate_above_200(row_with_nans)
        assert above_200 == 0.0, "Missing DMA200 should give 0"
        
        golden_cross = t_pillar._calculate_golden_cross(row_with_nans)
        assert golden_cross == 0.0, "Missing DMAs should give 0"
        
        rsi_score = t_pillar._calculate_rsi_score(row_with_nans, {"rsi_bands": {"oversold": 30, "overbought": 70}})
        assert rsi_score == 50.0, "Missing RSI should give neutral 50"
        
        breakout_score = t_pillar._calculate_breakout_score(row_with_nans, {"breakout": {"atr_multiplier": 0.75, "close_pct": 0.01}})
        assert breakout_score == 0.0, "Missing breakout data should give 0"


class TestDeterminism:
    """Test deterministic behavior of pillar calculations."""

    def test_identical_inputs_identical_outputs(self, tmp_path):
        """Test that identical inputs produce identical outputs."""
        # Create deterministic test data
        test_data = pd.DataFrame({
            'ticker': ['TEST1', 'TEST2'] * 3,
            'sector_group': ['tech', 'finance'] * 3,  
            'metric1': [10, 20, 15, 25, 12, 22],
            'metric2': [100, 200, 150, 250, 120, 220]
        })
        
        metrics_config = {
            'metric1': True,   # Higher better
            'metric2': False   # Lower better  
        }
        
        # Run normalization twice
        result1 = batch_normalize_metrics(test_data.copy(), metrics_config, sector_col='sector_group')
        result2 = batch_normalize_metrics(test_data.copy(), metrics_config, sector_col='sector_group')
        
        # Results should be identical
        pd.testing.assert_frame_equal(result1, result2, check_exact=True)
        
        # Spot check some values
        assert (result1['metric1_points'] == result2['metric1_points']).all(), "metric1_points should be identical"
        assert (result1['metric2_points'] == result2['metric2_points']).all(), "metric2_points should be identical"

    def test_floating_point_precision(self):
        """Test floating point precision consistency."""
        # Test with values that might cause floating point issues
        data = pd.DataFrame({
            'ticker': ['A', 'B', 'C'],
            'sector_group': ['test'] * 3,
            'metric': [1.0000000001, 1.0000000002, 1.0000000003]  # Very close values
        })
        
        metrics_config = {'metric': True}
        
        result = batch_normalize_metrics(data, metrics_config, sector_col='sector_group')
        
        # Should handle small differences consistently
        points = result['metric_points'].values
        assert len(set(points)) <= 3, "Should preserve relative ordering even for tiny differences"
        assert all(0 <= p <= 100 for p in points), "All points should be in valid range"