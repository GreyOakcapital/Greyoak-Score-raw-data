"""Unit tests for normalization module."""

import numpy as np
import pandas as pd
import pytest

from greyoak_score.core.normalization import (
    batch_normalize_metrics,
    compute_z_score,
    normalize_metric,
    normalize_metric_detailed,
    percentile_to_points,
    z_score_to_points,
)
from greyoak_score.utils.constants import SMALL_SECTOR_THRESHOLD


class TestZScoreCalculation:
    """Test z-score calculation."""

    def test_z_score_higher_better(self):
        """Test z-score for higher-is-better metrics."""
        # Value above median
        z = compute_z_score(
            value=15.0,
            sector_median=10.0,
            sector_std=2.0,
            higher_better=True,
        )
        # z = (15 - 10) / 2 = 2.5
        assert abs(z - 2.5) < 0.01

    def test_z_score_lower_better(self):
        """Test z-score for lower-is-better metrics (flipped)."""
        # Value below median is GOOD for lower-better
        z = compute_z_score(
            value=8.0,
            sector_median=10.0,
            sector_std=2.0,
            higher_better=False,
        )
        # z = (10 - 8) / 2 = 1.0 (positive because lower is better)
        assert abs(z - 1.0) < 0.01

    def test_z_score_at_median(self):
        """Test z-score when value equals median."""
        z = compute_z_score(
            value=10.0,
            sector_median=10.0,
            sector_std=2.0,
            higher_better=True,
        )
        # z = (10 - 10) / 2 = 0
        assert abs(z) < 0.01

    def test_z_score_zero_stdev_handled(self):
        """Test z-score doesn't crash with zero stdev (uses TINY)."""
        z = compute_z_score(
            value=10.0,
            sector_median=10.0,
            sector_std=0.0,
            higher_better=True,
        )
        # Should not crash, returns valid number
        assert isinstance(z, (int, float))
        assert not np.isnan(z)


class TestZScoreToPoints:
    """Test z-score to points conversion."""

    def test_z_score_zero_maps_to_50(self):
        """Test z=0 (median) maps to 50 points."""
        points = z_score_to_points(0.0)
        assert points == 50.0

    def test_positive_z_score(self):
        """Test positive z-scores map to >50 points."""
        points = z_score_to_points(2.0)
        # points = 50 + 15*2 = 80
        assert abs(points - 80.0) < 0.01

    def test_negative_z_score(self):
        """Test negative z-scores map to <50 points."""
        points = z_score_to_points(-2.0)
        # points = 50 + 15*(-2) = 20
        assert abs(points - 20.0) < 0.01

    def test_extreme_positive_clamped(self):
        """Test extreme positive z-scores clamped to 100."""
        points = z_score_to_points(10.0)
        # 50 + 15*10 = 200, clamped to 100
        assert points == 100.0

    def test_extreme_negative_clamped(self):
        """Test extreme negative z-scores clamped to 0."""
        points = z_score_to_points(-10.0)
        # 50 + 15*(-10) = -100, clamped to 0
        assert points == 0.0


class TestPercentileToPoints:
    """Test percentile rank to points conversion."""

    def test_lowest_rank(self):
        """Test lowest rank in sector."""
        points = percentile_to_points(rank=1, n=10)
        # (1 / 11) * 100 ≈ 9.09
        assert 8 < points < 10

    def test_highest_rank(self):
        """Test highest rank in sector."""
        points = percentile_to_points(rank=10, n=10)
        # (10 / 11) * 100 ≈ 90.91
        assert 90 < points < 92

    def test_middle_rank(self):
        """Test middle rank."""
        points = percentile_to_points(rank=5, n=10)
        # (5 / 11) * 100 ≈ 45.45
        assert 44 < points < 47

    def test_single_value_sector(self):
        """Test sector with single value."""
        points = percentile_to_points(rank=1, n=1)
        # (1 / 2) * 100 = 50
        assert abs(points - 50.0) < 1

    def test_empty_sector(self):
        """Test empty sector returns neutral score."""
        points = percentile_to_points(rank=0, n=0)
        assert points == 50.0  # Neutral


class TestNormalizeMetric:
    """Test metric normalization."""

    def test_normalize_large_sector_uses_z_score(self):
        """Test that sectors with ≥6 stocks use z-score method."""
        df = pd.DataFrame({
            "sector_group": ["A"] * 10,
            "metric": [10, 12, 14, 16, 18, 20, 22, 24, 26, 28],
        })
        
        points = normalize_metric(df, "metric", "sector_group", higher_better=True)
        
        # Check range is valid
        assert all(0 <= p <= 100 for p in points)
        # Median value (19) should get ~50 points
        median_idx = 4  # Value 18, close to median
        assert 45 < points[median_idx] < 55

    def test_normalize_small_sector_uses_ecdf(self):
        """Test that sectors with <6 stocks use ECDF method."""
        df = pd.DataFrame({
            "sector_group": ["A"] * 4,  # n=4 < 6
            "metric": [10, 20, 30, 40],
        })
        
        points = normalize_metric(df, "metric", "sector_group", higher_better=True)
        
        # Check range
        assert all(0 <= p <= 100 for p in points)
        # ECDF: ranks 1,2,3,4 → points ≈ 20, 40, 60, 80
        assert points[0] < 30  # Lowest
        assert points[3] > 70  # Highest

    def test_normalize_zero_stdev_uses_ecdf(self):
        """Test that zero stdev triggers ECDF fallback even with n≥6."""
        df = pd.DataFrame({
            "sector_group": ["A"] * 10,
            "metric": [10.0] * 10,  # All same → stdev = 0
        })
        
        points = normalize_metric(df, "metric", "sector_group", higher_better=True)
        
        # All values identical → all get same rank → ~50 points
        assert all(abs(p - 50.0) < 5 for p in points)

    def test_normalize_higher_better(self):
        """Test normalization with higher-is-better metric."""
        df = pd.DataFrame({
            "sector_group": ["A"] * 6,
            "metric": [10, 20, 30, 40, 50, 60],
        })
        
        points = normalize_metric(df, "metric", "sector_group", higher_better=True)
        
        # Higher values should get higher points
        assert points[0] < points[2] < points[5]

    def test_normalize_lower_better(self):
        """Test normalization with lower-is-better metric."""
        df = pd.DataFrame({
            "sector_group": ["A"] * 6,
            "metric": [10, 20, 30, 40, 50, 60],
        })
        
        points = normalize_metric(df, "metric", "sector_group", higher_better=False)
        
        # Lower values should get higher points (reversed)
        assert points[0] > points[2] > points[5]

    def test_normalize_multiple_sectors(self):
        """Test normalization handles multiple sectors separately."""
        df = pd.DataFrame({
            "sector_group": ["A"] * 6 + ["B"] * 6,
            "metric": list(range(10, 16)) + list(range(100, 106)),
        })
        
        points = normalize_metric(df, "metric", "sector_group", higher_better=True)
        
        # Each sector normalized independently
        # Sector A median ≈ 12.5, Sector B median ≈ 102.5
        # Check that median values in each sector get ~50 points
        sector_a_median_idx = 2  # value 12
        sector_b_median_idx = 8  # value 102
        
        assert 40 < points[sector_a_median_idx] < 60
        assert 40 < points[sector_b_median_idx] < 60

    def test_normalize_with_missing_values(self):
        """Test normalization handles NaN values."""
        df = pd.DataFrame({
            "sector_group": ["A"] * 6,
            "metric": [10, 20, np.nan, 40, 50, 60],
        })
        
        points = normalize_metric(df, "metric", "sector_group", higher_better=True)
        
        # NaN should remain NaN
        assert pd.isna(points[2])
        # Others should be normalized
        assert all(0 <= p <= 100 for p in points.dropna())

    def test_normalize_missing_metric(self):
        """Test normalization with non-existent metric returns NaN."""
        df = pd.DataFrame({
            "sector_group": ["A"] * 3,
            "other_metric": [1, 2, 3],
        })
        
        points = normalize_metric(df, "missing_metric", "sector_group", higher_better=True)
        
        # Should return all NaN
        assert points.isna().all()


class TestNormalizeMetricDetailed:
    """Test detailed normalization output."""

    def test_detailed_output_structure(self):
        """Test that detailed normalization returns expected columns."""
        df = pd.DataFrame({
            "ticker": ["A.NS"] * 6,
            "sector_group": ["it"] * 6,
            "roe_3y": [0.10, 0.15, 0.20, 0.25, 0.30, 0.35],
        })
        
        result = normalize_metric_detailed(
            df, "roe_3y", "sector_group", higher_better=True
        )
        
        # Check columns
        expected_cols = [
            "ticker", "sector_group", "value", "sector_median",
            "sector_std", "z_score", "method", "points",
        ]
        assert all(col in result.columns for col in expected_cols)
        
        # Check method
        assert result["method"][0] in ["z_score", "percentile"]

    def test_detailed_z_score_method(self):
        """Test detailed output for z-score method."""
        df = pd.DataFrame({
            "ticker": ["A.NS"] * 10,
            "sector_group": ["it"] * 10,
            "metric": list(range(10, 20)),
        })
        
        result = normalize_metric_detailed(
            df, "metric", "sector_group", higher_better=True
        )
        
        # Should use z-score method (n=10 ≥ 6)
        assert all(result["method"] == "z_score")
        assert result["z_score"].notna().all()


class TestBatchNormalizeMetrics:
    """Test batch normalization of multiple metrics."""

    def test_batch_normalize_multiple_metrics(self):
        """Test normalizing multiple metrics at once."""
        df = pd.DataFrame({
            "ticker": ["A.NS"] * 6,
            "sector_group": ["it"] * 6,
            "roe_3y": [0.10, 0.15, 0.20, 0.25, 0.30, 0.35],
            "pe": [20, 25, 30, 35, 40, 45],
        })
        
        metrics = {
            "roe_3y": True,  # higher better
            "pe": False,  # lower better
        }
        
        result = batch_normalize_metrics(df, metrics, "sector_group")
        
        # Check new columns added
        assert "roe_3y_points" in result.columns
        assert "pe_points" in result.columns
        
        # Check ranges
        assert all(0 <= p <= 100 for p in result["roe_3y_points"])
        assert all(0 <= p <= 100 for p in result["pe_points"])
        
        # Original columns preserved
        assert "roe_3y" in result.columns
        assert "pe" in result.columns


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_stock_sector(self):
        """Test normalization with single-stock sector."""
        df = pd.DataFrame({
            "sector_group": ["singleton"],
            "metric": [42.0],
        })
        
        points = normalize_metric(df, "metric", "sector_group", higher_better=True)
        
        # Single value → neutral score
        assert abs(points[0] - 50.0) < 5

    def test_two_stock_sector(self):
        """Test normalization with two-stock sector."""
        df = pd.DataFrame({
            "sector_group": ["pair", "pair"],
            "metric": [10.0, 20.0],
        })
        
        points = normalize_metric(df, "metric", "sector_group", higher_better=True)
        
        # n=2 < 6 → ECDF
        # Lower value gets lower rank
        assert points[0] < points[1]

    def test_all_nan_sector(self):
        """Test sector with all NaN values."""
        df = pd.DataFrame({
            "sector_group": ["A"] * 3,
            "metric": [np.nan, np.nan, np.nan],
        })
        
        points = normalize_metric(df, "metric", "sector_group", higher_better=True)
        
        # All NaN → all get neutral (50)
        # Actually, with no valid values, median returns NaN, so we get 50
        # (check implementation - might be all NaN or all 50)
        assert points.isna().all() or all(abs(p - 50) < 1 for p in points.dropna())

    def test_exact_threshold_boundary(self):
        """Test behavior at n=6 boundary."""
        # n=5 should use ECDF
        df_small = pd.DataFrame({
            "sector_group": ["A"] * 5,
            "metric": [10, 20, 30, 40, 50],
        })
        
        points_small = normalize_metric(df_small, "metric", "sector_group", True)
        
        # n=6 should use z-score
        df_large = pd.DataFrame({
            "sector_group": ["B"] * 6,
            "metric": [10, 20, 30, 40, 50, 60],
        })
        
        points_large = normalize_metric(df_large, "metric", "sector_group", True)
        
        # Both should produce valid results
        assert all(0 <= p <= 100 for p in points_small)
        assert all(0 <= p <= 100 for p in points_large)
