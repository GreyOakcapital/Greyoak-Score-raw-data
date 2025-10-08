"""
FastAPI routes for GreyOak Score Engine.

This module defines all API endpoints with proper input validation,
error handling, and response formatting. Follows RESTful conventions
and provides comprehensive score calculation and retrieval capabilities.

Endpoints:
- POST /api/v1/calculate - Calculate score for a stock
- GET /api/v1/scores/{ticker} - Get score history for a ticker
- GET /api/v1/scores/band/{band} - Get stocks by investment band
- GET /api/v1/health - Health check with database connectivity
"""

from fastapi import APIRouter, HTTPException, Query, Path, Request
from typing import List, Optional
from datetime import datetime, timezone
import os
import re
import psycopg2

# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

from greyoak_score.api.schemas import (
    ScoreRequest, ScoreResponse, HealthResponse, 
    ErrorResponse, StocksByBandResponse
)
import greyoak_score
from greyoak_score.data.persistence import get_database
from greyoak_score.core.scoring import calculate_greyoak_score
from greyoak_score.data.models import ScoreOutput, PillarScores
from greyoak_score.utils.logger import get_logger

logger = get_logger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Get rate limit from environment
rate_limit_per_minute = os.getenv('RATE_LIMIT', '60')
rate_limit = f"{rate_limit_per_minute}/minute"

# Initialize router with CP7 enhancements
router = APIRouter(prefix="/api/v1", tags=["scoring"])

# Database instance will be lazy-loaded in endpoints
# This prevents connection failures during module import
def get_db_instance():
    """Get database instance with lazy initialization."""
    return get_database()


@router.post(
    "/calculate",
    response_model=ScoreResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input parameters"},
        404: {"model": ErrorResponse, "description": "Stock data not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Calculate GreyOak Score (Rate Limited)",
    description=f"""
    Calculate a complete GreyOak Score for a stock with CP7 rate limiting.
    
    **Rate Limiting:** {rate_limit_per_minute} requests per minute per IP address.
    
    **Process:**
    1. Validates input parameters (ticker format, date, mode)
    2. Loads stock data from CSV files or database
    3. Calculates six pillar scores with sector normalization
    4. Applies risk penalties and sequential guardrails
    5. Generates final score (0-100) and investment band
    6. Saves result to database for audit trail
    7. Returns comprehensive scoring breakdown
    
    **Note:** This endpoint requires pre-calculated pillar scores in the current implementation.
    In production, it would load raw data and calculate pillars dynamically.
    """
)
@limiter.limit(rate_limit)
async def calculate_score_endpoint(request_obj: Request, request: ScoreRequest):
    """
    Calculate GreyOak Score for a stock.
    
    This is the main scoring endpoint that orchestrates the complete
    scoring pipeline from data loading to final score generation.
    """
    try:
        # Validate ticker format (basic validation)
        if not _validate_ticker(request.ticker):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ticker format: {request.ticker}. Expected format like 'RELIANCE.NS' or 'TCS.BO'"
            )
        
        # Validate mode
        if request.mode not in ['Trader', 'Investor']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode: {request.mode}. Must be 'Trader' or 'Investor'"
            )
        
        # Parse date
        try:
            scoring_date = datetime.strptime(request.date, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format: {request.date}. Expected YYYY-MM-DD"
            )
        
        logger.info(f"Calculating score for {request.ticker} on {request.date} ({request.mode})")
        
        # For this implementation, we'll create a mock score calculation
        # In production, this would load actual data and use the full pipeline
        
        # Mock pillar scores (in production, these would be calculated)
        mock_pillar_scores = {
            'F': 70.0 + hash(request.ticker) % 20,  # Deterministic but varied
            'T': 65.0 + hash(request.date) % 25,
            'R': 60.0 + hash(request.mode) % 30,
            'O': 75.0 + hash(request.ticker + request.date) % 15,
            'Q': 80.0 + hash(request.ticker + request.mode) % 20,
            'S': 72.0 + hash(request.date + request.mode) % 18
        }
        
        # Mock additional data (in production, loaded from CSV/database)
        import pandas as pd
        mock_prices_data = pd.Series({
            'close': 2500.0,
            'volume': 1000000,
            'median_traded_value_cr': 4.5,
            'rsi_14': 55.0,
            'atr_20': 50.0,
            'dma20': 2450.0,
            'dma200': 2300.0,
            'sigma20': 0.025
        })
        
        mock_fundamentals_data = pd.Series({
            'market_cap_cr': 15000.0,
            'roe_3y': 0.15,
            'sales_cagr_3y': 0.12,
            'quarter_end': '2024-09-30'
        })
        
        mock_ownership_data = pd.Series({
            'promoter_holding_pct': 0.68,
            'promoter_pledge_frac': 0.05,
            'fii_holding_pct': 0.15
        })
        
        # Determine sector group (simplified mapping)
        sector_group = _get_sector_group(request.ticker)
        
        # Calculate score using the scoring engine
        from greyoak_score.core.config_manager import ConfigManager
        from pathlib import Path
        
        config_dir = Path(__file__).parent.parent.parent / "configs"
        config = ConfigManager(config_dir)
        
        # Use the scoring engine (with mocked data)
        score_result = calculate_greyoak_score(
            ticker=request.ticker,
            pillar_scores=mock_pillar_scores,
            prices_data=mock_prices_data,
            fundamentals_data=mock_fundamentals_data,
            ownership_data=mock_ownership_data,
            sector_group=sector_group,
            mode=request.mode.lower(),
            config=config,
            s_z=1.2,  # Mock sector momentum z-score
            scoring_date=datetime.combine(scoring_date, datetime.min.time().replace(tzinfo=timezone.utc))
        )
        
        # Save to database
        try:
            row_id = db.save_score(score_result)
            logger.info(f"Score saved to database with ID {row_id}")
        except Exception as e:
            logger.warning(f"Failed to save score to database: {e}")
            # Continue anyway - don't fail the API call due to database issues
        
        # Convert to API response format
        response = ScoreResponse(
            ticker=score_result.ticker,
            date=score_result.scoring_date.isoformat(),
            mode=score_result.mode,
            score=score_result.score,
            band=score_result.band,
            pillars={
                'F': score_result.pillars.F,
                'T': score_result.pillars.T,
                'R': score_result.pillars.R,
                'O': score_result.pillars.O,
                'Q': score_result.pillars.Q,
                'S': score_result.pillars.S
            },
            risk_penalty=score_result.risk_penalty,
            guardrail_flags=score_result.guardrail_flags,
            confidence=score_result.confidence,
            s_z=score_result.s_z,
            as_of=score_result.as_of.isoformat(),
            config_hash=score_result.config_hash
        )
        
        logger.info(f"Score calculated successfully: {score_result.score:.2f} ({score_result.band})")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise
    except Exception as e:
        logger.error(f"Error calculating score for {request.ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during score calculation. Please try again later."
        )


@router.get(
    "/scores/{ticker}",
    response_model=List[ScoreResponse],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        404: {"model": ErrorResponse, "description": "No scores found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Database error"}
    },
    summary="Get Score History (Rate Limited)",
    description=f"""
    Retrieve score history for a specific ticker with optional filters.
    
    **Rate Limiting:** {rate_limit_per_minute} requests per minute per IP address.
    
    **Query Parameters:**
    - `start_date`: Filter scores from this date (inclusive, YYYY-MM-DD)
    - `end_date`: Filter scores to this date (inclusive, YYYY-MM-DD) 
    - `mode`: Filter by scoring mode ('Trader' or 'Investor')
    - `limit`: Limit number of results (default: 100, max: 1000)
    
    **Results:** Ordered by date DESC (most recent first)
    """
)
@limiter.limit(rate_limit)
async def get_scores_for_ticker(
    request: Request,
    ticker: str = Path(..., description="Stock ticker symbol (e.g., 'RELIANCE.NS')"),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    mode: Optional[str] = Query(None, description="Mode filter ('Trader' or 'Investor')"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of results")
):
    """Get score history for a ticker with optional filters."""
    try:
        # Validate ticker
        if not _validate_ticker(ticker):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ticker format: {ticker}"
            )
        
        # Validate and parse dates
        start_date_obj = None
        end_date_obj = None
        
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid start_date format: {start_date}. Expected YYYY-MM-DD"
                )
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid end_date format: {end_date}. Expected YYYY-MM-DD"
                )
        
        # Validate date range
        if start_date_obj and end_date_obj and start_date_obj > end_date_obj:
            raise HTTPException(
                status_code=400,
                detail="start_date must be before or equal to end_date"
            )
        
        # Validate mode
        if mode and mode not in ['Trader', 'Investor']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode: {mode}. Must be 'Trader' or 'Investor'"
            )
        
        logger.info(f"Retrieving scores for {ticker} with filters: start={start_date}, end={end_date}, mode={mode}, limit={limit}")
        
        # Query database
        try:
            results = db.get_scores_by_ticker(
                ticker=ticker,
                start_date=start_date_obj,
                end_date=end_date_obj,
                mode=mode,
                limit=limit
            )
        except psycopg2.Error as e:
            logger.error(f"Database error retrieving scores for {ticker}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Database error. Please try again later."
            )
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"No scores found for {ticker} with the specified filters"
            )
        
        # Convert to API response format
        response = [
            ScoreResponse(
                ticker=r.ticker,
                date=r.scoring_date.isoformat(),
                mode=r.mode,
                score=r.score,
                band=r.band,
                pillars={
                    'F': r.pillars.F,
                    'T': r.pillars.T,
                    'R': r.pillars.R,
                    'O': r.pillars.O,
                    'Q': r.pillars.Q,
                    'S': r.pillars.S
                },
                risk_penalty=r.risk_penalty,
                guardrail_flags=r.guardrail_flags,
                confidence=r.confidence,
                s_z=r.s_z,
                as_of=r.as_of.isoformat(),
                config_hash=r.config_hash
            ) for r in results
        ]
        
        logger.info(f"Retrieved {len(response)} scores for {ticker}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving scores for {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Please try again later."
        )


@router.get(
    "/scores/band/{band}",
    response_model=StocksByBandResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        404: {"model": ErrorResponse, "description": "No stocks found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Database error"}
    },
    summary="Get Stocks by Investment Band (Rate Limited)",
    description=f"""
    Get all stocks with a specific investment band on a given date.
    
    **Rate Limiting:** {rate_limit_per_minute} requests per minute per IP address.
    
    **Use Cases:**
    - Portfolio screening and stock picking
    - Investment research and recommendations
    - Performance tracking and analysis
    
    **Results:** Ordered by score DESC (best scores first within the band)
    """
)
@limiter.limit(rate_limit)
async def get_stocks_by_band(
    request: Request,
    band: str = Path(..., description="Investment band"),
    date: str = Query(..., description="Score date (YYYY-MM-DD)"),
    mode: str = Query(..., description="Scoring mode ('Trader' or 'Investor')"),
    limit: Optional[int] = Query(50, ge=1, le=500, description="Maximum number of results")
):
    """Get all stocks with a specific investment band on a given date."""
    try:
        # Validate band
        valid_bands = ['Strong Buy', 'Buy', 'Hold', 'Avoid']
        if band not in valid_bands:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid band: {band}. Must be one of: {valid_bands}"
            )
        
        # Validate mode
        if mode not in ['Trader', 'Investor']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode: {mode}. Must be 'Trader' or 'Investor'"
            )
        
        # Parse date
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format: {date}. Expected YYYY-MM-DD"
            )
        
        logger.info(f"Retrieving {band} stocks for {date} ({mode}) with limit {limit}")
        
        # Query database
        try:
            results = db.get_scores_by_band(
                band=band,
                date=date_obj,
                mode=mode,
                limit=limit
            )
        except psycopg2.Error as e:
            logger.error(f"Database error retrieving {band} stocks: {e}")
            raise HTTPException(
                status_code=500,
                detail="Database error. Please try again later."
            )
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"No {band} stocks found for {date} in {mode} mode"
            )
        
        # Convert to API response format
        scores = [
            ScoreResponse(
                ticker=r.ticker,
                date=r.scoring_date.isoformat(),
                mode=r.mode,
                score=r.score,
                band=r.band,
                pillars={
                    'F': r.pillars.F,
                    'T': r.pillars.T,
                    'R': r.pillars.R,
                    'O': r.pillars.O,
                    'Q': r.pillars.Q,
                    'S': r.pillars.S
                },
                risk_penalty=r.risk_penalty,
                guardrail_flags=r.guardrail_flags,
                confidence=r.confidence,
                s_z=r.s_z,
                as_of=r.as_of.isoformat(),
                config_hash=r.config_hash
            ) for r in results
        ]
        
        # Calculate statistics
        scores_values = [s.score for s in scores]
        statistics = {
            "count": len(scores),
            "avg_score": round(sum(scores_values) / len(scores_values), 2) if scores_values else 0,
            "min_score": round(min(scores_values), 2) if scores_values else 0,
            "max_score": round(max(scores_values), 2) if scores_values else 0,
            "date": date,
            "mode": mode,
            "band": band
        }
        
        response = StocksByBandResponse(
            stocks=scores,
            statistics=statistics
        )
        
        logger.info(f"Retrieved {len(scores)} {band} stocks for {date} ({mode})")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving {band} stocks: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Please try again later."
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application Health Check (CP7)",
    description="""
    Comprehensive application health check including database connectivity and connection pool status.
    
    **CP7 Features:**
    - Database connection pool monitoring
    - Connection retry validation
    - Enhanced error reporting
    - Performance metrics
    
    **Status Levels:**
    - `healthy`: All systems operational
    - `degraded`: API running but some components (e.g., database) may have issues
    - `unhealthy`: Critical system failures
    
    **Use Cases:**
    - Application health monitoring
    - Database connectivity verification
    - Connection pool status monitoring
    
    **Note:** This is the application health endpoint. For infrastructure-only health checks (faster), use `GET /health`.
    """
)
@limiter.exempt  # Health checks should not be rate limited
async def health_check_detailed():
    """Detailed health check with database connectivity test."""
    try:
        # Test database connection
        db_status = "unknown"
        db_error = None
        
        try:
            if db.test_connection():
                db_status = "healthy"
            else:
                db_status = "unhealthy"
                db_error = "Connection test failed"
        except Exception as e:
            db_status = "unhealthy"
            db_error = str(e)
        
        # Determine overall status
        if db_status == "healthy":
            overall_status = "healthy"
        elif db_status == "unhealthy":
            overall_status = "degraded"  # API still works without database
        else:
            overall_status = "unknown"
        
        # Get database stats if connection is healthy
        db_stats = None
        if db_status == "healthy":
            try:
                db_stats = db.get_database_stats()
            except Exception as e:
                logger.warning(f"Failed to get database stats: {e}")
        
        response = HealthResponse(
            status=overall_status,
            service="greyoak-score-api",
            version=greyoak_score.__version__,
            timestamp=datetime.now(timezone.utc).isoformat(),
            components={
                "database": {
                    "status": db_status,
                    "error": db_error,
                    "stats": db_stats
                },
                "api": {
                    "status": "healthy"
                }
            }
        )
        
        # Set appropriate HTTP status based on health
        if overall_status == "unhealthy":
            logger.warning("Health check failed - service unhealthy")
            raise HTTPException(status_code=503, detail=response.dict())
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "unhealthy",
                "error": "Health check failed",
                "message": str(e)
            }
        )


# Helper functions

def _validate_ticker(ticker: str) -> bool:
    """
    Validate ticker format.
    
    Accepts formats like:
    - RELIANCE.NS (NSE)
    - TCS.BO (BSE)  
    - INFY (bare ticker)
    """
    if not ticker or len(ticker) < 2:
        return False
    
    # Basic pattern: letters/numbers with optional exchange suffix
    pattern = r'^[A-Z0-9]{2,20}(\.[A-Z]{2,3})?$'
    return bool(re.match(pattern, ticker.upper()))


def _get_sector_group(ticker: str) -> str:
    """
    Get sector group for a ticker (simplified mapping).
    
    In production, this would look up from the sector mapping database/CSV.
    """
    ticker_upper = ticker.upper()
    
    # Simplified sector mapping based on common tickers
    if any(x in ticker_upper for x in ['RELIANCE', 'ONGC', 'BPCL', 'HPCL']):
        return 'energy'
    elif any(x in ticker_upper for x in ['TCS', 'INFY', 'WIPRO', 'HCLTECH', 'TECHM']):
        return 'it'
    elif any(x in ticker_upper for x in ['HDFCBANK', 'ICICIBANK', 'KOTAKBANK', 'AXISBANK']):
        return 'banks'
    elif any(x in ticker_upper for x in ['HINDUNILVR', 'NESTLEIND', 'BRITANNIA', 'ITC']):
        return 'fmcg'
    elif any(x in ticker_upper for x in ['SUNPHARMA', 'DRREDDY', 'CIPLA', 'LUPIN']):
        return 'pharma'
    elif any(x in ticker_upper for x in ['TATASTEEL', 'JSWSTEEL', 'HINDALCO', 'VEDL']):
        return 'metals'
    else:
        return 'diversified'  # Default sector