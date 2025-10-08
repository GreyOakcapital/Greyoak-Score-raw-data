"""Sector Momentum (S) Pillar - Cross-sector momentum with S_z tracking."""

from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
from scipy import stats

from greyoak_score.pillars.base import BasePillar
from greyoak_score.utils.logger import get_logger

logger = get_logger(__name__)


class SectorMomentumPillar(BasePillar):
    """Sector Momentum Pillar Calculator.
    
    CRITICAL: This pillar tracks S_z (sector momentum z-score) for guardrails.
    
    Cross-sector momentum calculation across three horizons:
    - 1M (20% weight): 21-day returns
    - 3M (30% weight): 63-day returns  
    - 6M (50% weight): 126-day returns
    
    Formula for each horizon:
    1. sector_excess = sector_return - nifty_return
    2. ex_norm = sector_excess / (sector_sigma20 + 1e-8)
    3. S_z = cross-sector z-score of ex_norm
    4. Final S score = weighted percentile of S_z values
    
    Returns BOTH S_score (0-100) AND S_z (for guardrails).
    """
    
    @property
    def pillar_name(self) -> str:
        return "S"
    
    def calculate(
        self,
        prices_df: pd.DataFrame,
        fundamentals_df: pd.DataFrame,
        ownership_df: pd.DataFrame,
        sector_map_df: pd.DataFrame,
        mode: str = "trader",
        **kwargs
    ) -> pd.DataFrame:
        """Calculate Sector Momentum pillar scores with S_z tracking.
        
        Args:
            prices_df: Price data with return and volatility columns
            fundamentals_df: Not used for sector momentum
            ownership_df: Not used for sector momentum
            sector_map_df: Sector mapping
            mode: Trading mode (not used for S scoring logic)
            
        Returns:
            DataFrame with S_score, S_z, and S_details columns
        """
        logger.info("📈 Calculating Sector Momentum (S) Pillar...")
        
        # Validate inputs
        self.validate_inputs(prices_df, fundamentals_df, ownership_df, sector_map_df)
        self._validate_sector_momentum_data(prices_df)
        
        # Get configuration
        horizon_weights = self.config.get_sector_momentum_config()  # Returns horizon_weights directly
        
        # Get latest price data per ticker
        latest_prices = self.get_latest_data_by_ticker(prices_df)
        
        # Merge with sector information
        prices_with_sector = self.merge_sector_data(latest_prices, sector_map_df)
        
        logger.info(f"  📊 Processing sector momentum for {prices_with_sector['sector_group'].nunique()} sectors")
        
        # Calculate sector-level aggregates
        sector_aggregates = self._calculate_sector_aggregates(prices_with_sector)
        
        # Calculate market (NIFTY) benchmark - equal weighted for now
        market_benchmark = self._calculate_market_benchmark(prices_with_sector)
        
        # Calculate S_z for each sector and horizon
        sector_s_z_data = self._calculate_cross_sector_s_z(
            sector_aggregates, market_benchmark, horizon_weights
        )
        
        # Map S_z back to individual stocks and calculate final S scores
        results = []
        
        for _, row in prices_with_sector.iterrows():
            ticker = row['ticker']
            sector = row['sector_group']
            
            if pd.isna(sector) or sector not in sector_s_z_data:
                # Handle missing sector data
                results.append({
                    'ticker': ticker,
                    'S_score': 50.0,  # Neutral
                    'S_z': 0.0,       # Neutral S_z
                    'S_details': {
                        "reason": "missing_sector_data",
                        "sector_group": sector,
                        "horizon_s_z": {},
                        "weighted_s_z": 0.0,
                        "final_score": 50.0
                    }
                })
                continue
            
            sector_data = sector_s_z_data[sector]
            
            results.append({
                'ticker': ticker,
                'S_score': sector_data['s_score'],
                'S_z': sector_data['weighted_s_z'],  # CRITICAL: S_z for guardrails
                'S_details': {
                    "sector_group": sector,
                    "horizon_s_z": sector_data['horizon_s_z'],
                    "weighted_s_z": sector_data['weighted_s_z'],
                    "percentile_rank": sector_data['percentile_rank'],
                    "final_score": sector_data['s_score'],
                    "config_used": {
                        "horizon_weights": horizon_weights
                    }
                }
            })
        
        result_df = pd.DataFrame(results)
        
        # Log summary statistics
        if len(result_df) > 0:
            scores = result_df['S_score'].values
            s_z_values = result_df['S_z'].values
            logger.info(f"✅ Sector Momentum pillar complete:")
            logger.info(f"    S_score: mean={np.mean(scores):.1f}, min={np.min(scores):.1f}, max={np.max(scores):.1f}")
            logger.info(f"    S_z: mean={np.mean(s_z_values):.2f}, min={np.min(s_z_values):.2f}, max={np.max(s_z_values):.2f}")
        else:
            logger.warning("⚠️ No sector momentum scores calculated")
        
        return result_df[['ticker', 'S_score', 'S_z', 'S_details']]
    
    def _validate_sector_momentum_data(self, prices_df: pd.DataFrame) -> None:
        """Validate price data has required return and volatility columns."""
        required_cols = [
            'ticker', 'ret_21d', 'ret_63d', 'ret_126d', 'sigma20'
        ]
        missing_cols = [col for col in required_cols if col not in prices_df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns for sector momentum: {missing_cols}")
    
    def _calculate_sector_aggregates(self, prices_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate sector-level return and volatility aggregates.
        
        Returns:
            DataFrame with sector_group, ret_21d, ret_63d, ret_126d, sigma20
        """
        # Group by sector and calculate equal-weighted averages
        sector_aggs = prices_df.groupby('sector_group').agg({
            'ret_21d': 'mean',
            'ret_63d': 'mean', 
            'ret_126d': 'mean',
            'sigma20': 'mean'
        }).reset_index()
        
        # Remove any sectors with all NaN data
        sector_aggs = sector_aggs.dropna()
        
        logger.info(f"    📊 Calculated aggregates for {len(sector_aggs)} sectors")
        
        return sector_aggs
    
    def _calculate_market_benchmark(self, prices_df: pd.DataFrame) -> Dict[str, float]:
        """Calculate market (NIFTY) benchmark returns.
        
        For now, using equal-weighted market average.
        TODO: In future, could use actual NIFTY data.
        """
        market_returns = {
            'ret_21d': prices_df['ret_21d'].mean(),
            'ret_63d': prices_df['ret_63d'].mean(),
            'ret_126d': prices_df['ret_126d'].mean()
        }
        
        # Remove NaN values
        market_returns = {k: v for k, v in market_returns.items() if not pd.isna(v)}
        
        logger.info(f"    📈 Market benchmark: 1M={market_returns.get('ret_21d', 0):.1%}, "
                   f"3M={market_returns.get('ret_63d', 0):.1%}, 6M={market_returns.get('ret_126d', 0):.1%}")
        
        return market_returns
    
    def _calculate_cross_sector_s_z(
        self, 
        sector_aggs: pd.DataFrame,
        market_benchmark: Dict[str, float],
        horizon_weights: Dict[str, float]
    ) -> Dict[str, Dict]:
        """Calculate cross-sector S_z values for each horizon.
        
        CRITICAL: This is the core S_z calculation for guardrails.
        
        Returns:
            Dict[sector_group -> {"s_score": float, "S_z": float, "horizon_s_z": dict}]
        """
        horizons = {
            "1M": "ret_21d",
            "3M": "ret_63d", 
            "6M": "ret_126d"
        }
        
        sector_results = {}
        
        # Calculate S_z for each horizon across all sectors
        for horizon_name, return_col in horizons.items():
            if return_col not in sector_aggs.columns:
                continue
                
            market_return = market_benchmark.get(return_col, 0.0)
            
            # Calculate excess returns for each sector
            sector_excess = sector_aggs[return_col] - market_return
            
            # Normalize by sector volatility (with protection against zero)
            sector_volatility = sector_aggs['sigma20'] + 1e-8
            ex_norm = sector_excess / sector_volatility
            
            # Calculate cross-sector z-scores
            if len(ex_norm) > 1 and ex_norm.std() > 1e-8:
                s_z_values = (ex_norm - ex_norm.mean()) / ex_norm.std()
            else:
                s_z_values = pd.Series(0.0, index=ex_norm.index)
            
            # Store S_z values by sector
            for i, (_, row) in enumerate(sector_aggs.iterrows()):
                sector_group = row['sector_group']
                
                if sector_group not in sector_results:
                    sector_results[sector_group] = {
                        'horizon_s_z': {},
                        'ex_norm_values': {}
                    }
                
                sector_results[sector_group]['horizon_s_z'][horizon_name] = s_z_values.iloc[i]
                sector_results[sector_group]['ex_norm_values'][horizon_name] = ex_norm.iloc[i]
        
        # Calculate weighted S_z and convert to scores
        all_weighted_s_z = []
        
        for sector_group, data in sector_results.items():
            # Calculate weighted S_z across horizons
            weighted_s_z = sum(
                data['horizon_s_z'].get(horizon, 0.0) * weight
                for horizon, weight in horizon_weights.items()
            )
            
            data['weighted_s_z'] = weighted_s_z
            all_weighted_s_z.append(weighted_s_z)
        
        # Convert weighted S_z to percentile scores (0-100)
        if len(all_weighted_s_z) > 1:
            for sector_group in sector_results:
                s_z = sector_results[sector_group]['weighted_s_z']
                percentile = stats.percentileofscore(all_weighted_s_z, s_z, kind='rank')
                sector_results[sector_group]['percentile_rank'] = percentile
                sector_results[sector_group]['s_score'] = percentile
        else:
            # Single sector case
            for sector_group in sector_results:
                sector_results[sector_group]['percentile_rank'] = 50.0
                sector_results[sector_group]['s_score'] = 50.0
        
        logger.info(f"    ✅ Cross-sector S_z calculated for {len(sector_results)} sectors")
        
        return sector_results
    
    def get_sector_s_z_summary(self, result_df: pd.DataFrame) -> Dict[str, float]:
        """Get summary of S_z values by sector for debugging.
        
        Args:
            result_df: Result DataFrame from calculate() method
            
        Returns:
            Dict[sector_group -> mean_S_z]
        """
        if 'S_details' not in result_df.columns:
            return {}
        
        sector_s_z = {}
        for _, row in result_df.iterrows():
            details = row['S_details']
            sector = details.get('sector_group')
            s_z = row.get('S_z', 0.0)
            
            if sector and not pd.isna(s_z):
                if sector not in sector_s_z:
                    sector_s_z[sector] = []
                sector_s_z[sector].append(s_z)
        
        # Calculate means
        return {sector: np.mean(values) for sector, values in sector_s_z.items()}