"""Fundamentals (F) Pillar - Banking vs Non-financial logic."""

from typing import Dict, Any
import pandas as pd
import numpy as np

from greyoak_score.pillars.base import BasePillar
from greyoak_score.core.normalization import batch_normalize_metrics
from greyoak_score.utils.logger import get_logger

logger = get_logger(__name__)


class FundamentalsPillar(BasePillar):
    """Fundamentals Pillar Calculator.
    
    Implements separate logic for banking vs non-financial stocks:
    - Non-financial: ROE, Sales CAGR, EPS CAGR, Valuation (PE/EV-EBITDA)
    - Banking: ROA, ROE, GNPA%, PCR%, NIM
    
    All metrics are sector-normalized before weighted aggregation.
    """
    
    @property
    def pillar_name(self) -> str:
        return "F"
    
    def calculate(
        self,
        prices_df: pd.DataFrame,
        fundamentals_df: pd.DataFrame,
        ownership_df: pd.DataFrame,
        sector_map_df: pd.DataFrame,
        mode: str = "trader",
        **kwargs
    ) -> pd.DataFrame:
        """Calculate Fundamentals pillar scores.
        
        Args:
            prices_df: Price data (not used for fundamentals)
            fundamentals_df: Fundamental metrics
            ownership_df: Ownership data (not used for fundamentals)
            sector_map_df: Sector mapping for banking classification
            mode: Trading mode (affects weights in final scoring)
            
        Returns:
            DataFrame with F_score and F_details columns
        """
        logger.info("🏛️ Calculating Fundamentals (F) Pillar...")
        
        # Validate inputs
        self.validate_inputs(prices_df, fundamentals_df, ownership_df, sector_map_df)
        self._validate_fundamentals_data(fundamentals_df)
        
        # Get latest fundamentals data
        latest_fund = self.get_latest_data_by_ticker(fundamentals_df)
        
        # Merge with sector information
        fund_with_sector = self.merge_sector_data(latest_fund, sector_map_df)
        
        logger.info(f"  📊 Processing {len(fund_with_sector)} stocks across sectors")
        
        # Split into banking and non-financial
        banking_stocks = fund_with_sector[
            fund_with_sector['sector_group'].apply(self.is_banking_sector)
        ].copy()
        
        non_financial_stocks = fund_with_sector[
            ~fund_with_sector['sector_group'].apply(self.is_banking_sector)
        ].copy()
        
        logger.info(f"  🏦 Banking stocks: {len(banking_stocks)}")
        logger.info(f"  🏭 Non-financial stocks: {len(non_financial_stocks)}")
        
        results = []
        
        # Process non-financial stocks
        if len(non_financial_stocks) > 0:
            non_financial_results = self._calculate_non_financial_scores(non_financial_stocks)
            results.append(non_financial_results)
        
        # Process banking stocks
        if len(banking_stocks) > 0:
            banking_results = self._calculate_banking_scores(banking_stocks)
            results.append(banking_results)
        
        # Combine results
        if results:
            final_results = pd.concat(results, ignore_index=True)
        else:
            # Empty result with proper structure
            final_results = pd.DataFrame(columns=['ticker', 'F_score', 'F_details'])
        
        logger.info(f"✅ Fundamentals pillar complete: {len(final_results)} stocks scored")
        
        return final_results[['ticker', 'F_score', 'F_details']]
    
    def _validate_fundamentals_data(self, fundamentals_df: pd.DataFrame) -> None:
        """Validate fundamentals data has required columns."""
        required_cols = ['ticker', 'quarter_end']
        missing_cols = [col for col in required_cols if col not in fundamentals_df.columns]
        if missing_cols:
            raise ValueError(f"Missing required fundamentals columns: {missing_cols}")
    
    def _calculate_non_financial_scores(self, stocks_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate F scores for non-financial stocks.
        
        Metrics: ROE, Sales CAGR, EPS CAGR, Valuation (PE/EV-EBITDA)
        """
        logger.info("  📈 Processing non-financial stocks...")
        
        # Get configuration
        weights = self.config.get_non_financial_fundamentals_weights()
        
        # Define metrics and their direction (True = higher better, False = lower better)
        metrics_config = {
            "roe_3y": True,      # Higher ROE is better
            "sales_cagr_3y": True,   # Higher growth is better
            "eps_cagr_3y": True,     # Higher growth is better
            "valuation": False       # Lower valuation is better (PE/EV-EBITDA)
        }
        
        # Prepare valuation metric (prefer EV/EBITDA, fallback to PE)
        stocks_df = stocks_df.copy()
        stocks_df['valuation'] = stocks_df['ev_ebitda'].fillna(stocks_df['pe'])
        
        # Normalize metrics sector-wise
        normalized_df = batch_normalize_metrics(
            stocks_df, 
            metrics_config,
            sector_col="sector_group"
        )
        
        # Calculate weighted F score
        f_scores = []
        f_details = []
        
        for _, row in normalized_df.iterrows():
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
            
            f_scores.append(final_score)
            f_details.append({
                "pillar_type": "non_financial",
                "components": components,
                "total_weight_used": total_weight,
                "raw_score": weighted_score,
                "final_score": final_score
            })
        
        result_df = pd.DataFrame({
            'ticker': normalized_df['ticker'],
            'F_score': f_scores,
            'F_details': f_details
        })
        
        logger.info(f"    ✅ Non-financial F scores: mean={np.mean(f_scores):.1f}, "
                   f"min={np.min(f_scores):.1f}, max={np.max(f_scores):.1f}")
        
        return result_df
    
    def _calculate_banking_scores(self, stocks_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate F scores for banking stocks.
        
        Metrics: ROA, ROE, GNPA%, PCR%, NIM
        """
        logger.info("  🏦 Processing banking stocks...")
        
        # Get configuration
        weights = self.config.get_banking_fundamentals_weights()
        
        # Define metrics and their direction
        metrics_config = {
            "roa_3y": True,       # Higher ROA is better
            "roe_3y": True,       # Higher ROE is better
            "gnpa_pct": False,    # Lower GNPA is better
            "pcr_pct": True,      # Higher PCR is better
            "nim_3y": True        # Higher NIM is better
        }
        
        # Normalize metrics sector-wise (within banking sector)
        normalized_df = batch_normalize_metrics(
            stocks_df,
            metrics_config,
            sector_col="sector_group"
        )
        
        # Calculate weighted F score
        f_scores = []
        f_details = []
        
        for _, row in normalized_df.iterrows():
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
            
            f_scores.append(final_score)
            f_details.append({
                "pillar_type": "banking",
                "components": components,
                "total_weight_used": total_weight,
                "raw_score": weighted_score,
                "final_score": final_score
            })
        
        result_df = pd.DataFrame({
            'ticker': normalized_df['ticker'],
            'F_score': f_scores,
            'F_details': f_details
        })
        
        logger.info(f"    ✅ Banking F scores: mean={np.mean(f_scores):.1f}, "
                   f"min={np.min(f_scores):.1f}, max={np.max(f_scores):.1f}")
        
        return result_df