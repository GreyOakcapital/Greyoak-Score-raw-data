"""
GreyOak Predictor API Routes
FastAPI endpoints for predictor inference
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from pathlib import Path
import pandas as pd
import sys

sys.path.insert(0, '/app/backend')
from predictor.infer import load_model, run_inference

# Create router
router = APIRouter(prefix="/predictor", tags=["predictor"])

# Load model and predictions cache
MODEL_PATH = Path("/app/backend/predictor_output")
PREDICTIONS_FILE = MODEL_PATH / "predictor_predictions.parquet"

# Cache
predictions_cache = None
model_cache = None


def load_predictions_cache():
    """Load predictions from parquet file"""
    global predictions_cache
    if predictions_cache is None and PREDICTIONS_FILE.exists():
        predictions_cache = pd.read_parquet(PREDICTIONS_FILE)
    return predictions_cache


def load_model_cache():
    """Load trained model"""
    global model_cache
    if model_cache is None:
        model_files = list(MODEL_PATH.glob("all_d20_*.pkl"))
        if model_files:
            latest_model = sorted(model_files)[-1]
            model_cache = load_model(latest_model)
    return model_cache


# Response model
class PredictorResponse(BaseModel):
    ticker: str
    p_hat: float
    expected_edge_pct: float
    risk_adjusted_edge: float
    predictor_score: int
    timing_band: str
    flags: List[str]
    as_of: str
    mode: str = "TRADER"


@router.get("/{ticker}", response_model=PredictorResponse)
async def get_predictor_signal(
    ticker: str,
    mode: str = Query("TRADER", description="Mode: TRADER (20d) or INVESTOR (63/126d)")
):
    """
    Get predictor signal for a stock
    
    Args:
        ticker: Stock symbol (e.g., RELIANCE, TCS)
        mode: TRADER or INVESTOR (MVP only supports TRADER)
    
    Returns:
        PredictorResponse with timing signal and score
    """
    # Load predictions
    predictions = load_predictions_cache()
    
    if predictions is None:
        raise HTTPException(
            status_code=503,
            detail="Predictor not initialized. Run training first."
        )
    
    # Find ticker (case-insensitive)
    ticker_upper = ticker.upper()
    stock_data = predictions[predictions['symbol'].str.upper() == ticker_upper]
    
    if len(stock_data) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Ticker {ticker} not found in predictions. Available tickers: {len(predictions)} stocks."
        )
    
    # Get most recent prediction
    stock_data = stock_data.sort_values('date', ascending=False).iloc[0]
    
    # Parse flags
    flags = stock_data['flags'].split(',') if stock_data['flags'] else []
    
    # Build response
    response = PredictorResponse(
        ticker=stock_data['symbol'],
        p_hat=round(stock_data['p_pos'], 4),
        expected_edge_pct=round(stock_data['E'] * 100, 2),
        risk_adjusted_edge=round(stock_data['RA'], 4),
        predictor_score=int(stock_data['predictor_score']),
        timing_band=stock_data['timing_band'],
        flags=flags,
        as_of=stock_data['date'].isoformat() if hasattr(stock_data['date'], 'isoformat') else str(stock_data['date']),
        mode=mode
    )
    
    return response


@router.get("/", summary="List all predictions")
async def list_predictions(
    timing_band: Optional[str] = Query(None, description="Filter by timing band"),
    min_score: Optional[int] = Query(None, description="Minimum predictor score"),
    limit: int = Query(100, description="Max results to return")
):
    """
    List all predictions with optional filters
    
    Args:
        timing_band: Filter by TimingSB, TimingBuy, TimingHold, TimingAvoid
        min_score: Minimum predictor score
        limit: Maximum number of results
    
    Returns:
        List of predictions
    """
    predictions = load_predictions_cache()
    
    if predictions is None:
        raise HTTPException(
            status_code=503,
            detail="Predictor not initialized. Run training first."
        )
    
    # Apply filters
    filtered = predictions.copy()
    
    if timing_band:
        filtered = filtered[filtered['timing_band'] == timing_band]
    
    if min_score is not None:
        filtered = filtered[filtered['predictor_score'] >= min_score]
    
    # Sort by score descending
    filtered = filtered.sort_values('predictor_score', ascending=False).head(limit)
    
    # Convert to dict
    results = []
    for _, row in filtered.iterrows():
        results.append({
            'ticker': row['symbol'],
            'predictor_score': int(row['predictor_score']),
            'timing_band': row['timing_band'],
            'p_pos': round(row['p_pos'], 4),
            'expected_edge_pct': round(row['E'] * 100, 2),
            'risk_adjusted_edge': round(row['RA'], 4),
            'as_of': row['date'].isoformat() if hasattr(row['date'], 'isoformat') else str(row['date'])
        })
    
    return {
        'count': len(results),
        'results': results
    }


@router.get("/stats/summary", summary="Get predictor statistics")
async def get_predictor_stats():
    """
    Get summary statistics of predictor predictions
    
    Returns:
        Statistics including band distribution, score distribution
    """
    predictions = load_predictions_cache()
    
    if predictions is None:
        raise HTTPException(
            status_code=503,
            detail="Predictor not initialized. Run training first."
        )
    
    # Calculate stats
    band_counts = predictions['timing_band'].value_counts().to_dict()
    
    return {
        'total_stocks': len(predictions),
        'timing_bands': band_counts,
        'score_stats': {
            'mean': round(predictions['predictor_score'].mean(), 1),
            'median': int(predictions['predictor_score'].median()),
            'min': int(predictions['predictor_score'].min()),
            'max': int(predictions['predictor_score'].max()),
            'std': round(predictions['predictor_score'].std(), 1)
        },
        'edge_stats': {
            'mean_expected_edge_pct': round(predictions['E'].mean() * 100, 2),
            'mean_risk_adjusted_edge': round(predictions['RA'].mean(), 4)
        },
        'as_of': predictions['date'].max().isoformat() if hasattr(predictions['date'].max(), 'isoformat') else str(predictions['date'].max())
    }


# Health check
@router.get("/health", summary="Predictor health check")
async def health_check():
    """Check if predictor is ready"""
    predictions = load_predictions_cache()
    model = load_model_cache()
    
    return {
        'status': 'healthy' if predictions is not None and model is not None else 'not_initialized',
        'model_loaded': model is not None,
        'predictions_loaded': predictions is not None,
        'predictions_count': len(predictions) if predictions is not None else 0
    }
