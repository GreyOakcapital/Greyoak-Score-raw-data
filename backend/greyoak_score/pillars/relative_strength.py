"""Relative Strength (R) Pillar - Risk-adjusted alpha calculation."""

from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

from greyoak_score.pillars.base import BasePillar
from greyoak_score.utils.logger import get_logger

logger = get_logger(__name__)


class RelativeStrengthPillar(BasePillar):
    """Relative Strength Pillar Calculator.
    
    Calculates risk-adjusted alpha vs sector and market (NIFTY) across:
    - 1M (21 days): 45% weight
    - 3M (63 days): 35% weight  
    - 6M (126 days): 20% weight
    
    Alpha weights: sector 60%, market 40%
    
    Formula: alpha = (stock_return - benchmark_return) / stock_volatility
    Final score is percentile-ranked alpha converted to 0-100 points.
    """
    
    @property
    def pillar_name(self) -> str:
        return "R"
    
    def calculate(
        self,
        prices_df: pd.DataFrame,
        fundamentals_df: pd.DataFrame,
        ownership_df: pd.DataFrame,
        sector_map_df: pd.DataFrame,
        mode: str = "trader",
        **kwargs
    ) -> pd.DataFrame:
        """Calculate Relative Strength pillar scores.
        
        Args:
            prices_df: Price data with return and volatility columns
            fundamentals_df: Not used for relative strength
            ownership_df: Not used for relative strength
            sector_map_df: Sector mapping for sector benchmark
            mode: Trading mode (not used for R scoring logic)
            
        Returns:
            DataFrame with R_score and R_details columns
        """
        logger.info("🚀 Calculating Relative Strength (R) Pillar...")
        
        # Validate inputs
        self.validate_inputs(prices_df, fundamentals_df, ownership_df, sector_map_df)
        self._validate_returns_data(prices_df)
        
        # Get configuration
        config = self.config.get_relative_strength_config()
        horizon_weights = config["horizon_weights"]
        alpha_weights = config["alpha_weights"]
        
        logger.info(f"  📊 Processing returns for {prices_df['ticker'].nunique()} stocks")
        
        # Get latest data with returns and volatility
        latest_prices = self.get_latest_data_by_ticker(prices_df)
        
        # Merge with sector information
        prices_with_sector = self.merge_sector_data(latest_prices, sector_map_df)
        
        # Calculate sector benchmarks
        sector_benchmarks = self._calculate_sector_benchmarks(prices_with_sector)
        
        # Calculate market benchmark (assume equal-weighted for now)
        market_benchmark = self._calculate_market_benchmark(prices_with_sector)
        
        logger.info(f"  🎯 Calculated benchmarks for {len(sector_benchmarks)} sectors")
        
        # Calculate alpha scores for each stock
        results = []
        
        for _, row in prices_with_sector.iterrows():
            ticker = row['ticker']
            sector = row['sector_group']
            
            # Get benchmarks for this stock's sector
            sector_returns = sector_benchmarks.get(sector, {})
            
            # Calculate alpha for each horizon
            alpha_scores = {}
            horizon_details = {}
            
            for horizon in ["1M", "3M", "6M"]:
                return_col = self._get_return_column(horizon)
                vol_col = self._get_volatility_column(horizon)
                
                alpha_score, details = self._calculate_horizon_alpha(
                    row, sector_returns, market_benchmark, horizon, 
                    return_col, vol_col, alpha_weights
                )
                
                alpha_scores[horizon] = alpha_score
                horizon_details[horizon] = details
            
            # Weight alpha scores by horizon
            weighted_alpha = sum(
                alpha_scores[horizon] * horizon_weights[horizon] 
                for horizon in horizon_weights
            )
            
            results.append({
                'ticker': ticker,
                'sector_group': sector,
                'weighted_alpha': weighted_alpha,
                'horizon_alphas': alpha_scores,
                'horizon_details': horizon_details
            })
        
        # Convert to DataFrame for percentile ranking
        results_df = pd.DataFrame(results)
        
        # Rank alphas to get 0-100 scores
        if len(results_df) > 0:
            results_df['alpha_rank'] = results_df['weighted_alpha'].rank(pct=True) * 100
            # Handle edge case of identical values
            results_df['alpha_rank'] = results_df['alpha_rank'].fillna(50.0)
        else:
            results_df['alpha_rank'] = []
        
        # Prepare final output
        final_results = []
        
        for _, row in results_df.iterrows():
            final_results.append({
                'ticker': row['ticker'],
                'R_score': row['alpha_rank'],
                'R_details': {
                    "weighted_alpha": row['weighted_alpha'],
                    "horizon_alphas": row['horizon_alphas'],
                    "horizon_details": row['horizon_details'],
                    "percentile_rank": row['alpha_rank'],
                    "config_used": {
                        "horizon_weights": horizon_weights,
                        "alpha_weights": alpha_weights
                    }
                }
            })
        
        result_df = pd.DataFrame(final_results)
        
        # Log summary statistics
        if len(result_df) > 0:
            scores = result_df['R_score'].values
            logger.info(f"✅ Relative Strength pillar complete: mean={np.mean(scores):.1f}, "
                       f"min={np.min(scores):.1f}, max={np.max(scores):.1f}")
        else:
            logger.warning("⚠️ No relative strength scores calculated")
        
        return result_df[['ticker', 'R_score', 'R_details']]
    
    def _validate_returns_data(self, prices_df: pd.DataFrame) -> None:
        """Validate price data has required return and volatility columns."""
        required_cols = [
            'ticker', 'ret_21d', 'ret_63d', 'ret_126d', 
            'sigma20', 'sigma60'
        ]
        missing_cols = [col for col in required_cols if col not in prices_df.columns]
        if missing_cols:
            raise ValueError(f"Missing required return/volatility columns: {missing_cols}")
    
    def _get_return_column(self, horizon: str) -> str:
        """Map horizon to return column name."""
        mapping = {
            "1M": "ret_21d",
            "3M": "ret_63d", 
            "6M": "ret_126d"
        }
        return mapping[horizon]
    
    def _get_volatility_column(self, horizon: str) -> str:
        """Map horizon to volatility column name."""
        mapping = {
            "1M": "sigma20",  # Use 20-day vol for 1M
            "3M": "sigma60",  # Use 60-day vol for 3M+
            "6M": "sigma60"   # Use 60-day vol for 6M
        }
        return mapping[horizon]
    
    def _calculate_sector_benchmarks(self, prices_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Calculate sector benchmark returns (equal-weighted averages).
        
        Returns:
            Dict[sector_group -> Dict[horizon -> return]]
        """
        sector_benchmarks = {}
        
        # Group by sector
        for sector, sector_data in prices_df.groupby('sector_group'):
            if pd.isna(sector):
                continue
            
            sector_returns = {}
            
            for horizon in ["1M", "3M", "6M"]:
                return_col = self._get_return_column(horizon)
                
                # Calculate equal-weighted average return for sector
                valid_returns = sector_data[return_col].dropna()
                if len(valid_returns) > 0:
                    sector_returns[horizon] = valid_returns.mean()
                else:
                    sector_returns[horizon] = 0.0
            
            sector_benchmarks[sector] = sector_returns
        
        return sector_benchmarks
    
    def _calculate_market_benchmark(self, prices_df: pd.DataFrame) -> Dict[str, float]:
        """Calculate market benchmark returns (equal-weighted).
        
        Returns:
            Dict[horizon -> return]
        """
        market_returns = {}
        
        for horizon in ["1M", "3M", "6M"]:
            return_col = self._get_return_column(horizon)
            
            # Calculate equal-weighted market return
            valid_returns = prices_df[return_col].dropna()
            if len(valid_returns) > 0:
                market_returns[horizon] = valid_returns.mean()
            else:
                market_returns[horizon] = 0.0
        
        return market_returns
    
    def _calculate_horizon_alpha(
        self, 
        stock_row: pd.Series,
        sector_returns: Dict[str, float],
        market_returns: Dict[str, float],
        horizon: str,
        return_col: str,
        vol_col: str,
        alpha_weights: Dict[str, float]
    ) -> Tuple[float, Dict]:
        """Calculate risk-adjusted alpha for one horizon.
        
        Returns:
            (alpha_score, details_dict)
        """
        stock_return = stock_row.get(return_col)
        stock_vol = stock_row.get(vol_col)
        
        # Handle missing data
        if pd.isna(stock_return) or pd.isna(stock_vol) or stock_vol <= 0:
            return 0.0, {
                "stock_return": stock_return,
                "stock_volatility": stock_vol,
                "alpha": 0.0,
                "reason": "missing_or_invalid_data"
            }
        
        # Get benchmark returns
        sector_return = sector_returns.get(horizon, 0.0)
        market_return = market_returns.get(horizon, 0.0)
        
        # Calculate excess returns vs benchmarks
        sector_excess = stock_return - sector_return
        market_excess = stock_return - market_return
        
        # Calculate risk-adjusted alphas
        sector_alpha = sector_excess / stock_vol
        market_alpha = market_excess / stock_vol
        
        # Weighted combination
        combined_alpha = (
            sector_alpha * alpha_weights["sector"] + 
            market_alpha * alpha_weights["market"]
        )
        
        details = {
            "stock_return": stock_return,
            "stock_volatility": stock_vol,
            "sector_return": sector_return,
            "market_return": market_return,
            "sector_excess": sector_excess,
            "market_excess": market_excess,
            "sector_alpha": sector_alpha,
            "market_alpha": market_alpha,
            "combined_alpha": combined_alpha,
            "alpha_weights": alpha_weights
        }
        
        return combined_alpha, details