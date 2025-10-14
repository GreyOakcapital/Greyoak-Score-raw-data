"""
GreyOak Rule-Based Predictor API Routes
FastAPI endpoints for rule-based signals combining GreyOak Score + Technical Triggers
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, '/app/backend')
from predictor.rule_based import RuleBasedPredictor
from greyoak_score.utils.logger import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/rule-based", tags=["rule-based-predictor"])

# Initialize predictor (singleton)
predictor_instance = None


def get_predictor():
    """Get or create predictor instance"""
    global predictor_instance
    if predictor_instance is None:
        predictor_instance = RuleBasedPredictor()
    return predictor_instance


# Response models
class TechnicalsData(BaseModel):
    current_price: float
    rsi_14: float
    dma20: float
    high_20d: float
    price_vs_dma20_pct: float
    price_vs_high20d_pct: float


class ScoreDetails(BaseModel):
    ticker: str
    score: float
    band: str
    pillars: Dict[str, float]
    risk_penalty: float
    confidence: float


class RuleBasedSignalResponse(BaseModel):
    ticker: str
    signal: str
    greyoak_score: float
    confidence: str
    reasoning: List[str]
    technicals: TechnicalsData
    score_details: ScoreDetails
    timestamp: str


class BatchSignalRequest(BaseModel):
    tickers: List[str]
    mode: str = "trader"


class BatchSignalResponse(BaseModel):
    results: List[Dict]
    summary: Dict


@router.get("/{ticker}", response_model=RuleBasedSignalResponse)
async def get_rule_based_signal(
    ticker: str,
    mode: str = Query("trader", description="Mode: trader or investor")
):
    """
    Get rule-based signal for a stock
    
    **Rules (Priority Order):**
    1. Score ≥ 70 AND price > 20-day high → **Strong Buy**
    2. Score ≥ 60 AND RSI ≤ 35 AND price > DMA20 → **Buy**
    3. Score ≥ 60 AND RSI ≥ 65 → **Hold**
    4. Score < 50 → **Avoid**
    
    **Process:**
    - Fetches real-time price data from NSE (via nsepython)
    - Calculates GreyOak Score (0-100)
    - Computes technical indicators (RSI, DMA20, 20-day high)
    - Applies rule-based logic
    - Returns actionable signal with reasoning
    
    Args:
        ticker: Stock symbol (e.g., RELIANCE, TCS, HDFCBANK)
        mode: trader or investor (default: trader)
    
    Returns:
        RuleBasedSignalResponse with signal, score, technicals, and reasoning
    """
    try:
        logger.info(f"API request for rule-based signal: {ticker} ({mode})")
        
        # Validate mode
        if mode.lower() not in ['trader', 'investor']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode: {mode}. Must be 'trader' or 'investor'"
            )
        
        # Get predictor
        predictor = get_predictor()
        
        # Get signal
        result = predictor.get_signal(ticker, mode=mode.lower())
        
        # Check for errors
        if result.get('signal') == 'Error':
            raise HTTPException(
                status_code=404 if 'unavailable' in result.get('error', '').lower() else 500,
                detail=result.get('error', 'Unknown error')
            )
        
        # Build response
        response = RuleBasedSignalResponse(
            ticker=result['ticker'],
            signal=result['signal'],
            greyoak_score=result['greyoak_score'],
            confidence=result['confidence'],
            reasoning=result['reasoning'],
            technicals=TechnicalsData(**result['technicals']),
            score_details=ScoreDetails(**result['score_details']),
            timestamp=result['timestamp']
        )
        
        logger.info(f"Signal generated for {ticker}: {result['signal']}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request for {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/batch", response_model=BatchSignalResponse)
async def get_batch_signals(request: BatchSignalRequest):
    """
    Get rule-based signals for multiple stocks
    
    **Use Cases:**
    - Portfolio screening
    - Bulk stock analysis
    - Watchlist monitoring
    
    Args:
        request: BatchSignalRequest with list of tickers and mode
    
    Returns:
        BatchSignalResponse with results for each ticker and summary stats
    """
    try:
        logger.info(f"Batch request for {len(request.tickers)} tickers")
        
        # Validate
        if not request.tickers:
            raise HTTPException(
                status_code=400,
                detail="Tickers list cannot be empty"
            )
        
        if len(request.tickers) > 50:
            raise HTTPException(
                status_code=400,
                detail="Maximum 50 tickers per batch request"
            )
        
        # Get predictor
        predictor = get_predictor()
        
        # Process each ticker
        results = []
        signal_counts = {'Strong Buy': 0, 'Buy': 0, 'Hold': 0, 'Avoid': 0, 'Error': 0}
        
        for ticker in request.tickers:
            try:
                result = predictor.get_signal(ticker, mode=request.mode.lower())
                results.append(result)
                
                signal = result.get('signal', 'Error')
                signal_counts[signal] = signal_counts.get(signal, 0) + 1
                
            except Exception as e:
                logger.warning(f"Failed to process {ticker}: {e}")
                results.append({
                    'ticker': ticker,
                    'signal': 'Error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                signal_counts['Error'] += 1
        
        # Build summary
        summary = {
            'total_tickers': len(request.tickers),
            'successful': len(request.tickers) - signal_counts['Error'],
            'failed': signal_counts['Error'],
            'signal_distribution': {k: v for k, v in signal_counts.items() if v > 0},
            'mode': request.mode
        }
        
        response = BatchSignalResponse(
            results=results,
            summary=summary
        )
        
        logger.info(f"Batch processing complete: {summary['successful']}/{summary['total_tickers']} successful")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing batch request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/", summary="Rule-Based Predictor Overview")
async def get_overview():
    """
    Get overview of the rule-based predictor
    
    Returns:
        Overview of rules, features, and usage
    """
    return {
        'name': 'GreyOak Rule-Based Predictor',
        'version': '1.0.0',
        'description': 'Combines GreyOak Score Engine with technical triggers for actionable signals',
        'rules': [
            {
                'priority': 1,
                'condition': 'Score ≥ 70 AND price > 20-day high',
                'signal': 'Strong Buy',
                'rationale': 'High quality stock with price breakout'
            },
            {
                'priority': 2,
                'condition': 'Score ≥ 60 AND RSI ≤ 35 AND price > DMA20',
                'signal': 'Buy',
                'rationale': 'Good quality stock, oversold, above support'
            },
            {
                'priority': 3,
                'condition': 'Score ≥ 60 AND RSI ≥ 65',
                'signal': 'Hold',
                'rationale': 'Good quality but overbought - wait for pullback'
            },
            {
                'priority': 4,
                'condition': 'Score < 50',
                'signal': 'Avoid',
                'rationale': 'Low quality stock'
            },
            {
                'priority': 5,
                'condition': 'Default',
                'signal': 'Hold',
                'rationale': 'Safe default when no strong triggers'
            }
        ],
        'features': [
            'Real-time NSE data (via nsepython)',
            'GreyOak Score (0-100) with 6 pillars',
            'Technical indicators (RSI-14, DMA20, 20-day high)',
            'Rule-based logic with priority ordering',
            'Confidence levels (high/medium)',
            'Detailed reasoning for each signal'
        ],
        'supported_modes': ['trader', 'investor'],
        'data_source': 'NSE India (via nsepython)',
        'endpoints': {
            'single_signal': 'GET /api/rule-based/{ticker}',
            'batch_signals': 'POST /api/rule-based/batch',
            'overview': 'GET /api/rule-based/'
        }
    }


@router.get("/health", summary="Health Check")
async def health_check():
    """Check if rule-based predictor is ready"""
    try:
        predictor = get_predictor()
        
        # Quick test with a known ticker
        test_result = predictor.get_signal('RELIANCE', mode='trader')
        
        if test_result.get('signal') != 'Error':
            status = 'healthy'
        else:
            status = 'degraded'
        
        return {
            'status': status,
            'predictor_loaded': predictor is not None,
            'data_source': 'NSE India (nsepython)',
            'test_ticker': 'RELIANCE',
            'test_result': test_result.get('signal', 'Unknown')
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e)
        }
