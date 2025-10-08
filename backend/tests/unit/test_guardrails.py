"""Unit tests for Guardrails Engine (core/guardrails.py)."""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from greyoak_score.core.config_manager import ConfigManager
from greyoak_score.core.guardrails import (
    apply_guardrails,
    _get_mtv_cr,
    _is_illiquid,
    _score_to_band,
    _max_conservative,
    get_guardrail_summary,
    validate_guardrail_order,
    explain_guardrail,
    get_band_implications,
    BAND_HIERARCHY
)


@pytest.fixture
def config_manager():
    """Get test config manager."""
    config_dir = Path(__file__).parent.parent.parent / "configs"
    return ConfigManager(config_dir)


@pytest.fixture
def sample_prices_data():
    """Sample price data for testing."""
    return pd.Series({
        'close': 2500.0,
        'volume': 1000000,
        'median_traded_value_cr': 4.5  # Good liquidity
    })


@pytest.fixture
def sample_fundamentals_data():
    """Sample fundamentals data."""
    return pd.Series({
        'roe_3y': 0.15,
        'quarter_end': '2024-09-30'
    })


@pytest.fixture
def sample_ownership_data():
    """Sample ownership data."""
    return pd.Series({
        'promoter_pledge_frac': 0.05  # Low pledge
    })


class TestGuardrailsEngine:
    """Test the main guardrails application function."""
    
    def test_apply_guardrails_no_triggers(self, config_manager, sample_prices_data,
                                        sample_fundamentals_data, sample_ownership_data):
        """Test guardrails with no triggers (ideal scenario)."""
        score, band, flags = apply_guardrails(
            score_pre_guard=80.0,
            ticker="GOODSTOCK",
            prices_data=sample_prices_data,
            fundamentals_data=sample_fundamentals_data,
            ownership_data=sample_ownership_data,
            sector_group="it",
            mode="trader",
            config=config_manager,
            confidence=0.85,  # Good confidence
            imputed_fraction=0.10,  # Low imputation
            s_z=1.2,  # Positive sector momentum
            risk_penalty=5.0  # Low risk penalty
        )
        
        # No guardrails should trigger
        assert score == 80.0  # Score unchanged
        assert band == "Strong Buy"  # High score band
        assert len(flags) == 0  # No flags triggered
    
    def test_apply_guardrails_low_data_hold(self, config_manager, sample_prices_data,
                                          sample_fundamentals_data, sample_ownership_data):
        """Test LowDataHold guardrail (confidence < 0.70)."""
        score, band, flags = apply_guardrails(
            score_pre_guard=85.0,  # High score
            ticker="LOWCONF",
            prices_data=sample_prices_data,
            fundamentals_data=sample_fundamentals_data,
            ownership_data=sample_ownership_data,
            sector_group="it",
            mode="trader",
            config=config_manager,
            confidence=0.60,  # Low confidence (< 0.70)
            imputed_fraction=0.10,
            s_z=1.0,
            risk_penalty=5.0
        )
        
        assert score == 85.0  # Score unchanged
        assert band == "Hold"  # Capped at Hold
        assert "LowDataHold" in flags
    
    def test_apply_guardrails_illiquidity(self, config_manager, sample_fundamentals_data,
                                        sample_ownership_data):
        """Test Illiquidity guardrail (low MTV)."""
        # Low liquidity prices data
        illiquid_prices = pd.Series({
            'close': 100.0,
            'volume': 10000,
            'median_traded_value_cr': 1.5  # Low MTV for trader (< 3Cr)
        })
        
        score, band, flags = apply_guardrails(
            score_pre_guard=80.0,
            ticker="ILLIQUID",
            prices_data=illiquid_prices,
            fundamentals_data=sample_fundamentals_data,
            ownership_data=sample_ownership_data,
            sector_group="it",
            mode="trader",
            config=config_manager,
            confidence=0.80,
            imputed_fraction=0.10,
            s_z=1.0,
            risk_penalty=5.0
        )
        
        assert score == 80.0  # Score unchanged
        assert band == "Hold"  # Capped at Hold
        assert "Illiquidity" in flags
    
    def test_apply_guardrails_pledge_cap(self, config_manager, sample_prices_data,
                                       sample_fundamentals_data):
        """Test PledgeCap guardrail (pledge > 10%)."""
        # High pledge ownership data
        high_pledge_ownership = pd.Series({
            'promoter_pledge_frac': 0.15  # 15% pledge (> 10%)
        })
        
        score, band, flags = apply_guardrails(
            score_pre_guard=75.0,
            ticker="HIGHPLEDGE",
            prices_data=sample_prices_data,
            fundamentals_data=sample_fundamentals_data,
            ownership_data=high_pledge_ownership,
            sector_group="it",
            mode="trader",
            config=config_manager,
            confidence=0.80,
            imputed_fraction=0.10,
            s_z=1.0,
            risk_penalty=5.0
        )
        
        assert score == 75.0  # Score unchanged
        assert band == "Hold"  # Capped at Hold (was Strong Buy)
        assert "PledgeCap" in flags
    
    def test_apply_guardrails_high_risk_cap(self, config_manager, sample_prices_data,
                                          sample_fundamentals_data, sample_ownership_data):
        """Test HighRiskCap guardrail (RP ≥ 15)."""
        score, band, flags = apply_guardrails(
            score_pre_guard=70.0,
            ticker="HIGHRISK",
            prices_data=sample_prices_data,
            fundamentals_data=sample_fundamentals_data,
            ownership_data=sample_ownership_data,
            sector_group="it",
            mode="trader",
            config=config_manager,
            confidence=0.80,
            imputed_fraction=0.10,
            s_z=1.0,
            risk_penalty=18.0  # High RP (≥ 15)
        )
        
        assert score == 70.0  # Score unchanged
        assert band == "Hold"  # Capped at Hold (was Buy)
        assert "HighRiskCap" in flags
    
    def test_apply_guardrails_sector_bear_trader(self, config_manager, sample_prices_data,
                                               sample_fundamentals_data, sample_ownership_data):
        """Test SectorBear guardrail in Trader mode (band capping)."""
        score, band, flags = apply_guardrails(
            score_pre_guard=80.0,
            ticker="BEARSECTOR",
            prices_data=sample_prices_data,
            fundamentals_data=sample_fundamentals_data,
            ownership_data=sample_ownership_data,
            sector_group="metals",
            mode="trader",
            config=config_manager,
            confidence=0.80,
            imputed_fraction=0.10,
            s_z=-2.0,  # Negative S_z (≤ -1.5)
            risk_penalty=5.0
        )
        
        assert score == 80.0  # Score unchanged in trader mode
        assert band == "Hold"  # Capped at Hold
        assert "SectorBear" in flags
    
    def test_apply_guardrails_sector_bear_investor(self, config_manager, sample_prices_data,
                                                 sample_fundamentals_data, sample_ownership_data):
        """Test SectorBear guardrail in Investor mode (score adjustment)."""
        score, band, flags = apply_guardrails(
            score_pre_guard=75.0,
            ticker="BEARSECTOR", 
            prices_data=sample_prices_data,
            fundamentals_data=sample_fundamentals_data,
            ownership_data=sample_ownership_data,
            sector_group="metals",
            mode="investor",
            config=config_manager,
            confidence=0.80,
            imputed_fraction=0.10,
            s_z=-1.8,  # Negative S_z (≤ -1.5)
            risk_penalty=5.0
        )
        
        assert score == 70.0  # Score reduced by 5 points
        assert band == "Buy"  # Re-banded after score adjustment (70 = Buy)
        assert "SectorBear" in flags
    
    def test_apply_guardrails_low_coverage(self, config_manager, sample_prices_data,
                                         sample_fundamentals_data, sample_ownership_data):
        """Test LowCoverage guardrail (imputed_fraction ≥ 0.25)."""
        score, band, flags = apply_guardrails(
            score_pre_guard=72.0,
            ticker="LOWCOVERAGE",
            prices_data=sample_prices_data,
            fundamentals_data=sample_fundamentals_data,
            ownership_data=sample_ownership_data,
            sector_group="it",
            mode="trader",
            config=config_manager,
            confidence=0.80,
            imputed_fraction=0.30,  # High imputation (≥ 0.25)
            s_z=1.0,
            risk_penalty=5.0
        )
        
        assert score == 72.0  # Score unchanged
        assert band == "Hold"  # Capped at Hold (was Buy)
        assert "LowCoverage" in flags
    
    def test_apply_guardrails_multiple_triggers(self, config_manager):
        """Test multiple guardrails triggering simultaneously."""
        # Create data that triggers multiple guardrails
        bad_prices = pd.Series({
            'close': 50.0,
            'volume': 5000,
            'median_traded_value_cr': 0.8  # Very low MTV
        })
        
        bad_ownership = pd.Series({
            'promoter_pledge_frac': 0.20  # High pledge
        })
        
        score, band, flags = apply_guardrails(
            score_pre_guard=85.0,  # High score initially
            ticker="MULTIISSUE",
            prices_data=bad_prices,
            fundamentals_data=pd.Series({}),
            ownership_data=bad_ownership,
            sector_group="metals",
            mode="trader",
            config=config_manager,
            confidence=0.55,  # Low confidence
            imputed_fraction=0.35,  # High imputation
            s_z=-2.2,  # Sector bear
            risk_penalty=16.0  # High RP
        )
        
        # All guardrails should trigger
        expected_flags = {"LowDataHold", "Illiquidity", "PledgeCap", "HighRiskCap", "SectorBear", "LowCoverage"}
        assert set(flags) == expected_flags
        
        # Band should be most conservative (Hold)
        assert band == "Hold"
    
    def test_guardrails_order_matters(self, config_manager, sample_prices_data,
                                    sample_fundamentals_data, sample_ownership_data):
        """Test that guardrail order is deterministic and sequential."""
        # Apply guardrails twice - should get identical results
        args = {
            'score_pre_guard': 78.0,
            'ticker': "ORDERTEST",
            'prices_data': sample_prices_data,
            'fundamentals_data': sample_fundamentals_data,
            'ownership_data': sample_ownership_data,
            'sector_group': "it",
            'mode': "trader",
            'config': config_manager,
            'confidence': 0.65,  # Triggers LowDataHold
            'imputed_fraction': 0.15,
            's_z': 1.0,
            'risk_penalty': 10.0
        }
        
        score1, band1, flags1 = apply_guardrails(**args)
        score2, band2, flags2 = apply_guardrails(**args)
        
        # Results should be identical
        assert score1 == score2
        assert band1 == band2
        assert flags1 == flags2


class TestHelperFunctions:
    """Test helper functions used by guardrails."""
    
    def test_get_mtv_cr_from_data(self):
        """Test MTV extraction from price data."""
        prices_with_mtv = pd.Series({'median_traded_value_cr': 5.5})
        assert _get_mtv_cr(prices_with_mtv) == 5.5
    
    def test_get_mtv_cr_estimation(self):
        """Test MTV estimation from volume and price."""
        prices_without_mtv = pd.Series({
            'volume': 1000000,
            'close': 250.0
        })
        # Expected: (1M * 250) / 10^7 = 25 Cr
        assert _get_mtv_cr(prices_without_mtv) == 25.0
    
    def test_get_mtv_cr_missing_data(self):
        """Test MTV with missing data."""
        empty_prices = pd.Series({})
        assert _get_mtv_cr(empty_prices) == 0.0
    
    def test_is_illiquid(self, config_manager):
        """Test illiquidity detection."""
        # Test trader mode thresholds
        assert _is_illiquid(2.0, "trader", config_manager) == True  # < 3Cr → illiquid
        assert _is_illiquid(4.0, "trader", config_manager) == False  # ≥ 3Cr → liquid
        
        # Test investor mode thresholds
        assert _is_illiquid(1.5, "investor", config_manager) == True  # < 2Cr → illiquid
        assert _is_illiquid(3.0, "investor", config_manager) == False  # ≥ 2Cr → liquid
        
        # Test edge cases
        assert _is_illiquid(np.nan, "trader", config_manager) == True
        assert _is_illiquid(-1.0, "trader", config_manager) == True
    
    def test_score_to_band(self, config_manager):
        """Test score to band conversion."""
        # Test production thresholds (Strong Buy: 75, Buy: 65, Hold: 50)
        assert _score_to_band(80.0, config_manager) == "Strong Buy"
        assert _score_to_band(75.0, config_manager) == "Strong Buy"  # Boundary
        assert _score_to_band(70.0, config_manager) == "Buy"
        assert _score_to_band(65.0, config_manager) == "Buy"  # Boundary
        assert _score_to_band(55.0, config_manager) == "Hold"
        assert _score_to_band(50.0, config_manager) == "Hold"  # Boundary
        assert _score_to_band(40.0, config_manager) == "Avoid"
    
    def test_max_conservative(self):
        """Test conservative band selection."""
        # Test all combinations
        assert _max_conservative("Strong Buy", "Buy") == "Buy"
        assert _max_conservative("Buy", "Hold") == "Hold"
        assert _max_conservative("Hold", "Avoid") == "Avoid"
        
        # Test same bands
        assert _max_conservative("Buy", "Buy") == "Buy"
        
        # Test reverse order
        assert _max_conservative("Hold", "Strong Buy") == "Hold"
        
        # Test with Avoid (most conservative)
        assert _max_conservative("Strong Buy", "Avoid") == "Avoid"
    
    def test_band_hierarchy_consistency(self):
        """Test that band hierarchy is correctly ordered."""
        assert BAND_HIERARCHY["Avoid"] < BAND_HIERARCHY["Hold"]
        assert BAND_HIERARCHY["Hold"] < BAND_HIERARCHY["Buy"]
        assert BAND_HIERARCHY["Buy"] < BAND_HIERARCHY["Strong Buy"]


class TestGuardrailUtilities:
    """Test utility functions for guardrails."""
    
    def test_get_guardrail_summary(self):
        """Test guardrail summary generation."""
        # No flags
        assert get_guardrail_summary([]) == "No guardrails triggered"
        
        # Single flag
        summary = get_guardrail_summary(["LowDataHold"])
        assert "Low Data Quality" in summary
        
        # Two flags
        summary = get_guardrail_summary(["Illiquidity", "PledgeCap"])
        assert "Low Liquidity" in summary
        assert "High Promoter Pledge" in summary
        assert " and " in summary
        
        # Multiple flags
        summary = get_guardrail_summary(["LowDataHold", "Illiquidity", "PledgeCap"])
        assert "Low Data Quality" in summary
        assert "Low Liquidity" in summary
        assert "High Promoter Pledge" in summary
        assert ", and " in summary
    
    def test_validate_guardrail_order(self):
        """Test guardrail order validation."""
        # Should return True as order is correctly implemented
        assert validate_guardrail_order() == True
    
    def test_explain_guardrail(self):
        """Test guardrail explanations."""
        # Test with appropriate kwargs
        explanation = explain_guardrail("LowDataHold", confidence=0.65)
        assert "65.0%" in explanation
        assert "70%" in explanation
        
        explanation = explain_guardrail("Illiquidity", mtv_cr=1.5, mode="trader")
        assert "1.5₹Cr" in explanation
        assert "trader" in explanation
        
        explanation = explain_guardrail("PledgeCap", pledge_frac=0.15)
        assert "15.0%" in explanation
        assert "10%" in explanation
        
        # Test unknown guardrail
        explanation = explain_guardrail("UnknownGuardrail")
        assert "Unknown guardrail" in explanation
        
        # Test with missing kwargs (should not crash)
        explanation = explain_guardrail("LowDataHold")  # Missing confidence
        assert "insufficient data" in explanation
    
    def test_get_band_implications(self):
        """Test band implications."""
        # Test each band
        for band in ["Strong Buy", "Buy", "Hold", "Avoid"]:
            implications = get_band_implications(band)
            assert "action" in implications
            assert "timeframe" in implications
            assert "risk_level" in implications
            assert "allocation" in implications
        
        # Test unknown band
        implications = get_band_implications("Unknown")
        assert "Unknown band" in implications["action"]


if __name__ == "__main__":
    pytest.main([__file__])