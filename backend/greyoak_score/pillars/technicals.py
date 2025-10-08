"""Technicals (T) Pillar - 5-component technical analysis."""

from typing import Dict, Any
import pandas as pd
import numpy as np

from greyoak_score.pillars.base import BasePillar
from greyoak_score.utils.logger import get_logger

logger = get_logger(__name__)


class TechnicalsPillar(BasePillar):
    """Technicals Pillar Calculator.
    
    Implements 5-component technical scoring:
    1. Above200: Is close > DMA200? (20% weight)
    2. GoldenCross: Is DMA20 > DMA50? (15% weight) 
    3. RSI: RSI-based momentum (30-70 bands) (20% weight)
    4. Breakout: Recent price vs ATR-adjusted threshold (25% weight)
    5. Volume Surprise: Recent volume vs historical average (20% weight)
    
    All components are binary (0/100) or scaled (0-100) then weighted.
    """
    
    @property
    def pillar_name(self) -> str:
        return "T"
    
    def calculate(
        self,
        prices_df: pd.DataFrame,
        fundamentals_df: pd.DataFrame,
        ownership_df: pd.DataFrame,
        sector_map_df: pd.DataFrame,
        mode: str = "trader",
        **kwargs
    ) -> pd.DataFrame:
        """Calculate Technicals pillar scores.
        
        Args:
            prices_df: Price and technical indicator data
            fundamentals_df: Not used for technicals
            ownership_df: Not used for technicals
            sector_map_df: Sector mapping (not used for technicals)
            mode: Trading mode (not used for technicals scoring logic)
            
        Returns:
            DataFrame with T_score and T_details columns
        """
        logger.info("📊 Calculating Technicals (T) Pillar...")
        
        # Validate inputs
        self.validate_inputs(prices_df, fundamentals_df, ownership_df, sector_map_df)
        self._validate_technicals_data(prices_df)
        
        # Get configuration
        config = self.config.get_technicals_config()
        weights = config["weights"]
        
        logger.info(f"  📈 Processing {len(prices_df)} price records")
        
        # Get latest price data per ticker
        latest_prices = self.get_latest_data_by_ticker(prices_df)
        
        logger.info(f"  📊 Analyzing {len(latest_prices)} stocks for technical signals")
        
        # Calculate each technical component
        results = []
        
        for _, row in latest_prices.iterrows():
            ticker = row['ticker']
            
            # Calculate individual components
            above_200 = self._calculate_above_200(row)
            golden_cross = self._calculate_golden_cross(row)
            rsi_score = self._calculate_rsi_score(row, config)
            breakout_score = self._calculate_breakout_score(row, config)
            volume_score = self._calculate_volume_score(row, prices_df[prices_df['ticker'] == ticker])
            
            # Calculate weighted T score
            components = {
                "above_200": {"score": above_200, "weight": weights["above_200"]},
                "golden_cross": {"score": golden_cross, "weight": weights["golden_cross"]},
                "rsi": {"score": rsi_score, "weight": weights["rsi"]},
                "breakout": {"score": breakout_score, "weight": weights["breakout"]},
                "volume": {"score": volume_score, "weight": weights["volume"]}
            }
            
            # Weighted average
            total_score = sum(comp["score"] * comp["weight"] for comp in components.values())
            total_weight = sum(comp["weight"] for comp in components.values())
            
            final_score = total_score / total_weight if total_weight > 0 else 0.0
            
            results.append({
                'ticker': ticker,
                'T_score': final_score,
                'T_details': {
                    "components": components,
                    "final_score": final_score,
                    "config_used": {
                        "rsi_bands": config["rsi_bands"],
                        "breakout": config["breakout"]
                    }
                }
            })
        
        result_df = pd.DataFrame(results)
        
        # Log summary statistics
        scores = result_df['T_score'].values
        logger.info(f"✅ Technicals pillar complete: mean={np.mean(scores):.1f}, "
                   f"min={np.min(scores):.1f}, max={np.max(scores):.1f}")
        
        return result_df[['ticker', 'T_score', 'T_details']]
    
    def _validate_technicals_data(self, prices_df: pd.DataFrame) -> None:
        """Validate price data has required technical indicators."""
        required_cols = [
            'ticker', 'close', 'volume',
            'dma20', 'dma50', 'dma200', 'rsi14', 'atr14'
        ]
        missing_cols = [col for col in required_cols if col not in prices_df.columns]
        if missing_cols:
            raise ValueError(f"Missing required technical columns: {missing_cols}")
    
    def _calculate_above_200(self, row: pd.Series) -> float:
        """Calculate Above200 component.
        
        Binary: 100 if close > DMA200, else 0
        """
        if pd.isna(row.get('dma200')) or pd.isna(row.get('close')):
            return 0.0
        
        return 100.0 if row['close'] > row['dma200'] else 0.0
    
    def _calculate_golden_cross(self, row: pd.Series) -> float:
        """Calculate GoldenCross component.
        
        Binary: 100 if DMA20 > DMA50, else 0
        """
        if pd.isna(row.get('dma20')) or pd.isna(row.get('dma50')):
            return 0.0
        
        return 100.0 if row['dma20'] > row['dma50'] else 0.0
    
    def _calculate_rsi_score(self, row: pd.Series, config: Dict) -> float:
        """Calculate RSI-based momentum score.
        
        Scale RSI to 0-100 using overbought/oversold bands:
        - RSI ≤ oversold (30): 0 points
        - RSI ≥ overbought (70): 100 points  
        - Linear interpolation between
        """
        rsi = row.get('rsi14')
        if pd.isna(rsi):
            return 50.0  # Neutral if missing
        
        oversold = config["rsi_bands"]["oversold"]  # 30
        overbought = config["rsi_bands"]["overbought"]  # 70
        
        if rsi <= oversold:
            return 0.0
        elif rsi >= overbought:
            return 100.0
        else:
            # Linear interpolation between oversold and overbought
            return ((rsi - oversold) / (overbought - oversold)) * 100.0
    
    def _calculate_breakout_score(self, row: pd.Series, config: Dict) -> float:
        """Calculate breakout vs ATR-adjusted threshold.
        
        Logic: Compare recent price gap vs (0.75 * ATR) or 1% of close
        - gap = max(0, close - max(hi20, dma20))
        - threshold = max(0.75 * ATR, 0.01 * close)
        - score = min(100, (gap / threshold) * 100)
        """
        close = row.get('close')
        hi20 = row.get('hi20')
        dma20 = row.get('dma20')
        atr14 = row.get('atr14')
        
        # Check for missing data
        if any(pd.isna(val) for val in [close, hi20, dma20, atr14]):
            return 0.0
        
        # Calculate price gap (breakout above resistance)
        resistance = max(hi20, dma20)
        gap = max(0, close - resistance)
        
        # Calculate ATR-based threshold
        atr_multiplier = config["breakout"]["atr_multiplier"]  # 0.75
        close_pct = config["breakout"]["close_pct"]  # 0.01
        
        atr_threshold = atr_multiplier * atr14
        pct_threshold = close_pct * close
        threshold = max(atr_threshold, pct_threshold)
        
        if threshold <= 0:
            return 0.0
        
        # Score as percentage of threshold, capped at 100
        score = min(100.0, (gap / threshold) * 100.0)
        return score
    
    def _calculate_volume_score(self, row: pd.Series, ticker_history: pd.DataFrame) -> float:
        """Calculate volume surprise score.
        
        Logic: Current volume vs 20-day average volume
        - If vol_ratio ≥ 2.0: 100 points
        - If vol_ratio ≤ 0.5: 0 points
        - Linear interpolation between 0.5 and 2.0
        """
        current_volume = row.get('volume')
        if pd.isna(current_volume) or current_volume <= 0:
            return 50.0  # Neutral if missing/invalid
        
        # Calculate 20-day average volume (excluding current day)
        if len(ticker_history) < 2:
            return 50.0  # Not enough history
        
        # Get last 20 days excluding current (for fair comparison)
        recent_history = ticker_history.sort_values('trading_date').iloc[:-1].tail(20)
        
        if len(recent_history) == 0:
            return 50.0
        
        avg_volume = recent_history['volume'].mean()
        if pd.isna(avg_volume) or avg_volume <= 0:
            return 50.0
        
        # Calculate volume ratio
        vol_ratio = current_volume / avg_volume
        
        # Score based on ratio
        if vol_ratio >= 2.0:
            return 100.0
        elif vol_ratio <= 0.5:
            return 0.0
        else:
            # Linear interpolation between 0.5 and 2.0
            # 0.5 -> 0, 2.0 -> 100
            return ((vol_ratio - 0.5) / (2.0 - 0.5)) * 100.0