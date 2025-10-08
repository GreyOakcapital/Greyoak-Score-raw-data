"""Unit tests for data hygiene module."""

import numpy as np
import pandas as pd
import pytest
from datetime import date, timedelta

from greyoak_score.core.data_hygiene import (
    apply_data_hygiene,
    calculate_confidence,
    calculate_coverage,
    impute_missing,
    validate_freshness,
    winsorize_by_sector,
)


class TestWinsorization:
    """Test winsorization functionality."""

    def test_winsorize_caps_outliers(self):
        """Test that winsorization caps extreme values at 1% and 99%."""
        # Create data with outliers
        df = pd.DataFrame({
            "sector_group": ["A"] * 100,
            "metric": list(range(100)),  # 0 to 99
        })
        
        result = winsorize_by_sector(df, "sector_group", ["metric"])
        
        # 1st percentile ≈ 0.99, 99th percentile ≈ 98.01
        # Values 0 and 99 should be capped to these percentiles
        assert result["metric"].min() >= 0.9  # Allow some tolerance
        assert result["metric"].max() <= 98.1
        # Most values should be unchanged
        assert (result["metric"] == df["metric"]).sum() > 90

    def test_winsorize_by_sector_separate(self):
        """Test that winsorization is done separately per sector."""
        df = pd.DataFrame({
            "sector_group": ["A"] * 50 + ["B"] * 50,
            "metric": list(range(50)) + list(range(100, 150)),
        })
        
        result = winsorize_by_sector(df, "sector_group", ["metric"])
        
        # Sector A: range 0-49, winsorized to ~0.49-48.51
        sector_a = result[result["sector_group"] == "A"]
        assert sector_a["metric"].min() >= 0.4  # Allow tolerance
        assert sector_a["metric"].max() <= 48.6
        
        # Sector B: range 100-149, winsorized to ~101-148
        sector_b = result[result["sector_group"] == "B"]
        assert sector_b["metric"].min() >= 101
        assert sector_b["metric"].max() <= 148

    def test_winsorize_small_sector(self):
        """Test winsorization with very small sector (< 2 values)."""
        df = pd.DataFrame({
            "sector_group": ["A"],
            "metric": [10.0],
        })
        
        # Should not crash, value should be unchanged
        result = winsorize_by_sector(df, "sector_group", ["metric"])
        assert result["metric"][0] == 10.0


class TestImputation:
    """Test missing data imputation."""

    def test_impute_with_sector_median(self):
        """Test that missing values are imputed with sector median."""
        df = pd.DataFrame({
            "sector_group": ["A", "A", "A", "A"],
            "metric": [10.0, 20.0, np.nan, 30.0],
        })
        
        result, imputed_frac = impute_missing(df, "sector_group", ["metric"])
        
        # NaN should be replaced with median of sector A (median of 10, 20, 30 = 20)
        assert result["metric"].isna().sum() == 0
        assert result.loc[2, "metric"] == 20.0
        # 1 out of 4 values imputed = 0.25
        assert 0.2 < imputed_frac < 0.3

    def test_impute_multiple_sectors(self):
        """Test imputation uses correct sector median for each sector."""
        df = pd.DataFrame({
            "sector_group": ["A", "A", "B", "B"],
            "metric": [10.0, np.nan, 100.0, np.nan],
        })
        
        result, _ = impute_missing(df, "sector_group", ["metric"])
        
        # Sector A: median = 10, so NaN → 10
        assert result.loc[1, "metric"] == 10.0
        # Sector B: median = 100, so NaN → 100
        assert result.loc[3, "metric"] == 100.0

    def test_imputed_fraction_calculation(self):
        """Test imputed_fraction calculation."""
        df = pd.DataFrame({
            "sector_group": ["A"] * 10,
            "metric1": [1.0] * 7 + [np.nan] * 3,  # 3 missing
            "metric2": [1.0] * 9 + [np.nan] * 1,  # 1 missing
        })
        
        _, imputed_frac = impute_missing(df, "sector_group", ["metric1", "metric2"])
        
        # Total: 20 cells, 4 imputed = 0.20
        assert abs(imputed_frac - 0.20) < 0.01

    def test_impute_all_missing_in_sector(self):
        """Test imputation when entire sector has missing values."""
        df = pd.DataFrame({
            "sector_group": ["A", "A", "B", "B"],
            "metric": [np.nan, np.nan, 10.0, 20.0],
        })
        
        result, _ = impute_missing(df, "sector_group", ["metric"])
        
        # Sector A has no valid values, should use cross-sector median (15.0)
        assert result.loc[0, "metric"] == 15.0
        assert result.loc[1, "metric"] == 15.0


class TestConfidenceCalculation:
    """Test confidence score calculation."""

    def test_confidence_formula(self):
        """Test confidence calculation formula."""
        # Perfect data: fresh, complete, primary source
        confidence = calculate_confidence(
            data_freshness={"prices": 0, "fundamentals": 0, "ownership": 0},
            coverage=1.0,
            source_penalty=0.0,
        )
        
        # confidence = 0.55 * 1.0 + 0.35 * 1.0 + 0.10 * 1.0 = 1.0
        assert confidence == 1.0

    def test_confidence_with_stale_data(self):
        """Test confidence decreases with stale data."""
        # Fresh data
        conf_fresh = calculate_confidence(
            data_freshness={"prices": 0, "fundamentals": 0},
            coverage=1.0,
            source_penalty=0.0,
        )
        
        # Stale data (120 days old for fundamentals)
        conf_stale = calculate_confidence(
            data_freshness={"prices": 0, "fundamentals": 120},
            coverage=1.0,
            source_penalty=0.0,
            freshness_slos={"prices": 1, "fundamentals": 120},
        )
        
        # Stale should have lower confidence
        assert conf_stale < conf_fresh

    def test_confidence_with_missing_data(self):
        """Test confidence decreases with missing data."""
        # Complete data
        conf_complete = calculate_confidence(
            data_freshness={"prices": 0},
            coverage=1.0,
            source_penalty=0.0,
        )
        
        # Incomplete data
        conf_incomplete = calculate_confidence(
            data_freshness={"prices": 0},
            coverage=0.5,
            source_penalty=0.0,
        )
        
        assert conf_incomplete < conf_complete

    def test_confidence_with_secondary_source(self):
        """Test confidence penalty for secondary data sources."""
        # Primary source
        conf_primary = calculate_confidence(
            data_freshness={"prices": 0},
            coverage=1.0,
            source_penalty=0.0,
        )
        
        # Secondary source
        conf_secondary = calculate_confidence(
            data_freshness={"prices": 0},
            coverage=1.0,
            source_penalty=0.15,
        )
        
        assert conf_secondary < conf_primary

    def test_confidence_clamped_to_valid_range(self):
        """Test confidence is clamped to [0, 1]."""
        # Worst case
        conf_worst = calculate_confidence(
            data_freshness={"prices": 1000, "fundamentals": 1000},
            coverage=0.0,
            source_penalty=1.0,
        )
        
        assert 0.0 <= conf_worst <= 1.0


class TestCoverageCalculation:
    """Test data coverage calculation."""

    def test_coverage_full(self):
        """Test coverage with no missing values."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": [4, 5, 6],
        })
        
        coverage = calculate_coverage(df, ["col1", "col2"])
        assert coverage == 1.0

    def test_coverage_partial(self):
        """Test coverage with some missing values."""
        df = pd.DataFrame({
            "col1": [1, np.nan, 3],
            "col2": [4, 5, 6],
        })
        
        coverage = calculate_coverage(df, ["col1", "col2"])
        # 5 out of 6 values present = 0.833...
        assert 0.8 < coverage < 0.9

    def test_coverage_empty_required_cols(self):
        """Test coverage with no required columns."""
        df = pd.DataFrame({"col1": [1, 2, 3]})
        
        coverage = calculate_coverage(df, [])
        assert coverage == 1.0  # No requirements = 100% coverage


class TestFreshnessValidation:
    """Test data freshness validation."""

    def test_fresh_data_passes(self):
        """Test that fresh data passes validation."""
        data_date = date.today()
        as_of_date = date.today()
        
        is_fresh = validate_freshness(data_date, as_of_date, slo_days=1)
        assert is_fresh is True

    def test_stale_data_fails(self):
        """Test that stale data fails validation."""
        data_date = date.today() - timedelta(days=10)
        as_of_date = date.today()
        
        is_fresh = validate_freshness(data_date, as_of_date, slo_days=1)
        assert is_fresh is False

    def test_boundary_case(self):
        """Test freshness at exact SLO boundary."""
        data_date = date.today() - timedelta(days=7)
        as_of_date = date.today()
        
        # Exactly at SLO
        is_fresh = validate_freshness(data_date, as_of_date, slo_days=7)
        assert is_fresh is True
        
        # Just over SLO
        is_fresh = validate_freshness(data_date, as_of_date, slo_days=6)
        assert is_fresh is False


class TestApplyDataHygiene:
    """Test complete data hygiene pipeline."""

    def test_full_pipeline(self):
        """Test end-to-end data hygiene pipeline."""
        # Create sample data
        prices_df = pd.DataFrame({
            "ticker": ["A.NS"] * 10 + ["B.NS"] * 10,
            "date": [date.today()] * 20,
            "close": list(range(10)) + list(range(100, 110)),
            "volume": [1e6] * 20,
            "sigma20": [0.02] * 18 + [np.nan, np.nan],  # 2 missing
        })
        
        fundamentals_df = pd.DataFrame({
            "ticker": ["A.NS", "B.NS"],
            "quarter_end": [date.today()] * 2,
            "roe_3y": [0.15, 0.20],
        })
        
        ownership_df = pd.DataFrame({
            "ticker": ["A.NS", "B.NS"],
            "quarter_end": [date.today()] * 2,
            "promoter_hold_pct": [0.50, 0.60],
            "promoter_pledge_frac": [0.0, 0.0],
            "fii_dii_delta_pp": [0.0, 0.0],
        })
        
        sector_map_df = pd.DataFrame({
            "ticker": ["A.NS", "B.NS"],
            "sector_id": ["SECTOR_A", "SECTOR_B"],
            "sector_group": ["it", "metals"],
        })
        
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
        
        # Assertions
        assert "sector_group" in clean_prices.columns
        assert clean_prices["sigma20"].isna().sum() == 0  # Missing values imputed
        assert 0.0 <= imputed_frac <= 1.0
        assert 0.0 <= confidence <= 1.0
        
        # Imputed fraction should be low (only 2 out of many values missing)
        assert imputed_frac < 0.2
