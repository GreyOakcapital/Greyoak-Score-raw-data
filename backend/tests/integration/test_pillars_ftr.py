"""Integration test for F, T, R pillars together."""

from pathlib import Path
import pandas as pd
import pytest

from greyoak_score.core.config_manager import ConfigManager
from greyoak_score.data.ingestion import load_all_data
from greyoak_score.core.data_hygiene import apply_data_hygiene
from greyoak_score.pillars.fundamentals import FundamentalsPillar
from greyoak_score.pillars.technicals import TechnicalsPillar
from greyoak_score.pillars.relative_strength import RelativeStrengthPillar


class TestPillarsFTRIntegration:
    """Test F, T, R pillars working together with real data."""

    @pytest.fixture
    def config_manager(self):
        """Load real configuration."""
        config_dir = Path(__file__).parent.parent.parent / "configs"
        return ConfigManager(config_dir)

    @pytest.fixture
    def real_data(self):
        """Load real CSV data."""
        data_dir = Path(__file__).parent.parent.parent / "data"
        return load_all_data(data_dir)

    @pytest.fixture
    def clean_data(self, real_data):
        """Apply data hygiene to real data."""
        prices_df, fundamentals_df, ownership_df, sector_map_df = real_data
        
        return apply_data_hygiene(
            prices_df, fundamentals_df, ownership_df, sector_map_df
        )

    def test_fundamentals_pillar_with_real_data(self, config_manager, clean_data):
        """Test Fundamentals pillar with real data."""
        clean_prices, clean_fund, clean_own, _, _ = clean_data
        
        # Extract unique sector mapping from clean_prices (which already has sector_group)
        sector_map_df = clean_prices.groupby('ticker')['sector_group'].first().reset_index()
        
        # Remove sector_group from fundamentals to avoid merge conflicts
        clean_fund_no_sector = clean_fund.drop(columns=['sector_group'], errors='ignore')
        clean_own_no_sector = clean_own.drop(columns=['sector_group'], errors='ignore')
        clean_prices_no_sector = clean_prices.drop(columns=['sector_group'], errors='ignore')
        
        # Create pillar
        f_pillar = FundamentalsPillar(config_manager)
        
        # Calculate scores
        result = f_pillar.calculate(
            clean_prices_no_sector, clean_fund_no_sector, clean_own_no_sector, sector_map_df
        )
        
        # Verify results
        assert len(result) > 0
        assert set(result.columns) == {'ticker', 'F_score', 'F_details'}
        
        # Check scores are in valid range
        for score in result['F_score']:
            assert 0 <= score <= 100
        
        # Check we have both banking and non-financial scores
        pillar_types = [details['pillar_type'] for details in result['F_details']]
        assert 'non_financial' in pillar_types  # Should have non-financial stocks
        
        print(f"✅ F Pillar: {len(result)} stocks scored")
        return result

    def test_technicals_pillar_with_real_data(self, config_manager, clean_data):
        """Test Technicals pillar with real data."""
        clean_prices, clean_fund, clean_own, _, _ = clean_data
        sector_map_df = clean_prices.groupby('ticker')['sector_group'].first().reset_index()
        
        # Create pillar
        t_pillar = TechnicalsPillar(config_manager)
        
        # Calculate scores
        result = t_pillar.calculate(
            clean_prices, clean_fund, clean_own, sector_map_df
        )
        
        # Verify results
        assert len(result) > 0
        assert set(result.columns) == {'ticker', 'T_score', 'T_details'}
        
        # Check scores are in valid range
        for score in result['T_score']:
            assert 0 <= score <= 100
        
        # Check all 5 technical components present
        for details in result['T_details']:
            components = details['components']
            expected_components = ['above_200', 'golden_cross', 'rsi', 'breakout', 'volume']
            assert set(components.keys()) == set(expected_components)
        
        print(f"✅ T Pillar: {len(result)} stocks scored")
        return result

    def test_relative_strength_pillar_with_real_data(self, config_manager, clean_data):
        """Test Relative Strength pillar with real data."""
        clean_prices, clean_fund, clean_own, _, _ = clean_data
        sector_map_df = clean_prices.groupby('ticker')['sector_group'].first().reset_index()
        
        # Create pillar
        r_pillar = RelativeStrengthPillar(config_manager)
        
        # Calculate scores
        result = r_pillar.calculate(
            clean_prices, clean_fund, clean_own, sector_map_df
        )
        
        # Verify results
        assert len(result) > 0
        assert set(result.columns) == {'ticker', 'R_score', 'R_details'}
        
        # Check scores are in valid range (should be percentile ranks)
        for score in result['R_score']:
            assert 0 <= score <= 100
        
        # Check alpha calculation details
        for details in result['R_details']:
            assert 'weighted_alpha' in details
            assert 'horizon_alphas' in details
            horizon_alphas = details['horizon_alphas']
            assert set(horizon_alphas.keys()) == {'1M', '3M', '6M'}
        
        print(f"✅ R Pillar: {len(result)} stocks scored")
        return result

    def test_all_three_pillars_together(self, config_manager, clean_data):
        """Test all F, T, R pillars working together."""
        clean_prices, clean_fund, clean_own, _, _ = clean_data
        sector_map_df = clean_prices.groupby('ticker')['sector_group'].first().reset_index()
        
        # Create all three pillars
        f_pillar = FundamentalsPillar(config_manager)
        t_pillar = TechnicalsPillar(config_manager)
        r_pillar = RelativeStrengthPillar(config_manager)
        
        # Calculate all scores
        f_scores = f_pillar.calculate(clean_prices, clean_fund, clean_own, sector_map_df)
        t_scores = t_pillar.calculate(clean_prices, clean_fund, clean_own, sector_map_df)
        r_scores = r_pillar.calculate(clean_prices, clean_fund, clean_own, sector_map_df)
        
        # Check all have same tickers (where data available)
        f_tickers = set(f_scores['ticker'])
        t_tickers = set(t_scores['ticker'])
        r_tickers = set(r_scores['ticker'])
        
        print(f"F Pillar tickers: {len(f_tickers)}")
        print(f"T Pillar tickers: {len(t_tickers)}")
        print(f"R Pillar tickers: {len(r_tickers)}")
        
        # T and R should have same tickers (both use price data)
        assert t_tickers == r_tickers, "T and R pillars should have same tickers"
        
        # F may have fewer tickers if some lack fundamental data
        # But any F tickers should also be in T/R
        common_tickers = f_tickers.intersection(t_tickers)
        assert len(common_tickers) > 0, "Should have some tickers with all F, T, R scores"
        
        # Combine results for common tickers
        combined_results = []
        
        for ticker in common_tickers:
            f_row = f_scores[f_scores['ticker'] == ticker].iloc[0]
            t_row = t_scores[t_scores['ticker'] == ticker].iloc[0]
            r_row = r_scores[r_scores['ticker'] == ticker].iloc[0]
            
            combined_results.append({
                'ticker': ticker,
                'F_score': f_row['F_score'],
                'T_score': t_row['T_score'],
                'R_score': r_row['R_score'],
                'F_details': f_row['F_details'],
                'T_details': t_row['T_details'],
                'R_details': r_row['R_details']
            })
        
        combined_df = pd.DataFrame(combined_results)
        
        # Verify combined results
        assert len(combined_df) > 0
        
        # All scores should be 0-100
        for col in ['F_score', 'T_score', 'R_score']:
            for score in combined_df[col]:
                assert 0 <= score <= 100
        
        print(f"✅ Combined F+T+R: {len(combined_df)} stocks with all three pillar scores")
        
        # Print sample results
        print("\n📊 Sample F+T+R Scores:")
        for _, row in combined_df.head(3).iterrows():
            print(f"  {row['ticker']}: F={row['F_score']:.1f}, T={row['T_score']:.1f}, R={row['R_score']:.1f}")
        
        return combined_df

    def test_pillar_score_distributions(self, config_manager, clean_data):
        """Test that pillar scores have reasonable distributions."""
        clean_prices, clean_fund, clean_own, _, _ = clean_data
        sector_map_df = clean_prices.groupby('ticker')['sector_group'].first().reset_index()
        
        # Get all pillar scores
        f_pillar = FundamentalsPillar(config_manager)
        t_pillar = TechnicalsPillar(config_manager)
        r_pillar = RelativeStrengthPillar(config_manager)
        
        f_scores = f_pillar.calculate(clean_prices, clean_fund, clean_own, sector_map_df)
        t_scores = t_pillar.calculate(clean_prices, clean_fund, clean_own, sector_map_df)
        r_scores = r_pillar.calculate(clean_prices, clean_fund, clean_own, sector_map_df)
        
        # Check score distributions
        for name, scores_df, col in [
            ("Fundamentals", f_scores, "F_score"),
            ("Technicals", t_scores, "T_score"),
            ("Relative Strength", r_scores, "R_score")
        ]:
            scores = scores_df[col].values
            
            # Should have some variation in scores
            assert len(set(scores)) > 1, f"{name} scores should not all be identical"
            
            # Should span a reasonable range
            score_range = scores.max() - scores.min()
            assert score_range > 10, f"{name} scores should span > 10 points (got {score_range:.1f})"
            
            print(f"  {name}: mean={scores.mean():.1f}, std={scores.std():.1f}, range={score_range:.1f}")

    def test_deterministic_pillar_scores(self, config_manager, clean_data):
        """Test that pillar scores are deterministic (same input = same output)."""
        clean_prices, clean_fund, clean_own, _, _ = clean_data
        sector_map_df = clean_prices.groupby('ticker')['sector_group'].first().reset_index()
        
        # Create pillar
        f_pillar = FundamentalsPillar(config_manager)
        
        # Calculate scores twice
        result1 = f_pillar.calculate(clean_prices, clean_fund, clean_own, sector_map_df)
        result2 = f_pillar.calculate(clean_prices, clean_fund, clean_own, sector_map_df)
        
        # Sort both by ticker for comparison
        result1_sorted = result1.sort_values('ticker').reset_index(drop=True)
        result2_sorted = result2.sort_values('ticker').reset_index(drop=True)
        
        # Scores should be identical
        assert len(result1_sorted) == len(result2_sorted)
        assert (result1_sorted['ticker'] == result2_sorted['ticker']).all()
        assert (result1_sorted['F_score'] == result2_sorted['F_score']).all()
        
        print("✅ Pillar scores are deterministic")