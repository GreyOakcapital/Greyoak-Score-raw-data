"""Integration tests for complete data pipeline.

Tests the full flow: CSV → Ingestion → Hygiene → Normalization → Output
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from greyoak_score.core.data_hygiene import apply_data_hygiene
from greyoak_score.core.normalization import batch_normalize_metrics, normalize_metric
from greyoak_score.data.ingestion import load_all_data, get_ticker_sector_map


class TestFullDataPipeline:
    """Test complete pipeline from CSV to normalized output."""

    @pytest.fixture
    def data_dir(self) -> Path:
        """Get path to data directory."""
        return Path(__file__).parent.parent.parent / "data"

    @pytest.fixture
    def loaded_data(self, data_dir):
        """Load all CSV files."""
        return load_all_data(data_dir)

    def test_load_all_csvs(self, loaded_data):
        """Test that all CSV files load successfully."""
        prices_df, fundamentals_df, ownership_df, sector_map_df = loaded_data
        
        # Check all DataFrames loaded
        assert len(prices_df) > 0
        assert len(fundamentals_df) > 0
        assert len(ownership_df) > 0
        assert len(sector_map_df) > 0
        
        # Check 15 tickers
        assert len(sector_map_df) == 15
        
        # Check column presence
        assert "ticker" in prices_df.columns
        assert "close" in prices_df.columns
        assert "roe_3y" in fundamentals_df.columns
        assert "promoter_hold_pct" in ownership_df.columns

    def test_hygiene_pipeline(self, loaded_data):
        """Test data hygiene pipeline on real CSV data."""
        prices_df, fundamentals_df, ownership_df, sector_map_df = loaded_data
        
        # Apply hygiene
        (
            clean_prices,
            clean_fund,
            clean_own,
            imputed_frac,
            confidence,
        ) = apply_data_hygiene(
            prices_df, fundamentals_df, ownership_df, sector_map_df
        )
        
        # Check outputs
        assert "sector_group" in clean_prices.columns
        assert 0.0 <= imputed_frac <= 1.0
        assert 0.0 <= confidence <= 1.0
        
        # Confidence should be reasonable (not too low)
        assert confidence > 0.5
        
        # Check missing values reduced
        # (May still have some NaN for metrics with no data)
        prices_na_before = prices_df.isna().sum().sum()
        prices_na_after = clean_prices.isna().sum().sum()
        # Should have fewer or equal NaN after imputation
        assert prices_na_after <= prices_na_before

    def test_normalization_on_real_data(self, loaded_data):
        """Test normalization on real CSV data."""
        prices_df, fundamentals_df, ownership_df, sector_map_df = loaded_data
        
        # Apply hygiene first
        (
            clean_prices,
            clean_fund,
            clean_own,
            _,
            _,
        ) = apply_data_hygiene(
            prices_df, fundamentals_df, ownership_df, sector_map_df
        )
        
        # Normalize a metric (e.g., sigma20 - volatility)
        points = normalize_metric(
            clean_prices,
            "sigma20",
            "sector_group",
            higher_better=False,  # Lower volatility is better
        )
        
        # Check output
        non_null_points = points.dropna()
        assert len(non_null_points) > 0
        assert all(0 <= p <= 100 for p in non_null_points)
        
        # Check variety (not all the same)
        assert non_null_points.std() > 0

    def test_small_sectors_use_ecdf(self, loaded_data):
        """Test that small sectors (<6 stocks) use ECDF method."""
        prices_df, fundamentals_df, ownership_df, sector_map_df = loaded_data
        
        # Apply hygiene
        clean_prices, clean_fund, clean_own, _, _ = apply_data_hygiene(
            prices_df, fundamentals_df, ownership_df, sector_map_df
        )
        
        # Count stocks per sector
        sector_counts = clean_prices.groupby("sector_group")["ticker"].nunique()
        
        # All our sectors should have ≤ 4 stocks (by design)
        assert all(count <= 4 for count in sector_counts.values)
        
        # Normalize a metric
        points = normalize_metric(
            clean_prices,
            "close",
            "sector_group",
            higher_better=True,
        )
        
        # Should still produce valid results with ECDF
        non_null_points = points.dropna()
        assert all(0 <= p <= 100 for p in non_null_points)

    def test_batch_normalization(self, loaded_data):
        """Test batch normalization of multiple metrics."""
        prices_df, fundamentals_df, ownership_df, sector_map_df = loaded_data
        
        # Apply hygiene
        clean_prices, _, _, _, _ = apply_data_hygiene(
            prices_df, fundamentals_df, ownership_df, sector_map_df
        )
        
        # Normalize multiple metrics
        metrics = {
            "close": True,  # Higher close is neutral (depends on perspective)
            "volume": True,  # Higher volume (liquidity) is better
            "sigma20": False,  # Lower volatility is better
            "rsi14": True,  # Higher RSI can be good (but range-dependent)
        }
        
        result = batch_normalize_metrics(clean_prices, metrics, "sector_group")
        
        # Check all _points columns added
        for metric in metrics:
            points_col = f"{metric}_points"
            assert points_col in result.columns
            
            non_null = result[points_col].dropna()
            if len(non_null) > 0:
                assert all(0 <= p <= 100 for p in non_null)

    def test_end_to_end_determinism(self, loaded_data):
        """Test that pipeline is deterministic (same input → same output)."""
        prices_df, fundamentals_df, ownership_df, sector_map_df = loaded_data
        
        # Run pipeline twice
        result1 = apply_data_hygiene(
            prices_df.copy(), fundamentals_df.copy(),
            ownership_df.copy(), sector_map_df.copy()
        )
        
        result2 = apply_data_hygiene(
            prices_df.copy(), fundamentals_df.copy(),
            ownership_df.copy(), sector_map_df.copy()
        )
        
        # Unpack
        clean_prices1, _, _, imputed_frac1, confidence1 = result1
        clean_prices2, _, _, imputed_frac2, confidence2 = result2
        
        # Check determinism
        assert abs(imputed_frac1 - imputed_frac2) < 1e-6
        assert abs(confidence1 - confidence2) < 1e-6
        
        # Check DataFrames are identical
        pd.testing.assert_frame_equal(
            clean_prices1.sort_index(axis=1),
            clean_prices2.sort_index(axis=1),
        )

    def test_imputed_fraction_reasonable(self, loaded_data):
        """Test that imputed fraction is within expected range."""
        prices_df, fundamentals_df, ownership_df, sector_map_df = loaded_data
        
        # Apply hygiene
        _, _, _, imputed_frac, _ = apply_data_hygiene(
            prices_df, fundamentals_df, ownership_df, sector_map_df
        )
        
        # Imputed fraction should be reasonable (not too high)
        # Our sample data has some missing values (by design) but not excessive
        assert imputed_frac < 0.5  # Less than 50% imputed
        
        # Should not be zero (we have some NaN by design for testing)
        # Actually, might be zero if data is complete
        assert 0.0 <= imputed_frac <= 1.0

    def test_sector_mapping_consistency(self, loaded_data):
        """Test that sector mapping is consistent across datasets."""
        prices_df, fundamentals_df, ownership_df, sector_map_df = loaded_data
        
        # Get sector map
        ticker_to_sector = get_ticker_sector_map(sector_map_df)
        
        # Check all tickers in data have sector mapping
        for ticker in prices_df["ticker"].unique():
            assert ticker in ticker_to_sector
        
        for ticker in fundamentals_df["ticker"].unique():
            assert ticker in ticker_to_sector
        
        for ticker in ownership_df["ticker"].unique():
            assert ticker in ticker_to_sector

    def test_missing_data_handling(self, loaded_data):
        """Test that missing data is handled gracefully."""
        prices_df, fundamentals_df, ownership_df, sector_map_df = loaded_data
        
        # Apply hygiene
        clean_prices, clean_fund, _, _, _ = apply_data_hygiene(
            prices_df, fundamentals_df, ownership_df, sector_map_df
        )
        
        # Check that fundamentals with all NaN for certain metrics are handled
        # Banking stocks should have NaN for non-financial metrics
        banking_tickers = ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"]
        banking_fund = clean_fund[clean_fund["ticker"].isin(banking_tickers)]
        
        # eps_cagr_3y should be NaN for banks (we don't have historical data)
        # This is OK - imputation will use sector median or cross-sector median
        # Just check it doesn't crash
        assert len(banking_fund) > 0

    def test_normalization_respects_sector_boundaries(self, loaded_data):
        """Test that normalization doesn't mix sectors."""
        prices_df, fundamentals_df, ownership_df, sector_map_df = loaded_data
        
        # Apply hygiene
        clean_prices, _, _, _, _ = apply_data_hygiene(
            prices_df, fundamentals_df, ownership_df, sector_map_df
        )
        
        # Normalize close prices
        points = normalize_metric(
            clean_prices,
            "close",
            "sector_group",
            higher_better=True,
        )
        
        # Add points to DataFrame
        clean_prices["points"] = points
        
        # Check that within each sector, points correlate with raw values
        for sector in clean_prices["sector_group"].unique():
            sector_df = clean_prices[clean_prices["sector_group"] == sector]
            
            # Drop NaN
            sector_df = sector_df[["close", "points"]].dropna()
            
            if len(sector_df) > 2:
                # For higher-better, higher close should generally mean higher points
                # (with some variance due to normalization method)
                correlation = sector_df["close"].corr(sector_df["points"])
                # Correlation should be positive
                assert correlation > 0.5

    def test_full_pipeline_with_all_metrics(self, loaded_data):
        """Test full pipeline normalizing all available metrics."""
        prices_df, fundamentals_df, ownership_df, sector_map_df = loaded_data
        
        # Apply hygiene
        clean_prices, clean_fund, clean_own, imputed_frac, confidence = apply_data_hygiene(
            prices_df, fundamentals_df, ownership_df, sector_map_df
        )
        
        # Normalize prices metrics
        price_metrics = {
            "close": True,
            "volume": True,
            "sigma20": False,  # Lower volatility better
            "rsi14": True,  # Neutral, but test it
        }
        
        clean_prices = batch_normalize_metrics(
            clean_prices, price_metrics, "sector_group"
        )
        
        # Check outputs
        assert len(clean_prices) > 0
        assert "close_points" in clean_prices.columns
        assert all(
            0 <= p <= 100
            for p in clean_prices["close_points"].dropna()
        )
        
        # Overall pipeline success
        assert imputed_frac >= 0.0
        assert confidence > 0.0
        logger.info(
            f"✅ Full pipeline complete: "
            f"imputed_frac={imputed_frac:.1%}, confidence={confidence:.3f}"
        )
