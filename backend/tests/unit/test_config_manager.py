"""Unit tests for ConfigManager."""

import pytest

from greyoak_score.core.config_manager import ConfigManager


class TestConfigManagerLoading:
    """Test configuration loading and validation."""

    def test_load_all_configs(self, config_manager: ConfigManager):
        """Test that all config files are loaded successfully."""
        assert config_manager.score_config is not None
        assert config_manager.sector_map_config is not None
        assert config_manager.freshness_config is not None
        assert config_manager.data_sources_config is not None

    def test_config_hash_generated(self, config_manager: ConfigManager):
        """Test that config hash is generated for audit trail."""
        assert config_manager.config_hash is not None
        assert len(config_manager.config_hash) == 64  # SHA-256 hex digest

    def test_mode_is_production(self, config_manager: ConfigManager):
        """Test that mode is set to production by default."""
        assert config_manager.mode == "production"


class TestPillarWeights:
    """Test pillar weight retrieval."""

    def test_get_default_trader_weights(self, config_manager: ConfigManager):
        """Test retrieving default trader weights."""
        weights = config_manager.get_pillar_weights("default", "Trader")
        
        assert weights["F"] == 0.12
        assert weights["T"] == 0.32
        assert weights["R"] == 0.16
        assert weights["O"] == 0.08
        assert weights["Q"] == 0.04
        assert weights["S"] == 0.28
        
        # Weights must sum to 1.0
        assert abs(sum(weights.values()) - 1.0) < 1e-6

    def test_get_metals_trader_weights(self, config_manager: ConfigManager):
        """Test sector-specific weights (metals trader)."""
        weights = config_manager.get_pillar_weights("metals", "Trader")
        
        # Metals has higher T and S weights
        assert weights["T"] > 0.30
        assert weights["S"] > 0.25
        assert abs(sum(weights.values()) - 1.0) < 1e-6

    def test_get_banks_investor_weights(self, config_manager: ConfigManager):
        """Test banking sector investor weights."""
        weights = config_manager.get_pillar_weights("banks", "Investor")
        
        # Banks has higher F weight in investor mode
        assert weights["F"] > 0.40
        assert abs(sum(weights.values()) - 1.0) < 1e-6

    def test_fallback_to_default_weights(self, config_manager: ConfigManager):
        """Test fallback to default weights for unknown sector."""
        weights = config_manager.get_pillar_weights("unknown_sector", "Trader")
        default_weights = config_manager.get_pillar_weights("default", "Trader")
        
        assert weights == default_weights


class TestBandThresholds:
    """Test band threshold retrieval."""

    def test_get_production_band_thresholds(self, config_manager: ConfigManager):
        """Test production band thresholds."""
        thresholds = config_manager.get_band_thresholds()
        
        assert thresholds["strong_buy"] == 75
        assert thresholds["buy"] == 65
        assert thresholds["hold"] == 50
        
        # Must be monotonic
        assert thresholds["strong_buy"] > thresholds["buy"] > thresholds["hold"]


class TestRiskPenaltyConfig:
    """Test risk penalty configuration retrieval."""

    def test_get_default_rp_cap(self, config_manager: ConfigManager):
        """Test default RP cap."""
        cap = config_manager.get_rp_cap("default")
        assert cap == 20

    def test_get_metals_rp_cap(self, config_manager: ConfigManager):
        """Test metals sector RP cap (lower for high volatility)."""
        cap = config_manager.get_rp_cap("metals")
        assert cap == 18

    def test_get_fmcg_rp_cap(self, config_manager: ConfigManager):
        """Test FMCG sector RP cap (lower for defensive)."""
        cap = config_manager.get_rp_cap("fmcg")
        assert cap == 12

    def test_get_trader_liquidity_penalties(self, config_manager: ConfigManager):
        """Test trader liquidity penalty bins."""
        penalties = config_manager.get_liquidity_penalties("Trader")
        
        assert len(penalties) == 3
        # Sorted descending by threshold
        assert penalties[0]["threshold"] == 5.0
        assert penalties[0]["penalty"] == 0
        assert penalties[2]["threshold"] == 0.0
        assert penalties[2]["penalty"] == 10

    def test_get_pledge_bins(self, config_manager: ConfigManager):
        """Test pledge penalty bins."""
        bins = config_manager.get_pledge_bins()
        
        assert len(bins) == 2
        assert bins[0]["threshold"] == 0.25
        assert bins[0]["penalty"] == 10


class TestGuardrailThresholds:
    """Test guardrail threshold retrieval."""

    def test_get_production_guardrail_thresholds(self, config_manager: ConfigManager):
        """Test production guardrail thresholds."""
        thresholds = config_manager.get_guardrail_thresholds()
        
        assert thresholds["confidence"] == 0.70
        assert thresholds["sector_bear_sz"] == -1.5
        assert thresholds["high_risk_rp"] == 15
        assert thresholds["pledge_cap"] == 0.10
        assert thresholds["low_coverage"] == 0.25


class TestSubPillarConfigs:
    """Test sub-pillar configuration retrieval."""

    def test_get_non_financial_fundamentals_weights(self, config_manager: ConfigManager):
        """Test non-financial fundamentals weights."""
        weights = config_manager.get_fundamentals_weights(is_banking=False)
        
        assert "roe_3y" in weights
        assert "sales_cagr_3y" in weights
        assert abs(sum(weights.values()) - 1.0) < 1e-6

    def test_get_banking_fundamentals_weights(self, config_manager: ConfigManager):
        """Test banking fundamentals weights (exclusive)."""
        weights = config_manager.get_fundamentals_weights(is_banking=True)
        
        assert "roa_3y" in weights
        assert "gnpa_pct" in weights
        assert "pcr_pct" in weights
        assert abs(sum(weights.values()) - 1.0) < 1e-6

    def test_get_technicals_config(self, config_manager: ConfigManager):
        """Test technicals pillar config."""
        config = config_manager.get_technicals_config()
        
        assert "weights" in config
        assert "rsi_bands" in config
        assert config["rsi_bands"]["oversold"] == 30
        assert config["rsi_bands"]["overbought"] == 70


class TestSectorMapping:
    """Test sector mapping functionality."""

    def test_is_banking_sector(self, config_manager: ConfigManager):
        """Test banking sector identification."""
        assert config_manager.is_banking_sector("banks") is True
        assert config_manager.is_banking_sector("psu_banks") is True
        assert config_manager.is_banking_sector("metals") is False
        assert config_manager.is_banking_sector("fmcg") is False


class TestConfigValidation:
    """Test configuration validation logic."""

    def test_all_weights_sum_to_one(self, config_manager: ConfigManager):
        """Test that all pillar weights sum to 1.0."""
        score_config = config_manager.score_config
        
        for mode in ["trader", "investor"]:
            for sector, weights in score_config["pillar_weights"][mode].items():
                total = sum(weights.values())
                assert abs(total - 1.0) < 1e-6, (
                    f"Weights for {mode}/{sector} sum to {total}, not 1.0"
                )

    def test_band_thresholds_monotonic(self, config_manager: ConfigManager):
        """Test that band thresholds are monotonic."""
        for mode in ["production", "test"]:
            bands = config_manager.score_config["banding"][mode]
            assert bands["strong_buy"] > bands["buy"] > bands["hold"] > 0

    def test_rp_caps_in_valid_range(self, config_manager: ConfigManager):
        """Test that RP caps are in valid range (0, 20]."""
        caps = config_manager.score_config["risk_penalty"]["caps"]
        
        for sector, cap in caps.items():
            assert 0 < cap <= 20, f"RP cap for {sector} is {cap}, must be in (0, 20]"
