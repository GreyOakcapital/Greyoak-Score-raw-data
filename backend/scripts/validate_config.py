#!/usr/bin/env python3
"""Validate YAML configuration files.

Checks:
- All pillar weights sum to 1.0 (every sector, every mode)
- Band thresholds monotonic (strong_buy > buy > hold > 0)
- No missing required fields in YAML
- No typos in sector names
- RP caps in valid range (0, 20]
- Pledge penalty curve monotonic
- Freshness SLOs > 0

Usage:
    python scripts/validate_config.py

Exit code 0 if valid, 1 if errors found.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from greyoak_score.core.config_manager import ConfigManager
from greyoak_score.utils.logger import setup_logger

logger = setup_logger("validate_config", "INFO")


def main() -> int:
    """
    Validate all configuration files.
    
    Returns:
        0 if validation passes, 1 if errors found.
    """
    logger.info("━" * 80)
    logger.info("✅ Validating GreyOak Score Engine Configuration")
    logger.info("━" * 80)
    
    config_dir = Path(__file__).parent.parent / "configs"
    
    if not config_dir.exists():
        logger.error(f"❌ Config directory not found: {config_dir}")
        return 1
    
    try:
        # Load configuration (validation happens in __init__)
        config = ConfigManager(config_dir)
        
        logger.info(f"✅ All config files loaded successfully")
        logger.info(f"   Config hash: {config.config_hash}")
        logger.info(f"   Mode: {config.mode}")
        
        # Additional validation checks
        logger.info("\n✅ Running additional validation checks...")
        
        # Check all sectors referenced in pillar weights exist in sector_map
        logger.info("   Checking sector name consistency...")
        sector_groups_in_map = set(config.sector_map_config["sector_groups"].keys())
        
        for mode in ["trader", "investor"]:
            sectors_in_weights = set(
                config.score_config["pillar_weights"][mode].keys()
            )
            # Remove 'default' as it's not a real sector
            sectors_in_weights.discard("default")
            
            # Check if all weighted sectors are defined in sector_map
            undefined_sectors = sectors_in_weights - sector_groups_in_map
            if undefined_sectors:
                logger.warning(
                    f"   ⚠️  Sectors in {mode} weights but not in sector_map: {undefined_sectors}"
                )
        
        # Check confidence weights sum to 1.0
        logger.info("   Checking confidence weights...")
        conf_weights = config.get_confidence_weights()
        conf_sum = sum(conf_weights.values())
        if abs(conf_sum - 1.0) > 1e-6:
            logger.error(
                f"❌ Confidence weights sum to {conf_sum:.6f}, not 1.0: {conf_weights}"
            )
            return 1
        logger.info(f"      Confidence weights sum to {conf_sum:.6f} ✅")
        
        # Check freshness SLOs are positive
        logger.info("   Checking freshness SLOs...")
        slos = config.get_freshness_slos()
        for domain, days in slos.items():
            if days <= 0:
                logger.error(f"❌ Freshness SLO for {domain} is {days}, must be > 0")
                return 1
        logger.info(f"      All freshness SLOs positive ✅")
        
        # Check sub-pillar weights
        logger.info("   Checking sub-pillar weights...")
        
        # Fundamentals
        for is_banking in [False, True]:
            weights = config.get_fundamentals_weights(is_banking)
            total = sum(weights.values())
            sector_type = "banking" if is_banking else "non_financial"
            if abs(total - 1.0) > 1e-6:
                logger.error(
                    f"❌ Fundamentals {sector_type} weights sum to {total:.6f}, not 1.0"
                )
                return 1
            logger.info(f"      Fundamentals ({sector_type}) weights sum to {total:.6f} ✅")
        
        # Technicals
        tech_config = config.get_technicals_config()
        tech_weights = tech_config["weights"]
        tech_sum = sum(tech_weights.values())
        if abs(tech_sum - 1.0) > 1e-6:
            logger.error(
                f"❌ Technicals weights sum to {tech_sum:.6f}, not 1.0"
            )
            return 1
        logger.info(f"      Technicals weights sum to {tech_sum:.6f} ✅")
        
        # Ownership
        own_config = config.get_ownership_config()
        own_weights = own_config["weights"]
        own_sum = sum(own_weights.values())
        if abs(own_sum - 1.0) > 1e-6:
            logger.error(
                f"❌ Ownership weights sum to {own_sum:.6f}, not 1.0"
            )
            return 1
        logger.info(f"      Ownership weights sum to {own_sum:.6f} ✅")
        
        # Quality
        qual_weights = config.get_quality_config()
        qual_sum = sum(qual_weights.values())
        if abs(qual_sum - 1.0) > 1e-6:
            logger.error(
                f"❌ Quality weights sum to {qual_sum:.6f}, not 1.0"
            )
            return 1
        logger.info(f"      Quality weights sum to {qual_sum:.6f} ✅")
        
        logger.info("\n" + "━" * 80)
        logger.info("✅ All validation checks passed!")
        logger.info("━" * 80)
        
        return 0
    
    except Exception as e:
        logger.error(f"\n❌ Validation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
