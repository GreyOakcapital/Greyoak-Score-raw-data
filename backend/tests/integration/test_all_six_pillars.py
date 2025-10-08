"""Integration test for all 6 pillars (F, T, R, O, Q, S) working together."""

from pathlib import Path
import pandas as pd
import pytest
import numpy as np

from greyoak_score.core.config_manager import ConfigManager
from greyoak_score.data.ingestion import load_all_data
from greyoak_score.core.data_hygiene import apply_data_hygiene
from greyoak_score.pillars.fundamentals import FundamentalsPillar
from greyoak_score.pillars.technicals import TechnicalsPillar
from greyoak_score.pillars.relative_strength import RelativeStrengthPillar
from greyoak_score.pillars.ownership import OwnershipPillar
from greyoak_score.pillars.quality import QualityPillar
from greyoak_score.pillars.sector_momentum import SectorMomentumPillar


class TestAllSixPillars:
    """Test all 6 pillars (F, T, R, O, Q, S) working together with real data."""

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

    def test_all_six_pillars_with_real_data(self, config_manager, clean_data):
        """Test all 6 pillars working together with real data."""
        clean_prices, clean_fund, clean_own, _, _ = clean_data
        
        # Extract sector mapping (without duplicated sector_group column)
        sector_map_df = clean_prices.groupby('ticker')['sector_group'].first().reset_index()
        
        # Remove sector_group from data to avoid merge conflicts
        clean_prices_no_sector = clean_prices.drop(columns=['sector_group'], errors='ignore')
        clean_fund_no_sector = clean_fund.drop(columns=['sector_group'], errors='ignore')
        clean_own_no_sector = clean_own.drop(columns=['sector_group'], errors='ignore')
        
        # Create all 6 pillars
        f_pillar = FundamentalsPillar(config_manager)
        t_pillar = TechnicalsPillar(config_manager)
        r_pillar = RelativeStrengthPillar(config_manager)
        o_pillar = OwnershipPillar(config_manager)
        q_pillar = QualityPillar(config_manager)
        s_pillar = SectorMomentumPillar(config_manager)
        
        # Calculate all pillar scores
        print("\n🔄 Calculating all 6 pillars...")
        
        f_scores = f_pillar.calculate(clean_prices_no_sector, clean_fund_no_sector, clean_own_no_sector, sector_map_df)
        print(f"  ✅ F Pillar: {len(f_scores)} stocks")
        
        t_scores = t_pillar.calculate(clean_prices_no_sector, clean_fund_no_sector, clean_own_no_sector, sector_map_df)
        print(f"  ✅ T Pillar: {len(t_scores)} stocks")
        
        r_scores = r_pillar.calculate(clean_prices_no_sector, clean_fund_no_sector, clean_own_no_sector, sector_map_df)
        print(f"  ✅ R Pillar: {len(r_scores)} stocks")
        
        o_scores = o_pillar.calculate(clean_prices_no_sector, clean_fund_no_sector, clean_own_no_sector, sector_map_df)
        print(f"  ✅ O Pillar: {len(o_scores)} stocks")
        
        q_scores = q_pillar.calculate(clean_prices_no_sector, clean_fund_no_sector, clean_own_no_sector, sector_map_df)
        print(f"  ✅ Q Pillar: {len(q_scores)} stocks")
        
        s_scores = s_pillar.calculate(clean_prices_no_sector, clean_fund_no_sector, clean_own_no_sector, sector_map_df)
        print(f"  ✅ S Pillar: {len(s_scores)} stocks (with S_z tracking)")
        
        # Verify all pillars return proper structure
        pillar_results = [
            ("F", f_scores, ['ticker', 'F_score', 'F_details']),
            ("T", t_scores, ['ticker', 'T_score', 'T_details']),
            ("R", r_scores, ['ticker', 'R_score', 'R_details']),
            ("O", o_scores, ['ticker', 'O_score', 'O_details']),
            ("Q", q_scores, ['ticker', 'Q_score', 'Q_details']),
            ("S", s_scores, ['ticker', 'S_score', 'S_z', 'S_details'])  # S has extra S_z column
        ]
        
        for name, scores, expected_cols in pillar_results:
            assert len(scores) > 0, f"{name} pillar should return results"
            assert list(scores.columns) == expected_cols, f"{name} pillar columns incorrect"
            
            # Check all scores are 0-100
            score_col = f"{name}_score"
            for score in scores[score_col]:
                assert 0 <= score <= 100, f"{name} pillar score {score} not in 0-100 range"

        # CRITICAL: Verify S_z tracking
        assert 'S_z' in s_scores.columns, "S pillar must include S_z column for guardrails"
        for s_z in s_scores['S_z']:
            assert np.isfinite(s_z), "All S_z values must be finite"

        # Check ticker overlap
        all_tickers = {
            'F': set(f_scores['ticker']),
            'T': set(t_scores['ticker']),
            'R': set(r_scores['ticker']),
            'O': set(o_scores['ticker']),
            'Q': set(q_scores['ticker']),
            'S': set(s_scores['ticker'])
        }
        
        print(f"\n📊 Ticker Coverage:")
        for pillar, tickers in all_tickers.items():
            print(f"  {pillar}: {len(tickers)} tickers")
        
        # T, R, S should have same tickers (all use price data)
        price_pillars = ['T', 'R', 'S']
        price_tickers = [all_tickers[p] for p in price_pillars]
        assert all(t == price_tickers[0] for t in price_tickers), "T, R, S should have identical tickers"
        
        # Find common tickers across all 6 pillars
        common_tickers = set.intersection(*all_tickers.values())
        assert len(common_tickers) > 0, "Should have some tickers with all 6 pillar scores"
        
        print(f"  📈 Common across all 6 pillars: {len(common_tickers)} tickers")
        
        return {
            'F': f_scores,
            'T': t_scores,
            'R': r_scores,
            'O': o_scores,
            'Q': q_scores,
            'S': s_scores,
            'common_tickers': common_tickers
        }

    def test_pillar_score_ranges_and_distributions(self, config_manager, clean_data):
        """Test that all pillars produce reasonable score distributions."""
        results = self.test_all_six_pillars_with_real_data(config_manager, clean_data)
        
        print(f"\n📈 Pillar Score Distributions:")
        
        for pillar_name in ['F', 'T', 'R', 'O', 'Q', 'S']:
            scores_df = results[pillar_name]
            score_col = f"{pillar_name}_score"
            scores = scores_df[score_col].values
            
            # Statistical checks
            score_range = scores.max() - scores.min()
            score_std = scores.std()
            
            print(f"  {pillar_name}: mean={scores.mean():.1f}, std={score_std:.1f}, range={score_range:.1f}")
            
            # Each pillar should have some variation
            assert score_range > 5, f"{pillar_name} pillar should show score variation > 5 points"
            assert len(set(scores)) > 1, f"{pillar_name} pillar should not have identical scores"
            
            # All scores should be valid
            assert all(0 <= s <= 100 for s in scores), f"{pillar_name} scores should be 0-100"
            assert not np.isnan(scores).any(), f"{pillar_name} should not have NaN scores"

    def test_s_z_tracking_validation(self, config_manager, clean_data):
        """CRITICAL: Validate S_z tracking for guardrails system."""
        results = self.test_all_six_pillars_with_real_data(config_manager, clean_data)
        
        s_scores = results['S']
        
        print(f"\n📊 S_z Validation:")
        s_z_values = s_scores['S_z'].values
        
        print(f"  S_z range: [{s_z_values.min():.2f}, {s_z_values.max():.2f}]")
        print(f"  S_z mean: {s_z_values.mean():.2f}, std: {s_z_values.std():.2f}")
        
        # CRITICAL validations for guardrails
        assert not np.isnan(s_z_values).any(), "S_z values must not be NaN"
        assert np.isfinite(s_z_values).all(), "S_z values must be finite"
        
        # S_z should be z-scores (typically -3 to +3, but allow wider range)
        assert all(-10 <= s_z <= 10 for s_z in s_z_values), "S_z should be in reasonable z-score range"
        
        # Check S_z by sector
        sector_s_z = {}
        for _, row in s_scores.iterrows():
            sector = row['S_details']['sector_group']
            if sector not in sector_s_z:
                sector_s_z[sector] = []
            sector_s_z[sector].append(row['S_z'])
        
        print(f"  S_z by sector:")
        for sector, s_z_list in sector_s_z.items():
            mean_s_z = np.mean(s_z_list)
            print(f"    {sector}: {mean_s_z:.2f}")
        
        # Should have different S_z across sectors (cross-sector normalization)
        sector_means = [np.mean(s_z_list) for s_z_list in sector_s_z.values()]
        s_z_range = max(sector_means) - min(sector_means)
        assert s_z_range > 0.1, "Should have S_z variation across sectors"

    def test_combined_pillar_matrix(self, config_manager, clean_data):
        """Test creating combined pillar score matrix."""
        results = self.test_all_six_pillars_with_real_data(config_manager, clean_data)
        
        common_tickers = results['common_tickers']
        
        # Create combined matrix for common tickers
        combined_data = []
        
        for ticker in common_tickers:
            row_data = {'ticker': ticker}
            
            # Add scores from all pillars
            for pillar_name in ['F', 'T', 'R', 'O', 'Q', 'S']:
                pillar_df = results[pillar_name]
                ticker_row = pillar_df[pillar_df['ticker'] == ticker].iloc[0]
                
                score_col = f"{pillar_name}_score"
                row_data[score_col] = ticker_row[score_col]
                
                # Add S_z for S pillar
                if pillar_name == 'S':
                    row_data['S_z'] = ticker_row['S_z']
            
            combined_data.append(row_data)
        
        combined_df = pd.DataFrame(combined_data)
        
        print(f"\n🎯 Combined 6-Pillar Matrix ({len(combined_df)} stocks):")
        print("Sample scores:")
        
        for _, row in combined_df.head(3).iterrows():
            ticker = row['ticker']
            scores_str = f"F={row['F_score']:.1f}, T={row['T_score']:.1f}, R={row['R_score']:.1f}, O={row['O_score']:.1f}, Q={row['Q_score']:.1f}, S={row['S_score']:.1f}"
            s_z_str = f"S_z={row['S_z']:.2f}"
            print(f"  {ticker}: {scores_str}, {s_z_str}")
        
        # Validate combined matrix
        assert len(combined_df) > 0, "Should have stocks with all 6 pillar scores"
        
        # Check all score columns present
        expected_cols = ['ticker', 'F_score', 'T_score', 'R_score', 'O_score', 'Q_score', 'S_score', 'S_z']
        assert all(col in combined_df.columns for col in expected_cols), "Combined matrix missing columns"
        
        # Check all scores are valid
        for col in ['F_score', 'T_score', 'R_score', 'O_score', 'Q_score', 'S_score']:
            scores = combined_df[col]
            assert all(0 <= s <= 100 for s in scores), f"{col} should be 0-100"
        
        return combined_df

    def test_pillar_determinism_all_six(self, config_manager, clean_data):
        """Test that all 6 pillars are deterministic."""
        clean_prices, clean_fund, clean_own, _, _ = clean_data
        sector_map_df = clean_prices.groupby('ticker')['sector_group'].first().reset_index()
        
        # Remove sector_group to avoid conflicts
        clean_prices_no_sector = clean_prices.drop(columns=['sector_group'], errors='ignore')
        clean_fund_no_sector = clean_fund.drop(columns=['sector_group'], errors='ignore')
        clean_own_no_sector = clean_own.drop(columns=['sector_group'], errors='ignore')
        
        # Create pillar instances
        pillars = {
            'F': FundamentalsPillar(config_manager),
            'T': TechnicalsPillar(config_manager),
            'R': RelativeStrengthPillar(config_manager),
            'O': OwnershipPillar(config_manager),
            'Q': QualityPillar(config_manager),
            'S': SectorMomentumPillar(config_manager)
        }
        
        # Run each pillar twice and check for identical results
        for pillar_name, pillar_instance in pillars.items():
            print(f"\n🔄 Testing {pillar_name} pillar determinism...")
            
            # Run twice with identical inputs
            result1 = pillar_instance.calculate(
                clean_prices_no_sector.copy(), 
                clean_fund_no_sector.copy(), 
                clean_own_no_sector.copy(), 
                sector_map_df.copy()
            )
            
            result2 = pillar_instance.calculate(
                clean_prices_no_sector.copy(), 
                clean_fund_no_sector.copy(), 
                clean_own_no_sector.copy(), 
                sector_map_df.copy()
            )
            
            # Sort both results by ticker for comparison
            result1_sorted = result1.sort_values('ticker').reset_index(drop=True)
            result2_sorted = result2.sort_values('ticker').reset_index(drop=True)
            
            # Check identical results
            assert len(result1_sorted) == len(result2_sorted), f"{pillar_name} pillar should return same number of results"
            
            score_col = f"{pillar_name}_score"
            scores1 = result1_sorted[score_col].values
            scores2 = result2_sorted[score_col].values
            
            assert np.array_equal(scores1, scores2), f"{pillar_name} pillar scores should be deterministic"
            
            # For S pillar, also check S_z determinism
            if pillar_name == 'S':
                s_z1 = result1_sorted['S_z'].values
                s_z2 = result2_sorted['S_z'].values
                assert np.array_equal(s_z1, s_z2), "S pillar S_z values should be deterministic"
            
            print(f"  ✅ {pillar_name} pillar is deterministic")

    def test_performance_benchmark(self, config_manager, clean_data):
        """Test performance of all 6 pillars together."""
        import time
        
        results = {}
        clean_prices, clean_fund, clean_own, _, _ = clean_data
        sector_map_df = clean_prices.groupby('ticker')['sector_group'].first().reset_index()
        
        # Remove sector_group to avoid conflicts
        clean_prices_no_sector = clean_prices.drop(columns=['sector_group'], errors='ignore')
        clean_fund_no_sector = clean_fund.drop(columns=['sector_group'], errors='ignore')  
        clean_own_no_sector = clean_own.drop(columns=['sector_group'], errors='ignore')
        
        pillars = {
            'F': FundamentalsPillar(config_manager),
            'T': TechnicalsPillar(config_manager), 
            'R': RelativeStrengthPillar(config_manager),
            'O': OwnershipPillar(config_manager),
            'Q': QualityPillar(config_manager),
            'S': SectorMomentumPillar(config_manager)
        }
        
        print(f"\n⏱️ Performance Benchmark ({len(clean_prices_no_sector)} records):")
        
        total_start = time.time()
        
        for pillar_name, pillar_instance in pillars.items():
            start_time = time.time()
            
            result = pillar_instance.calculate(
                clean_prices_no_sector, clean_fund_no_sector, clean_own_no_sector, sector_map_df
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            results[pillar_name] = {
                'duration': duration,
                'stocks_scored': len(result),
                'throughput': len(result) / duration if duration > 0 else float('inf')
            }
            
            print(f"  {pillar_name}: {duration:.3f}s ({results[pillar_name]['throughput']:.1f} stocks/sec)")
        
        total_duration = time.time() - total_start
        total_stocks = sum(r['stocks_scored'] for r in results.values())
        
        print(f"  Total: {total_duration:.3f}s ({total_stocks/total_duration:.1f} stocks/sec)")
        
        # Performance assertions (generous limits for testing environment)
        assert total_duration < 30, "All 6 pillars should complete within 30 seconds"
        
        for pillar_name, metrics in results.items():
            assert metrics['duration'] < 10, f"{pillar_name} pillar should complete within 10 seconds"