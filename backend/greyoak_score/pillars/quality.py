"""Quality (Q) Pillar - ROCE stability and operational margin consistency."""

from typing import Dict, Any
import pandas as pd
import numpy as np

from greyoak_score.pillars.base import BasePillar
from greyoak_score.core.normalization import batch_normalize_metrics
from greyoak_score.utils.logger import get_logger

logger = get_logger(__name__)


class QualityPillar(BasePillar):
    """Quality Pillar Calculator.
    
    Two components measuring business quality:
    1. ROCE 3Y (65% weight) - higher is better
    2. OPM stability (35% weight) - lower standard deviation is better
    
    Simpler than other pillars - just two metrics with sector normalization.
    """
    
    @property
    def pillar_name(self) -> str:
        return "Q"
    
    def calculate(
        self,
        prices_df: pd.DataFrame,
        fundamentals_df: pd.DataFrame,
        ownership_df: pd.DataFrame,
        sector_map_df: pd.DataFrame,
        mode: str = "trader",
        **kwargs
    ) -> pd.DataFrame:
        """Calculate Quality pillar scores.
        
        Args:
            prices_df: Price data (not used for quality)
            fundamentals_df: Fundamental metrics data
            ownership_df: Ownership data (not used for quality)
            sector_map_df: Sector mapping
            mode: Trading mode (not used for Q scoring logic)
            
        Returns:
            DataFrame with Q_score and Q_details columns
        """
        logger.info("💎 Calculating Quality (Q) Pillar...")
        
        # Validate inputs
        self.validate_inputs(prices_df, fundamentals_df, ownership_df, sector_map_df)
        self._validate_quality_data(fundamentals_df)
        
        # Get configuration
        config = self.config.get_quality_config()
        weights = config["weights"]
        
        # Get latest fundamentals data
        latest_fund = self.get_latest_data_by_ticker(fundamentals_df)
        
        # Merge with sector information
        fund_with_sector = self.merge_sector_data(latest_fund, sector_map_df)
        
        logger.info(f"  💎 Processing {len(fund_with_sector)} stocks for quality analysis")
        
        # Define metrics and their direction
        metrics_config = {
            "roce_3y": True,        # Higher ROCE is better
            "opm_stdev_12q": False  # Lower OPM standard deviation is better
        }
        
        # Normalize metrics sector-wise
        normalized_df = batch_normalize_metrics(
            fund_with_sector,
            metrics_config,
            sector_col="sector_group"
        )
        
        # Calculate weighted Q score
        results = []
        
        for _, row in normalized_df.iterrows():
            ticker = row['ticker']
            
            components = {}
            weighted_score = 0.0
            total_weight = 0.0
            
            # Calculate weighted average of available components
            for metric, weight in weights.items():
                points_col = f"{metric}_points"
                if points_col in row and not pd.isna(row[points_col]):
                    component_score = row[points_col]
                    weighted_score += component_score * weight
                    total_weight += weight
                    components[metric] = {
                        "raw_value": row.get(metric, np.nan),
                        "points": component_score,
                        "weight": weight
                    }
            
            # Normalize by actual total weight (in case some metrics missing)
            if total_weight > 0:
                final_score = weighted_score / total_weight
            else:
                final_score = 0.0
            
            results.append({
                'ticker': ticker,
                'Q_score': final_score,
                'Q_details': {
                    "components": components,
                    "total_weight_used": total_weight,
                    "raw_score": weighted_score,
                    "final_score": final_score,
                    "config_used": {
                        "weights": weights
                    }
                }
            })
        
        result_df = pd.DataFrame(results)
        
        # Log summary statistics
        if len(result_df) > 0:
            scores = result_df['Q_score'].values
            logger.info(f"✅ Quality pillar complete: mean={np.mean(scores):.1f}, "
                       f"min={np.min(scores):.1f}, max={np.max(scores):.1f}")
        else:
            logger.warning("⚠️ No quality scores calculated")
        
        return result_df[['ticker', 'Q_score', 'Q_details']]
    
    def _validate_quality_data(self, fundamentals_df: pd.DataFrame) -> None:
        """Validate fundamentals data has required columns for quality metrics."""
        required_cols = ['ticker', 'quarter_end']
        missing_cols = [col for col in required_cols if col not in fundamentals_df.columns]
        if missing_cols:
            raise ValueError(f"Missing required fundamentals columns for quality: {missing_cols}")
        
        # Check if we have at least one quality metric
        quality_metrics = ['roce_3y', 'opm_stdev_12q']
        available_metrics = [col for col in quality_metrics if col in fundamentals_df.columns]
        
        if not available_metrics:
            logger.warning(f"⚠️ No quality metrics available in fundamentals data. "
                          f"Expected: {quality_metrics}")
        else:
            logger.info(f"  📊 Available quality metrics: {available_metrics}")
    
    def get_missing_metrics_summary(self, fundamentals_df: pd.DataFrame) -> Dict[str, float]:
        """Get summary of missing data for quality metrics.
        
        Returns:
            Dict with metric names and fraction of missing values
        """
        quality_metrics = ['roce_3y', 'omp_stdev_12q']
        missing_summary = {}
        
        for metric in quality_metrics:
            if metric in fundamentals_df.columns:
                missing_frac = fundamentals_df[metric].isna().mean()
                missing_summary[metric] = missing_frac
            else:
                missing_summary[metric] = 1.0  # Completely missing
        
        return missing_summary