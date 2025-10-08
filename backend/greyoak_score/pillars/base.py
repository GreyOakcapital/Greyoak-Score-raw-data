"""Base class for all pillar calculators."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd

from greyoak_score.core.config_manager import ConfigManager


class BasePillar(ABC):
    """Abstract base class for all GreyOak Score pillars.
    
    Each pillar must implement the calculate method and follow the standardized
    interface for scoring stocks based on different criteria.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize the pillar with configuration.
        
        Args:
            config_manager: Configuration manager instance with loaded configs
        """
        self.config = config_manager
        
    @abstractmethod
    def calculate(
        self,
        prices_df: pd.DataFrame,
        fundamentals_df: pd.DataFrame,
        ownership_df: pd.DataFrame,
        sector_map_df: pd.DataFrame,
        mode: str = "trader",
        **kwargs
    ) -> pd.DataFrame:
        """Calculate pillar scores for all stocks.
        
        Args:
            prices_df: Price and technical data
            fundamentals_df: Fundamental metrics data
            ownership_df: Ownership structure data
            sector_map_df: Ticker to sector mapping
            mode: Scoring mode ("trader" or "investor")
            **kwargs: Additional parameters specific to pillar
            
        Returns:
            DataFrame with columns:
            - ticker: Stock symbol
            - {pillar_name}_score: Raw pillar score (0-100)
            - {pillar_name}_details: Dict with breakdown/components
        """
        pass
    
    @property
    @abstractmethod
    def pillar_name(self) -> str:
        """Return the pillar name (F, T, R, O, Q, S)."""
        pass
    
    def validate_inputs(
        self,
        prices_df: pd.DataFrame,
        fundamentals_df: pd.DataFrame,
        ownership_df: pd.DataFrame,
        sector_map_df: pd.DataFrame
    ) -> None:
        """Validate that required input data is present.
        
        Args:
            prices_df: Price data
            fundamentals_df: Fundamentals data
            ownership_df: Ownership data
            sector_map_df: Sector mapping
            
        Raises:
            ValueError: If required data is missing
        """
        if len(prices_df) == 0:
            raise ValueError("Empty prices DataFrame")
        if len(sector_map_df) == 0:
            raise ValueError("Empty sector_map DataFrame")
        
        # Check required columns
        required_price_cols = ["ticker", "close", "trading_date"]
        missing_cols = [col for col in required_price_cols if col not in prices_df.columns]
        if missing_cols:
            raise ValueError(f"Missing required price columns: {missing_cols}")
    
    def get_sector_weights(self, mode: str, sector_group: str) -> Dict[str, float]:
        """Get pillar weights for specific sector and mode.
        
        Args:
            mode: Trading mode ("trader" or "investor")
            sector_group: Sector group name
            
        Returns:
            Dict with pillar weights (F, T, R, O, Q, S)
        """
        try:
            return self.config.get_pillar_weights(mode, sector_group)
        except Exception:
            # Fallback to default weights
            return self.config.get_pillar_weights(mode, "default")
    
    def is_banking_sector(self, sector_group: str) -> bool:
        """Check if sector is banking/NBFC.
        
        Args:
            sector_group: Sector group name
            
        Returns:
            True if banking sector
        """
        return self.config.is_banking_sector(sector_group)
    
    def get_latest_data_by_ticker(self, df: pd.DataFrame) -> pd.DataFrame:
        """Get most recent record for each ticker.
        
        Args:
            df: DataFrame with 'ticker' and date column
            
        Returns:
            DataFrame with latest record per ticker
        """
        if 'trading_date' in df.columns:
            date_col = 'trading_date'
        elif 'scoring_date' in df.columns:
            date_col = 'scoring_date'
        elif 'quarter_end' in df.columns:
            date_col = 'quarter_end'
        else:
            # If no date column, assume already filtered
            return df.drop_duplicates('ticker', keep='last')
        
        return df.sort_values(date_col).drop_duplicates('ticker', keep='last')
    
    def merge_sector_data(
        self,
        stock_df: pd.DataFrame,
        sector_map_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Merge stock data with sector information.
        
        Args:
            stock_df: Stock data with 'ticker' column
            sector_map_df: Sector mapping data
            
        Returns:
            Merged DataFrame with sector_group column
        """
        return pd.merge(
            stock_df,
            sector_map_df[['ticker', 'sector_group']],
            on='ticker',
            how='left'
        )