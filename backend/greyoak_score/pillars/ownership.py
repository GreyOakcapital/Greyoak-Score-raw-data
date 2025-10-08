"""Ownership (O) Pillar - Promoter holdings, pledge penalty, FII/DII changes."""

from typing import Dict, Any
import pandas as pd
import numpy as np

from greyoak_score.pillars.base import BasePillar
from greyoak_score.core.normalization import batch_normalize_metrics
from greyoak_score.utils.logger import get_logger

logger = get_logger(__name__)


class OwnershipPillar(BasePillar):
    """Ownership Pillar Calculator.
    
    Three components with individual weights:
    1. Promoter holding % (30% weight) - higher is better
    2. Pledge penalty (30% weight) - penalty curve applied to pledge fraction
    3. FII/DII change (40% weight) - positive change is better
    
    Note: This is O pillar penalty only. RP bins and PledgeCap guardrail are separate.
    """
    
    @property
    def pillar_name(self) -> str:
        return "O"
    
    def calculate(
        self,
        prices_df: pd.DataFrame,
        fundamentals_df: pd.DataFrame,
        ownership_df: pd.DataFrame,
        sector_map_df: pd.DataFrame,
        mode: str = "trader",
        **kwargs
    ) -> pd.DataFrame:
        """Calculate Ownership pillar scores.
        
        Args:
            prices_df: Price data (not used for ownership)
            fundamentals_df: Fundamentals data (not used for ownership)
            ownership_df: Ownership structure data
            sector_map_df: Sector mapping
            mode: Trading mode (not used for O scoring logic)
            
        Returns:
            DataFrame with O_score and O_details columns
        """
        logger.info("🏢 Calculating Ownership (O) Pillar...")
        
        # Validate inputs
        self.validate_inputs(prices_df, fundamentals_df, ownership_df, sector_map_df)
        self._validate_ownership_data(ownership_df)
        
        # Get configuration
        config = self.config.get_ownership_config()
        weights = config["weights"]
        pledge_curve = config["pledge_penalty_curve"]
        
        # Get latest ownership data
        latest_ownership = self.get_latest_data_by_ticker(ownership_df)
        
        # Merge with sector information
        ownership_with_sector = self.merge_sector_data(latest_ownership, sector_map_df)
        
        logger.info(f"  📊 Processing {len(ownership_with_sector)} stocks for ownership analysis")
        
        # Calculate individual components
        results = []
        
        for _, row in ownership_with_sector.iterrows():
            ticker = row['ticker']
            
            # Calculate three components
            promoter_score = self._calculate_promoter_component(row, ownership_with_sector)
            pledge_score = self._calculate_pledge_component(row, pledge_curve, ownership_with_sector)
            fii_dii_score = self._calculate_fii_dii_component(row, ownership_with_sector)
            
            # Calculate weighted O score
            components = {
                "promoter_hold": {"score": promoter_score, "weight": weights["promoter_hold"]},
                "pledge": {"score": pledge_score, "weight": weights["pledge"]},
                "fii_dii_change": {"score": fii_dii_score, "weight": weights["fii_dii_change"]}
            }
            
            # Weighted average
            total_score = sum(comp["score"] * comp["weight"] for comp in components.values())
            total_weight = sum(comp["weight"] for comp in components.values())
            
            final_score = total_score / total_weight if total_weight > 0 else 0.0
            
            results.append({
                'ticker': ticker,
                'O_score': final_score,
                'O_details': {
                    "components": components,
                    "final_score": final_score,
                    "config_used": {
                        "weights": weights,
                        "pledge_curve": pledge_curve
                    }
                }
            })
        
        result_df = pd.DataFrame(results)
        
        # Log summary statistics
        if len(result_df) > 0:
            scores = result_df['O_score'].values
            logger.info(f"✅ Ownership pillar complete: mean={np.mean(scores):.1f}, "
                       f"min={np.min(scores):.1f}, max={np.max(scores):.1f}")
        else:
            logger.warning("⚠️ No ownership scores calculated")
        
        return result_df[['ticker', 'O_score', 'O_details']]
    
    def _validate_ownership_data(self, ownership_df: pd.DataFrame) -> None:
        """Validate ownership data has required columns."""
        required_cols = ['ticker', 'quarter_end']
        missing_cols = [col for col in required_cols if col not in ownership_df.columns]
        if missing_cols:
            raise ValueError(f"Missing required ownership columns: {missing_cols}")
    
    def _calculate_promoter_component(self, row: pd.Series, all_data: pd.DataFrame) -> float:
        """Calculate promoter holding component (higher is better).
        
        Sector-normalized promoter holding percentage.
        """
        promoter_hold = row.get('promoter_hold_pct')
        
        if pd.isna(promoter_hold):
            return 50.0  # Neutral if missing
        
        # Sector normalize within the current dataset
        sector_data = all_data[all_data['sector_group'] == row['sector_group']]
        
        if len(sector_data) <= 1:
            return 50.0  # Neutral if insufficient sector data
        
        # Calculate percentile within sector
        promoter_values = sector_data['promoter_hold_pct'].dropna()
        if len(promoter_values) <= 1:
            return 50.0
        
        percentile = (promoter_values < promoter_hold).mean() * 100
        return min(100.0, max(0.0, percentile))
    
    def _calculate_pledge_component(
        self, 
        row: pd.Series, 
        pledge_curve: list, 
        all_data: pd.DataFrame
    ) -> float:
        """Calculate pledge component with penalty curve.
        
        Process:
        1. Sector-normalize pledge fraction (inverted: lower pledge = higher points)
        2. Apply penalty curve to reduce points based on absolute pledge level
        3. Return final score (0-100)
        """
        pledge_frac = row.get('promoter_pledge_frac')
        
        if pd.isna(pledge_frac):
            return 50.0  # Neutral if missing
        
        # Step 1: Sector normalize (inverted - lower pledge is better)
        sector_data = all_data[all_data['sector_group'] == row['sector_group']]
        
        if len(sector_data) <= 1:
            base_score = 50.0  # Neutral if insufficient sector data
        else:
            pledge_values = sector_data['promoter_pledge_frac'].dropna()
            if len(pledge_values) <= 1:
                base_score = 50.0
            else:
                # Inverted percentile (lower pledge = higher score)
                percentile = (pledge_values > pledge_frac).mean() * 100
                base_score = min(100.0, max(0.0, percentile))
        
        # Step 2: Apply pledge penalty curve
        penalty = self._calculate_pledge_penalty(pledge_frac, pledge_curve)
        
        # Step 3: Subtract penalty from base score
        final_score = max(0.0, base_score - penalty)
        
        return final_score
    
    def _calculate_pledge_penalty(self, pledge_frac: float, pledge_curve: list) -> float:
        """Calculate penalty based on pledge penalty curve.
        
        Curve: [(0%, 0), (5%, 5), (10%, 10), (20%, 20), (100%, 30)]
        Linear interpolation between points.
        """
        if pd.isna(pledge_frac) or pledge_frac < 0:
            return 0.0
        
        # Sort curve points by fraction
        sorted_points = sorted(pledge_curve, key=lambda x: x['fraction'])
        
        # Find the two points to interpolate between
        for i in range(len(sorted_points) - 1):
            x1, y1 = sorted_points[i]['fraction'], sorted_points[i]['penalty']
            x2, y2 = sorted_points[i + 1]['fraction'], sorted_points[i + 1]['penalty']
            
            if x1 <= pledge_frac <= x2:
                # Linear interpolation
                if x2 == x1:
                    return y1
                penalty = y1 + (y2 - y1) * (pledge_frac - x1) / (x2 - x1)
                return penalty
        
        # If beyond the curve, use the last point's penalty
        return sorted_points[-1]['penalty']
    
    def _calculate_fii_dii_component(self, row: pd.Series, all_data: pd.DataFrame) -> float:
        """Calculate FII/DII change component (positive change is better).
        
        Sector-normalized FII/DII delta in percentage points.
        """
        fii_dii_delta = row.get('fii_dii_delta_pp')
        
        if pd.isna(fii_dii_delta):
            return 50.0  # Neutral if missing
        
        # Sector normalize within the current dataset
        sector_data = all_data[all_data['sector_group'] == row['sector_group']]
        
        if len(sector_data) <= 1:
            return 50.0  # Neutral if insufficient sector data
        
        # Calculate percentile within sector (higher delta = higher score)
        delta_values = sector_data['fii_dii_delta_pp'].dropna()
        if len(delta_values) <= 1:
            return 50.0
        
        percentile = (delta_values < fii_dii_delta).mean() * 100
        return min(100.0, max(0.0, percentile))