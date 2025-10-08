"""Configuration manager for GreyOak Score Engine.

Loads and validates all YAML configuration files.
Provides type-safe access to parameters.
Caches configurations with hash tracking for audit trail.

Section 12: Config Keys and Externalization - all configurable parameters.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from greyoak_score.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """Manages loading and validation of YAML configuration files.
    
    All parameters are loaded from YAML - NO hard-coded values.
    Configuration hash is logged for audit trail and determinism.
    
    Usage:
        >>> config = ConfigManager(Path("configs"))
        >>> weights = config.get_pillar_weights("metals", "Trader")
        >>> thresholds = config.get_band_thresholds("production")
    """

    def __init__(self, config_dir: Path):
        """Initialize configuration manager.
        
        Args:
            config_dir: Directory containing YAML config files.
            
        Raises:
            FileNotFoundError: If config directory or required files don't exist.
            ValueError: If configuration validation fails.
        """
        self.config_dir = config_dir
        
        # Load all config files
        self.score_config = self._load_yaml(config_dir / "score.yaml")
        self.sector_map_config = self._load_yaml(config_dir / "sector_map.yaml")
        self.freshness_config = self._load_yaml(config_dir / "freshness.yaml")
        self.data_sources_config = self._load_yaml(config_dir / "data_sources.yaml")
        
        # Validate configurations
        self._validate_score_config()
        self._validate_sector_map_config()
        
        # Compute config hash for audit trail
        self._config_hash = self._compute_hash()
        
        logger.info(
            f"Configuration loaded successfully from {config_dir}",
            extra={"data": {"config_hash": self._config_hash}},
        )
    
    @property
    def config_hash(self) -> str:
        """Get SHA-256 hash of all configurations (for audit trail)."""
        return self._config_hash
    
    @property
    def mode(self) -> str:
        """Get current mode (production or test)."""
        return self.score_config.get("mode", "production")
    
    def _load_yaml(self, filepath: Path) -> Dict[str, Any]:
        """Load YAML file.
        
        Args:
            filepath: Path to YAML file.
            
        Returns:
            Parsed YAML content as dictionary.
            
        Raises:
            FileNotFoundError: If file doesn't exist.
        """
        if not filepath.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")
        
        with open(filepath, "r") as f:
            return yaml.safe_load(f)
    
    def _compute_hash(self) -> str:
        """Compute SHA-256 hash of all configurations.
        
        Returns:
            Hex digest of configuration hash.
        """
        # Combine all configs into a single dict
        combined = {
            "score": self.score_config,
            "sector_map": self.sector_map_config,
            "freshness": self.freshness_config,
            "data_sources": self.data_sources_config,
        }
        
        # Serialize to JSON (sorted keys for determinism)
        config_str = json.dumps(combined, sort_keys=True)
        
        # Compute SHA-256 hash
        return hashlib.sha256(config_str.encode()).hexdigest()
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Validation Methods
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def _validate_score_config(self) -> None:
        """Validate score.yaml configuration.
        
        Checks:
        - All pillar weights sum to 1.0 for each sector/mode
        - Band thresholds are monotonic
        - RP caps are in valid range (0, 20]
        - Pledge penalty curve is monotonic
        
        Raises:
            ValueError: If validation fails.
        """
        # Check pillar weights sum to 1.0
        for mode in ["trader", "investor"]:
            mode_weights = self.score_config["pillar_weights"].get(mode, {})
            for sector, weights in mode_weights.items():
                total = sum(weights.values())
                if abs(total - 1.0) > 1e-6:
                    raise ValueError(
                        f"Pillar weights for {mode}/{sector} sum to {total:.6f}, not 1.0. "
                        f"Weights: {weights}"
                    )
        
        # Check band thresholds are monotonic
        mode_key = self.mode
        bands = self.score_config["banding"][mode_key]
        if not (bands["strong_buy"] > bands["buy"] > bands["hold"] > 0):
            raise ValueError(
                f"Band thresholds not monotonic in {mode_key} mode: {bands}"
            )
        
        # Check RP caps are in valid range
        for sector, cap in self.score_config["risk_penalty"]["caps"].items():
            if not (0 < cap <= 20):
                raise ValueError(
                    f"RP cap for {sector} is {cap}, must be in range (0, 20]"
                )
        
        # Check pledge penalty curve is monotonic
        curve = self.score_config["ownership"]["pledge_penalty_curve"]
        for i in range(len(curve) - 1):
            if curve[i]["fraction"] >= curve[i + 1]["fraction"]:
                raise ValueError(
                    f"Pledge penalty curve not monotonic at index {i}: "
                    f"{curve[i]['fraction']} >= {curve[i + 1]['fraction']}"
                )
            if curve[i]["penalty"] > curve[i + 1]["penalty"]:
                raise ValueError(
                    f"Pledge penalty curve not monotonic (penalties) at index {i}: "
                    f"{curve[i]['penalty']} > {curve[i + 1]['penalty']}"
                )
        
        logger.info("score.yaml validation passed")
    
    def _validate_sector_map_config(self) -> None:
        """Validate sector_map.yaml configuration.
        
        Raises:
            ValueError: If validation fails.
        """
        # Check all sector groups have required fields
        required_fields = ["name", "horizon_bias", "rp_cap"]
        for group, data in self.sector_map_config.get("sector_groups", {}).items():
            for field in required_fields:
                if field not in data:
                    raise ValueError(
                        f"Sector group '{group}' missing required field: {field}"
                    )
        
        logger.info("sector_map.yaml validation passed")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Pillar Weights
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_pillar_weights(self, sector_group: str, mode: str) -> Dict[str, float]:
        """Get pillar weights for a sector and mode.
        
        Args:
            sector_group: Sector group (e.g., "metals", "banks", "fmcg").
            mode: Scoring mode ("Trader" or "Investor").
            
        Returns:
            Dictionary with keys F, T, R, O, Q, S (sum to 1.0).
            Falls back to "default" if sector not found.
        """
        mode_key = mode.lower()
        weights = self.score_config["pillar_weights"][mode_key]
        
        # Try sector-specific, fallback to default
        sector_weights = weights.get(sector_group, weights.get("default"))
        
        if sector_weights is None:
            raise ValueError(
                f"No pillar weights found for sector '{sector_group}' and no default"
            )
        
        return sector_weights
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Band Thresholds
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_band_thresholds(self) -> Dict[str, float]:
        """Get band thresholds for current mode.
        
        Returns:
            Dictionary with keys: strong_buy, buy, hold.
        """
        mode_key = self.mode
        return self.score_config["banding"][mode_key]
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Risk Penalty Parameters
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_rp_cap(self, sector_group: str) -> float:
        """Get risk penalty cap for a sector.
        
        Args:
            sector_group: Sector group.
            
        Returns:
            RP cap (default 20, may be lower for defensive sectors).
        """
        caps = self.score_config["risk_penalty"]["caps"]
        return caps.get(sector_group, caps.get("default", 20))
    
    def get_liquidity_penalties(self, mode: str) -> List[Dict[str, float]]:
        """Get liquidity penalty bins for a mode.
        
        Args:
            mode: Scoring mode ("Trader" or "Investor").
            
        Returns:
            List of dicts with keys: threshold (₹Cr), penalty.
            Sorted descending by threshold.
        """
        mode_key = mode.lower()
        return self.score_config["risk_penalty"]["liquidity"][mode_key]
    
    def get_pledge_bins(self) -> List[Dict[str, float]]:
        """Get pledge penalty bins.
        
        Returns:
            List of dicts with keys: threshold (fraction), penalty.
        """
        return self.score_config["risk_penalty"]["pledge_bins"]
    
    def get_volatility_params(self) -> Dict[str, float]:
        """Get volatility penalty parameters.
        
        Returns:
            Dict with keys: multiplier (e.g., 2.5), penalty (e.g., 5).
        """
        return self.score_config["risk_penalty"]["volatility"]
    
    def get_event_window_params(self) -> Dict[str, float]:
        """Get event window penalty parameters.
        
        Returns:
            Dict with keys: days (±2), penalty.
        """
        return self.score_config["risk_penalty"]["event_window"]
    
    def get_governance_penalties(self) -> Dict[str, float]:
        """Get governance penalty parameters.
        
        Returns:
            Dict with keys: auditor_qualification, board_resignation.
        """
        return self.score_config["risk_penalty"]["governance"]
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Guardrail Thresholds
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_guardrail_thresholds(self) -> Dict[str, float]:
        """Get guardrail thresholds for current mode.
        
        Returns:
            Dict with keys: confidence, sector_bear_sz, high_risk_rp, 
            pledge_cap, low_coverage.
        """
        mode_key = self.mode
        return self.score_config["guardrails"]["thresholds"][mode_key]
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Sub-Pillar Configurations
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_fundamentals_weights(self, is_banking: bool) -> Dict[str, float]:
        """Get fundamentals sub-pillar weights.
        
        Args:
            is_banking: True if stock is in banking sector.
            
        Returns:
            Dict of metric weights (sum to 1.0).
        """
        key = "banking" if is_banking else "non_financial"
        return self.score_config["fundamentals"][key]
    
    def get_technicals_config(self) -> Dict[str, Any]:
        """Get technicals pillar configuration.
        
        Returns:
            Dict with keys: weights, rsi_bands, breakout, etc.
        """
        return self.score_config["technicals"]
    
    def get_relative_strength_config(self) -> Dict[str, Any]:
        """Get relative strength pillar configuration.
        
        Returns:
            Dict with keys: horizon_weights, alpha_weights.
        """
        return self.score_config["relative_strength"]
    
    def get_ownership_config(self) -> Dict[str, Any]:
        """Get ownership pillar configuration.
        
        Returns:
            Dict with keys: weights, pledge_penalty_curve.
        """
        return self.score_config["ownership"]
    
    def get_quality_config(self) -> Dict[str, float]:
        """Get quality pillar configuration.
        
        Returns:
            Dict with keys: roce_3y, opm_stability (weights sum to 1.0).
        """
        return self.score_config["quality"]["weights"]
    
    def get_sector_momentum_config(self) -> Dict[str, float]:
        """Get sector momentum pillar configuration.
        
        Returns:
            Dict with keys: 1M, 3M, 6M (horizon weights sum to 1.0).
        """
        return self.score_config["sector_momentum"]["horizon_weights"]
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Sector Mapping
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_sector_group_info(self, sector_group: str) -> Optional[Dict[str, Any]]:
        """Get sector group information.
        
        Args:
            sector_group: Sector group name.
            
        Returns:
            Dict with keys: name, horizon_bias, rp_cap, etc.
            None if sector group not found.
        """
        return self.sector_map_config["sector_groups"].get(sector_group)
    
    def is_banking_sector(self, sector_group: str) -> bool:
        """Check if sector group is banking/NBFC.
        
        Args:
            sector_group: Sector group name.
            
        Returns:
            True if banking sector (uses exclusive banking F pillar).
        """
        # Banking sectors use ONLY banking metrics
        banking_sectors = {"banks", "psu_banks", "nbfcs"}
        return sector_group.lower() in banking_sectors
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Freshness Configuration
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_freshness_slos(self) -> Dict[str, int]:
        """Get data freshness SLOs (in days).
        
        Returns:
            Dict with keys: prices, fundamentals, ownership, events.
        """
        return self.freshness_config["freshness_slo"]
    
    def get_confidence_weights(self) -> Dict[str, float]:
        """Get confidence calculation weights.
        
        Returns:
            Dict with keys: coverage, freshness, source_quality (sum to 1.0).
        """
        return self.freshness_config["confidence_weights"]
    
    def get_source_penalties(self) -> Dict[str, float]:
        """Get source quality penalties.
        
        Returns:
            Dict with keys: primary, secondary.
        """
        return self.freshness_config["source_penalties"]
