"""Unit tests for Risk Penalty Calculator (core/risk_penalty.py)."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

from greyoak_score.core.config_manager import ConfigManager
from greyoak_score.core.risk_penalty import (
    calculate_risk_penalty,
    _calculate_liquidity_penalty,
    _calculate_pledge_penalty, 
    _calculate_volatility_penalty,
    _calculate_event_penalty,
    _calculate_governance_penalty,
    get_risk_penalty_summary
)


@pytest.fixture
def config_manager():
    """Get test config manager."""
    config_dir = Path(__file__).parent.parent.parent / "configs"
    return ConfigManager(config_dir)


@pytest.fixture
def sample_prices_data():
    """Sample price/technical data."""
    return pd.Series({
        'close': 2500.0,
        'volume': 1000000,
        'median_traded_value_cr': 3.5,  # ₹3.5 Cr MTV
        'sigma20': 0.025  # 2.5% volatility
    })


@pytest.fixture
def sample_fundamentals_data():
    """Sample fundamentals data."""
    return pd.Series({
        'roe_3y': 0.15,  # 15% ROE
        'quarter_end': '2024-09-30',
        'opm_stdev_12q': 0.08  # 8% OPM volatility
    })


@pytest.fixture
def sample_ownership_data():
    """Sample ownership data.""" 
    return pd.Series({
        'promoter_pledge_frac': 0.05  # 5% pledge
    })


class TestRiskPenaltyCalculator:
    """Test the main risk penalty calculation function."""
    
    def test_calculate_risk_penalty_basic(self, config_manager, sample_prices_data, 
                                        sample_fundamentals_data, sample_ownership_data):
        """Test basic risk penalty calculation."""
        total_rp, breakdown = calculate_risk_penalty(
            ticker="TESTSTOCK",
            prices_data=sample_prices_data,
            fundamentals_data=sample_fundamentals_data,
            ownership_data=sample_ownership_data,
            sector_group="it",
            mode="trader",
            config=config_manager
        )
        
        # Check return types
        assert isinstance(total_rp, float)
        assert isinstance(breakdown, dict)
        
        # Check breakdown keys
        expected_keys = {
            'liquidity', 'pledge', 'volatility', 'event', 'governance',
            'total_before_cap', 'sector_cap', 'total_after_cap'
        }
        assert set(breakdown.keys()) == expected_keys
        
        # Check bounds
        assert 0 <= total_rp <= 20
        assert breakdown['total_after_cap'] == total_rp
    
    def test_calculate_risk_penalty_high_penalties(self, config_manager):
        """Test high penalty scenarios."""
        # High risk scenario: low MTV, high pledge, high volatility
        high_risk_prices = pd.Series({
            'close': 100.0,
            'volume': 50000,
            'median_traded_value_cr': 1.0,  # Low MTV
            'sigma20': 0.08  # High volatility
        })
        
        high_risk_fundamentals = pd.Series({
            'roe_3y': 0.02,  # Very low ROE
            'quarter_end': datetime.now(timezone.utc).strftime('%Y-%m-%d'),  # Recent quarter
            'opm_stdev_12q': 0.15  # High OPM volatility
        })
        
        high_risk_ownership = pd.Series({
            'promoter_pledge_frac': 0.30  # High pledge
        })
        
        total_rp, breakdown = calculate_risk_penalty(
            ticker="HIGHRISK",
            prices_data=high_risk_prices,
            fundamentals_data=high_risk_fundamentals,
            ownership_data=high_risk_ownership,
            sector_group="metals",
            mode="trader",
            config=config_manager
        )
        
        # Should have multiple penalties
        assert breakdown['liquidity'] > 0
        assert breakdown['pledge'] > 0
        assert breakdown['volatility'] > 0
        
        # Total should be capped at sector limit (metals = 18)
        assert total_rp <= 18
    
    def test_calculate_risk_penalty_mode_differences(self, config_manager, 
                                                   sample_fundamentals_data, sample_ownership_data):
        """Test that trader vs investor mode affects liquidity penalty."""
        # MTV = 2.5 Cr (between trader and investor thresholds)
        prices_data = pd.Series({
            'close': 1000.0,
            'volume': 250000,
            'median_traded_value_cr': 2.5,
            'sigma20': 0.02
        })
        
        # Test trader mode
        trader_rp, trader_breakdown = calculate_risk_penalty(
            ticker="TEST",
            prices_data=prices_data,
            fundamentals_data=sample_fundamentals_data,
            ownership_data=sample_ownership_data,
            sector_group="it",
            mode="trader",
            config=config_manager
        )
        
        # Test investor mode
        investor_rp, investor_breakdown = calculate_risk_penalty(
            ticker="TEST",
            prices_data=prices_data,
            fundamentals_data=sample_fundamentals_data,
            ownership_data=sample_ownership_data,
            sector_group="it",
            mode="investor",
            config=config_manager
        )
        
        # MTV 2.5Cr should penalize trader more than investor
        # Trader: <3Cr → +5, Investor: 2-5Cr → +5 (same in this case)
        assert trader_breakdown['liquidity'] >= investor_breakdown['liquidity']


class TestLiquidityPenalty:
    """Test liquidity penalty calculation."""
    
    def test_liquidity_penalty_trader_mode(self, config_manager):
        """Test trader mode liquidity penalties."""
        # Test different MTV levels for trader
        test_cases = [
            (0.5, 10.0),  # <3Cr → 10 penalty
            (3.0, 5.0),   # 3Cr → 5 penalty  
            (4.0, 5.0),   # 3-5Cr → 5 penalty
            (6.0, 0.0)    # >5Cr → 0 penalty
        ]
        
        for mtv_cr, expected_penalty in test_cases:
            penalty = _calculate_liquidity_penalty(mtv_cr, "trader", config_manager)
            assert penalty == expected_penalty, f"MTV {mtv_cr}Cr should give {expected_penalty} penalty"
    
    def test_liquidity_penalty_investor_mode(self, config_manager):
        """Test investor mode liquidity penalties."""
        # Test different MTV levels for investor
        test_cases = [
            (0.5, 10.0),  # <2Cr → 10 penalty
            (2.0, 5.0),   # 2Cr → 5 penalty
            (3.0, 5.0),   # 2-5Cr → 5 penalty
            (6.0, 0.0)    # >5Cr → 0 penalty
        ]
        
        for mtv_cr, expected_penalty in test_cases:
            penalty = _calculate_liquidity_penalty(mtv_cr, "investor", config_manager)
            assert penalty == expected_penalty, f"MTV {mtv_cr}Cr should give {expected_penalty} penalty"
    
    def test_liquidity_penalty_edge_cases(self, config_manager):
        """Test edge cases for liquidity penalty."""
        # Test negative/NaN MTV
        assert _calculate_liquidity_penalty(np.nan, "trader", config_manager) == 10.0
        assert _calculate_liquidity_penalty(-1.0, "trader", config_manager) == 10.0


class TestPledgePenalty:
    """Test pledge penalty calculation."""
    
    def test_pledge_penalty_bins(self, config_manager):
        """Test pledge penalty bins."""
        test_cases = [
            (0.05, 0.0),   # ≤10% → 0 penalty
            (0.10, 0.0),   # =10% → 0 penalty
            (0.15, 5.0),   # 10-25% → 5 penalty
            (0.25, 5.0),   # =25% → 5 penalty
            (0.30, 10.0),  # >25% → 10 penalty
            (0.50, 10.0)   # >25% → 10 penalty
        ]
        
        for pledge_frac, expected_penalty in test_cases:
            penalty = _calculate_pledge_penalty(pledge_frac, config_manager)
            assert penalty == expected_penalty, f"Pledge {pledge_frac*100}% should give {expected_penalty} penalty"
    
    def test_pledge_penalty_edge_cases(self, config_manager):
        """Test edge cases for pledge penalty."""
        # Test negative/NaN pledge
        assert _calculate_pledge_penalty(np.nan, config_manager) == 0.0
        assert _calculate_pledge_penalty(-0.1, config_manager) == 0.0


class TestVolatilityPenalty:
    """Test volatility penalty calculation."""
    
    def test_volatility_penalty_calculation(self, config_manager):
        """Test volatility penalty calculation."""
        # Test for IT sector (estimated sigma = 0.02)
        # Threshold = 2.5 × 0.02 = 0.05
        
        test_cases = [
            (0.02, "it", 0.0),  # Below threshold → 0 penalty
            (0.05, "it", 0.0),  # At threshold → 0 penalty
            (0.06, "it", 5.0),  # Above threshold → 5 penalty
            (0.10, "it", 5.0),  # Well above threshold → 5 penalty
        ]
        
        for stock_sigma, sector, expected_penalty in test_cases:
            penalty = _calculate_volatility_penalty(stock_sigma, sector, config_manager)
            assert penalty == expected_penalty, f"Sigma {stock_sigma} in {sector} should give {expected_penalty} penalty"
    
    def test_volatility_penalty_different_sectors(self, config_manager):
        """Test volatility penalty across sectors."""
        stock_sigma = 0.08  # Same volatility for different sectors
        
        # Different sectors have different estimated volatilities
        # so same stock volatility gives different penalties
        sectors_to_test = ["it", "banks", "metals", "fmcg"]
        
        for sector in sectors_to_test:
            penalty = _calculate_volatility_penalty(stock_sigma, sector, config_manager)
            assert penalty in [0.0, 5.0], f"Penalty should be 0 or 5 for sector {sector}"
    
    def test_volatility_penalty_edge_cases(self, config_manager):
        """Test edge cases for volatility penalty."""
        # Test invalid volatility
        assert _calculate_volatility_penalty(np.nan, "it", config_manager) == 0.0
        assert _calculate_volatility_penalty(0.0, "it", config_manager) == 0.0
        assert _calculate_volatility_penalty(-0.1, "it", config_manager) == 0.0


class TestEventPenalty:
    """Test event window penalty calculation."""
    
    def test_event_penalty_near_earnings(self, config_manager):
        """Test event penalty near estimated earnings date."""
        # Quarter ended 2024-09-30, estimated earnings ~45 days later (mid-Nov)
        quarter_end_data = pd.Series({'quarter_end': '2024-09-30'})
        
        # Test date ~45 days after quarter end (should trigger penalty)
        test_date = datetime(2024, 11, 14, tzinfo=timezone.utc)
        
        penalty = _calculate_event_penalty(
            "TEST", quarter_end_data, test_date, config_manager
        )
        
        # Should have penalty within ±2 days of estimated earnings
        assert penalty == 2.0
    
    def test_event_penalty_far_from_earnings(self, config_manager):
        """Test event penalty far from estimated earnings date."""
        quarter_end_data = pd.Series({'quarter_end': '2024-09-30'})
        
        # Test date far from estimated earnings (should not trigger penalty)
        test_date = datetime(2024, 10, 15, tzinfo=timezone.utc)
        
        penalty = _calculate_event_penalty(
            "TEST", quarter_end_data, test_date, config_manager
        )
        
        # Should have no penalty
        assert penalty == 0.0
    
    def test_event_penalty_missing_data(self, config_manager):
        """Test event penalty with missing quarter end data."""
        empty_data = pd.Series({'some_other_field': 'value'})
        test_date = datetime.now(timezone.utc)
        
        penalty = _calculate_event_penalty(
            "TEST", empty_data, test_date, config_manager
        )
        
        # Should have no penalty with missing data
        assert penalty == 0.0


class TestGovernancePenalty:
    """Test governance penalty calculation."""
    
    def test_governance_penalty_low_roe(self, config_manager):
        """Test governance penalty for low ROE (financial stress)."""
        # Very low ROE should trigger penalty
        low_roe_data = pd.Series({
            'roe_3y': 0.02,  # 2% ROE (below 5% threshold)
            'opm_stdev_12q': 0.05  # Normal OPM volatility
        })
        
        penalty = _calculate_governance_penalty(low_roe_data, config_manager)
        
        # Should have auditor qualification penalty
        assert penalty >= 2.0  # Based on config auditor_qualification: 2
    
    def test_governance_penalty_high_opm_volatility(self, config_manager):
        """Test governance penalty for high OPM volatility (management instability)."""
        # High OPM volatility should trigger penalty
        high_vol_data = pd.Series({
            'roe_3y': 0.15,  # Good ROE
            'opm_stdev_12q': 0.12  # High OPM volatility (above 10% threshold)
        })
        
        penalty = _calculate_governance_penalty(high_vol_data, config_manager)
        
        # Should have board resignation penalty
        assert penalty >= 1.0  # Based on config board_resignation: 1
    
    def test_governance_penalty_multiple_issues(self, config_manager):
        """Test governance penalty with multiple issues."""
        # Both low ROE and high OPM volatility
        problem_data = pd.Series({
            'roe_3y': 0.02,  # Low ROE
            'opm_stdev_12q': 0.12  # High OPM volatility
        })
        
        penalty = _calculate_governance_penalty(problem_data, config_manager)
        
        # Should have both penalties, but capped
        expected_penalty = 2.0 + 1.0  # auditor + board resignation
        assert penalty >= expected_penalty
    
    def test_governance_penalty_good_fundamentals(self, config_manager):
        """Test governance penalty with good fundamentals."""
        # Good ROE and normal OPM volatility
        good_data = pd.Series({
            'roe_3y': 0.15,  # Good ROE
            'opm_stdev_12q': 0.05  # Normal OPM volatility
        })
        
        penalty = _calculate_governance_penalty(good_data, config_manager)
        
        # Should have no penalties
        assert penalty == 0.0


class TestRiskPenaltySummary:
    """Test risk penalty summary generation."""
    
    def test_get_risk_penalty_summary_with_penalties(self):
        """Test summary generation with multiple penalties."""
        breakdown = {
            'liquidity': 5.0,
            'pledge': 10.0,
            'volatility': 0.0,
            'event': 2.0,
            'governance': 0.0,
            'total_after_cap': 17.0
        }
        
        summary = get_risk_penalty_summary(breakdown)
        
        # Should include non-zero components
        assert "Liquidity(5)" in summary
        assert "Pledge(10)" in summary
        assert "Event(2)" in summary
        assert "= 17" in summary
        
        # Should not include zero components
        assert "Volatility" not in summary
        assert "Governance" not in summary
    
    def test_get_risk_penalty_summary_no_penalties(self):
        """Test summary generation with no penalties."""
        breakdown = {
            'liquidity': 0.0,
            'pledge': 0.0,
            'volatility': 0.0,
            'event': 0.0,
            'governance': 0.0,
            'total_after_cap': 0.0
        }
        
        summary = get_risk_penalty_summary(breakdown)
        assert summary == "No penalties applied"


if __name__ == "__main__":
    pytest.main([__file__])