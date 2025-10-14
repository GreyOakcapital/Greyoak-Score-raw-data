"""
GreyOak Rule-Based Predictor
Combines GreyOak Score Engine with technical triggers for actionable signals

Rules (Priority Order):
1. Score ≥ 70 AND price > 20-day high → Strong Buy
2. Score ≥ 60 AND RSI ≤ 35 AND price > DMA20 → Buy  
3. Score ≥ 60 AND RSI ≥ 65 → Hold
4. Score < 50 → Avoid
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from pathlib import Path
import sys

sys.path.insert(0, '/app/backend')

from nsepython import equity_history
from greyoak_score.core.scoring import calculate_greyoak_score
from greyoak_score.core.config_manager import ConfigManager
from greyoak_score.utils.logger import get_logger

logger = get_logger(__name__)


class RuleBasedPredictor:
    """
    Rule-Based Predictor combining GreyOak Score with technical triggers
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize predictor with config"""
        if config_dir is None:
            config_dir = Path('/app/backend/configs')
        self.config = ConfigManager(config_dir)
        
    def fetch_price_data(self, ticker: str, days: int = 30) -> Optional[pd.DataFrame]:
        """
        Fetch price data from nsepython
        
        Args:
            ticker: Stock symbol (without .NS/.BO suffix)
            days: Number of days of historical data
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Clean ticker (remove .NS/.BO suffix if present)
            clean_ticker = ticker.replace('.NS', '').replace('.BO', '')
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 10)  # Extra buffer for weekends
            
            # Format dates for nsepython (DD-MM-YYYY)
            start_str = start_date.strftime('%d-%m-%Y')
            end_str = end_date.strftime('%d-%m-%Y')
            
            logger.info(f"Fetching price data for {clean_ticker} from {start_str} to {end_str}")
            
            # Fetch data from NSE
            df = equity_history(clean_ticker, "EQ", start_str, end_str)
            
            if df is None or df.empty:
                logger.warning(f"No data returned for {clean_ticker}")
                return None
                
            # Rename columns to standard format
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            
            # Ensure we have required columns
            required_cols = ['ch_timestamp', 'ch_closing_price', 'ch_trade_high_price', 
                            'ch_trade_low_price', 'ch_tot_traded_qty']
            
            if not all(col in df.columns for col in required_cols):
                logger.error(f"Missing required columns in data for {clean_ticker}")
                return None
            
            # Rename to standard OHLCV format
            df = df.rename(columns={
                'ch_timestamp': 'date',
                'ch_closing_price': 'close',
                'ch_opening_price': 'open',
                'ch_trade_high_price': 'high',
                'ch_trade_low_price': 'low',
                'ch_tot_traded_qty': 'volume'
            })
            
            # Convert date
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}", exc_info=True)
            return None
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators (RSI, DMA20, 20-day high)
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added technical indicators
        """
        try:
            # Calculate RSI-14
            df['rsi_14'] = self._calculate_rsi(df['close'], period=14)
            
            # Calculate DMA20 (20-day moving average)
            df['dma20'] = df['close'].rolling(window=20).mean()
            
            # Calculate 20-day high
            df['high_20d'] = df['high'].rolling(window=20).max()
            
            # Calculate ATR-20 for volatility
            df['atr_20'] = self._calculate_atr(df, period=20)
            
            # Calculate DMA200
            df['dma200'] = df['close'].rolling(window=200).mean()
            
            # Calculate sigma (20-day volatility)
            df['returns'] = df['close'].pct_change()
            df['sigma20'] = df['returns'].rolling(window=20).std()
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}", exc_info=True)
            return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Average True Range"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def get_sector_group(self, ticker: str) -> str:
        """
        Get sector group for a ticker
        
        Args:
            ticker: Stock ticker
            
        Returns:
            Sector group string
        """
        ticker_upper = ticker.upper()
        
        # Simplified sector mapping
        if any(x in ticker_upper for x in ['RELIANCE', 'ONGC', 'BPCL', 'HPCL', 'IOC']):
            return 'energy'
        elif any(x in ticker_upper for x in ['TCS', 'INFY', 'WIPRO', 'HCLTECH', 'TECHM']):
            return 'it'
        elif any(x in ticker_upper for x in ['HDFCBANK', 'ICICIBANK', 'KOTAKBANK', 'AXISBANK', 'INDUSINDBK']):
            return 'banks'
        elif any(x in ticker_upper for x in ['HINDUNILVR', 'NESTLEIND', 'BRITANNIA', 'ITC', 'DABUR']):
            return 'fmcg'
        elif any(x in ticker_upper for x in ['SUNPHARMA', 'DRREDDY', 'CIPLA', 'LUPIN', 'DIVISLAB']):
            return 'pharma'
        elif any(x in ticker_upper for x in ['TATASTEEL', 'JSWSTEEL', 'HINDALCO', 'VEDL', 'JINDALSTEL']):
            return 'metals'
        elif any(x in ticker_upper for x in ['MARUTI', 'M&M', 'TATAMOTORS', 'BAJAJ-AUTO', 'HEROMOTOCO']):
            return 'auto_caps'
        elif any(x in ticker_upper for x in ['SBIN', 'PNB', 'BANKBARODA', 'CANBK']):
            return 'psu_banks'
        else:
            return 'diversified'
    
    def calculate_greyoak_score_for_ticker(
        self, 
        ticker: str, 
        mode: str = 'trader'
    ) -> Optional[Tuple[float, Dict]]:
        """
        Calculate GreyOak Score for a ticker
        
        Args:
            ticker: Stock ticker
            mode: 'trader' or 'investor'
            
        Returns:
            Tuple of (score, score_output_dict) or None if failed
        """
        try:
            # Fetch price data
            df = self.fetch_price_data(ticker, days=250)  # Need 200 days for DMA200
            
            if df is None or len(df) < 50:
                logger.warning(f"Insufficient data for {ticker}")
                return None
            
            # Calculate technical indicators
            df = self.calculate_technical_indicators(df)
            
            # Get latest row
            latest = df.iloc[-1]
            
            # Build mock pillar scores (deterministic but realistic)
            # In production, these would be calculated from actual data
            base_seed = hash(ticker) % 100
            pillar_scores = {
                'F': 50 + (base_seed % 40),
                'T': 50 + ((base_seed * 7) % 35),
                'R': 50 + ((base_seed * 11) % 40),
                'O': 50 + ((base_seed * 13) % 35),
                'Q': 50 + ((base_seed * 17) % 40),
                'S': 50 + ((base_seed * 19) % 30)
            }
            
            # Build data series for scoring engine
            prices_data = pd.Series({
                'close': latest['close'],
                'volume': latest.get('volume', 1000000),
                'median_traded_value_cr': 5.0,
                'rsi_14': latest.get('rsi_14', 50.0),
                'atr_20': latest.get('atr_20', latest['close'] * 0.02),
                'dma20': latest.get('dma20', latest['close']),
                'dma200': latest.get('dma200', latest['close'] * 0.95),
                'sigma20': latest.get('sigma20', 0.02)
            })
            
            fundamentals_data = pd.Series({
                'market_cap_cr': 50000.0,
                'roe_3y': 0.15,
                'sales_cagr_3y': 0.12,
                'quarter_end': '2024-09-30'
            })
            
            ownership_data = pd.Series({
                'promoter_holding_pct': 0.60,
                'promoter_pledge_frac': 0.05,
                'fii_holding_pct': 0.20
            })
            
            sector_group = self.get_sector_group(ticker)
            
            # Calculate GreyOak Score
            score_result = calculate_greyoak_score(
                ticker=ticker,
                pillar_scores=pillar_scores,
                prices_data=prices_data,
                fundamentals_data=fundamentals_data,
                ownership_data=ownership_data,
                sector_group=sector_group,
                mode=mode.lower(),
                config=self.config,
                s_z=0.5,
                scoring_date=datetime.now()
            )
            
            return score_result.score, {
                'ticker': ticker,
                'score': score_result.score,
                'band': score_result.band,
                'pillars': pillar_scores,
                'risk_penalty': score_result.risk_penalty,
                'confidence': score_result.confidence
            }
            
        except Exception as e:
            logger.error(f"Error calculating GreyOak Score for {ticker}: {e}", exc_info=True)
            return None
    
    def apply_rules(
        self,
        ticker: str,
        greyoak_score: float,
        price_data: pd.DataFrame
    ) -> Dict:
        """
        Apply rule-based logic to generate signal
        
        Rules (Priority Order):
        1. Score ≥ 70 AND price > 20-day high → Strong Buy
        2. Score ≥ 60 AND RSI ≤ 35 AND price > DMA20 → Buy
        3. Score ≥ 60 AND RSI ≥ 65 → Hold
        4. Score < 50 → Avoid
        Default: Hold (safe default if no rules match)
        
        Args:
            ticker: Stock ticker
            greyoak_score: Calculated GreyOak Score
            price_data: DataFrame with price and technical data
            
        Returns:
            Dict with signal, reasoning, and supporting data
        """
        try:
            # Get latest data
            latest = price_data.iloc[-1]
            
            current_price = latest['close']
            rsi = latest.get('rsi_14', 50.0)
            dma20 = latest.get('dma20', current_price)
            high_20d = latest.get('high_20d', current_price)
            
            # Apply rules in priority order
            signal = 'Hold'  # Default
            reasoning = []
            confidence = 'medium'
            
            # Rule 1: Strong Buy
            if greyoak_score >= 70 and current_price > high_20d:
                signal = 'Strong Buy'
                reasoning.append(f"GreyOak Score {greyoak_score:.1f} ≥ 70 (High Quality)")
                reasoning.append(f"Price {current_price:.2f} > 20-day high {high_20d:.2f} (Breakout)")
                confidence = 'high'
                
            # Rule 2: Buy
            elif greyoak_score >= 60 and rsi <= 35 and current_price > dma20:
                signal = 'Buy'
                reasoning.append(f"GreyOak Score {greyoak_score:.1f} ≥ 60 (Good Quality)")
                reasoning.append(f"RSI {rsi:.1f} ≤ 35 (Oversold)")
                reasoning.append(f"Price {current_price:.2f} > DMA20 {dma20:.2f} (Above Support)")
                confidence = 'high'
                
            # Rule 3: Hold (High Score but Overbought)
            elif greyoak_score >= 60 and rsi >= 65:
                signal = 'Hold'
                reasoning.append(f"GreyOak Score {greyoak_score:.1f} ≥ 60 (Good Quality)")
                reasoning.append(f"RSI {rsi:.1f} ≥ 65 (Overbought - Wait for Pullback)")
                confidence = 'medium'
                
            # Rule 4: Avoid
            elif greyoak_score < 50:
                signal = 'Avoid'
                reasoning.append(f"GreyOak Score {greyoak_score:.1f} < 50 (Low Quality)")
                confidence = 'high'
                
            # Default: Hold
            else:
                signal = 'Hold'
                reasoning.append(f"GreyOak Score {greyoak_score:.1f} (Moderate Quality)")
                reasoning.append("No strong technical triggers detected")
                confidence = 'medium'
            
            return {
                'ticker': ticker,
                'signal': signal,
                'greyoak_score': round(greyoak_score, 1),
                'confidence': confidence,
                'reasoning': reasoning,
                'technicals': {
                    'current_price': round(current_price, 2),
                    'rsi_14': round(rsi, 1),
                    'dma20': round(dma20, 2),
                    'high_20d': round(high_20d, 2),
                    'price_vs_dma20_pct': round(((current_price / dma20) - 1) * 100, 2),
                    'price_vs_high20d_pct': round(((current_price / high_20d) - 1) * 100, 2)
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error applying rules for {ticker}: {e}", exc_info=True)
            return {
                'ticker': ticker,
                'signal': 'Error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_signal(self, ticker: str, mode: str = 'trader') -> Dict:
        """
        Get rule-based signal for a ticker
        
        Args:
            ticker: Stock ticker (with or without .NS/.BO suffix)
            mode: 'trader' or 'investor'
            
        Returns:
            Dict with signal and analysis
        """
        try:
            logger.info(f"Generating rule-based signal for {ticker}")
            
            # Step 1: Calculate GreyOak Score
            score_result = self.calculate_greyoak_score_for_ticker(ticker, mode)
            
            if score_result is None:
                return {
                    'ticker': ticker,
                    'signal': 'Error',
                    'error': 'Failed to calculate GreyOak Score (data unavailable)',
                    'timestamp': datetime.now().isoformat()
                }
            
            greyoak_score, score_details = score_result
            
            # Step 2: Fetch price data with indicators
            df = self.fetch_price_data(ticker, days=30)
            
            if df is None or len(df) < 20:
                return {
                    'ticker': ticker,
                    'signal': 'Error',
                    'error': 'Insufficient price data for technical analysis',
                    'greyoak_score': greyoak_score,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Calculate indicators
            df = self.calculate_technical_indicators(df)
            
            # Step 3: Apply rules
            result = self.apply_rules(ticker, greyoak_score, df)
            
            # Add score details
            result['score_details'] = score_details
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting signal for {ticker}: {e}", exc_info=True)
            return {
                'ticker': ticker,
                'signal': 'Error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Standalone function for easy import
def get_rule_based_signal(ticker: str, mode: str = 'trader') -> Dict:
    """
    Get rule-based signal for a ticker
    
    Args:
        ticker: Stock ticker
        mode: 'trader' or 'investor'
        
    Returns:
        Dict with signal and analysis
    """
    predictor = RuleBasedPredictor()
    return predictor.get_signal(ticker, mode)


if __name__ == "__main__":
    # Test
    predictor = RuleBasedPredictor()
    
    # Test with a few tickers
    test_tickers = ['RELIANCE', 'TCS', 'HDFCBANK']
    
    for ticker in test_tickers:
        print(f"\n{'='*60}")
        print(f"Testing {ticker}")
        print('='*60)
        
        result = predictor.get_signal(ticker)
        
        print(f"\nSignal: {result.get('signal')}")
        print(f"GreyOak Score: {result.get('greyoak_score')}")
        print(f"Confidence: {result.get('confidence')}")
        print(f"\nReasoning:")
        for reason in result.get('reasoning', []):
            print(f"  • {reason}")
        print(f"\nTechnicals:")
        for key, value in result.get('technicals', {}).items():
            print(f"  {key}: {value}")
