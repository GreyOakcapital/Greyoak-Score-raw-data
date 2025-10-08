"""
Pydantic schemas for API request/response models.

This module defines all data models used for API input validation
and response serialization. Follows OpenAPI standards and provides
comprehensive documentation for API consumers.

Key Features:
- Input validation with custom validators
- Automatic OpenAPI schema generation  
- Type safety and IDE support
- Clear error messages for validation failures
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
import re


class ScoreRequest(BaseModel):
    """
    Request model for score calculation endpoint.
    
    Used for POST /api/v1/calculate to specify which stock to score.
    """
    ticker: str = Field(
        ...,
        description="Stock ticker symbol (e.g., 'RELIANCE.NS', 'TCS.BO')",
        example="RELIANCE.NS",
        min_length=2,
        max_length=20
    )
    date: str = Field(
        ...,
        description="Scoring date in ISO format (YYYY-MM-DD)",
        example="2024-10-08",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    mode: Literal["Trader", "Investor"] = Field(
        ...,
        description="Scoring mode: Trader (short-term) or Investor (long-term)",
        example="Investor"
    )
    
    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        """Validate ticker format."""
        if not v or len(v.strip()) < 2:
            raise ValueError("Ticker must be at least 2 characters long")
        
        # Basic format validation
        ticker = v.strip().upper()
        pattern = r'^[A-Z0-9]{2,20}(\.[A-Z]{2,3})?$'
        if not re.match(pattern, ticker):
            raise ValueError("Invalid ticker format. Expected format like 'RELIANCE.NS' or 'TCS.BO'")
        
        return ticker
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Validate date format and range."""
        try:
            from datetime import datetime
            date_obj = datetime.strptime(v, '%Y-%m-%d')
            
            # Basic range validation (not too far in past/future)
            min_date = datetime(2020, 1, 1)
            max_date = datetime(2030, 12, 31)
            
            if date_obj < min_date or date_obj > max_date:
                raise ValueError(f"Date must be between {min_date.date()} and {max_date.date()}")
            
            return v
        except ValueError as e:
            if "does not match format" in str(e):
                raise ValueError("Invalid date format. Expected YYYY-MM-DD")
            raise


class ScoreResponse(BaseModel):
    """
    Response model for score-related endpoints.
    
    Contains complete scoring breakdown with all metadata needed
    for analysis and audit trail.
    """
    ticker: str = Field(..., description="Stock ticker symbol")
    date: str = Field(..., description="Scoring date (YYYY-MM-DD)")
    mode: str = Field(..., description="Scoring mode")
    
    # Core results
    score: float = Field(
        ..., 
        description="Final GreyOak Score (0-100)",
        ge=0,
        le=100
    )
    band: str = Field(
        ...,
        description="Investment recommendation band"
    )
    
    # Detailed breakdown
    pillars: Dict[str, float] = Field(
        ...,
        description="Six pillar scores (F, T, R, O, Q, S)",
        example={
            "F": 75.0,
            "T": 68.0,
            "R": 82.0,
            "O": 70.0,
            "Q": 85.0,
            "S": 73.0
        }
    )
    risk_penalty: float = Field(
        ...,
        description="Total risk penalty deducted from score",
        ge=0,
        le=20
    )
    guardrail_flags: List[str] = Field(
        default_factory=list,
        description="List of triggered guardrails",
        example=["LowDataHold", "PledgeCap"]
    )
    
    # Quality metrics
    confidence: float = Field(
        ...,
        description="Data confidence score (0-1)",
        ge=0,
        le=1
    )
    s_z: float = Field(
        ...,
        description="Sector momentum z-score"
    )
    
    # Audit trail
    as_of: str = Field(
        ...,
        description="Timestamp when score was calculated (ISO 8601)"
    )
    config_hash: str = Field(
        ...,
        description="Configuration hash for determinism audit"
    )
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "ticker": "RELIANCE.NS",
                "date": "2024-10-08",
                "mode": "Investor",
                "score": 68.5,
                "band": "Buy",
                "pillars": {
                    "F": 75.0,
                    "T": 68.0,
                    "R": 82.0,
                    "O": 70.0,
                    "Q": 85.0,
                    "S": 73.0
                },
                "risk_penalty": 3.5,
                "guardrail_flags": ["LowDataHold"],
                "confidence": 0.85,
                "s_z": 1.2,
                "as_of": "2024-10-08T10:30:00Z",
                "config_hash": "abc123def456"
            }
        }


class StocksByBandResponse(BaseModel):
    """
    Response model for GET /scores/band/{band} endpoint.
    
    Contains list of stocks in a band plus summary statistics.
    """
    stocks: List[ScoreResponse] = Field(
        ...,
        description="List of stocks with the specified band"
    )
    statistics: Dict[str, Any] = Field(
        ...,
        description="Summary statistics for the band",
        example={
            "count": 25,
            "avg_score": 72.5,
            "min_score": 65.0,
            "max_score": 78.0,
            "date": "2024-10-08",
            "mode": "Investor",
            "band": "Buy"
        }
    )


class HealthResponse(BaseModel):
    """
    Response model for health check endpoint.
    
    Provides comprehensive system health information for monitoring.
    """
    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ...,
        description="Overall system health status"
    )
    service: str = Field(
        ...,
        description="Service name"
    )
    version: str = Field(
        ...,
        description="Service version"
    )
    timestamp: str = Field(
        ...,
        description="Health check timestamp (ISO 8601)"
    )
    components: Dict[str, Dict[str, Any]] = Field(
        ...,
        description="Individual component health status",
        example={
            "database": {
                "status": "healthy",
                "error": None,
                "stats": {
                    "total_scores": 1500,
                    "unique_tickers": 50
                }
            },
            "api": {
                "status": "healthy"
            }
        }
    )


class ErrorResponse(BaseModel):
    """
    Standard error response model.
    
    Used consistently across all endpoints for error conditions.
    """
    error: str = Field(..., description="Error type or category")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    timestamp: Optional[str] = Field(None, description="Error timestamp")
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid input parameters",
                "detail": "Ticker format is invalid",
                "timestamp": "2024-10-08T10:30:00Z"
            }
        }


class BatchScoreRequest(BaseModel):
    """
    Request model for batch score calculation (future enhancement).
    
    Allows scoring multiple stocks in a single API call for efficiency.
    """
    tickers: List[str] = Field(
        ...,
        description="List of ticker symbols to score",
        min_length=1,
        max_length=50
    )
    date: str = Field(
        ...,
        description="Scoring date for all tickers (YYYY-MM-DD)"
    )
    mode: Literal["Trader", "Investor"] = Field(
        ...,
        description="Scoring mode for all tickers"
    )
    
    @field_validator('tickers')
    @classmethod
    def validate_tickers(cls, v: List[str]) -> List[str]:
        """Validate all tickers in the list."""
        validated_tickers = []
        for ticker in v:
            if not ticker or len(ticker.strip()) < 2:
                raise ValueError(f"Invalid ticker: {ticker}")
            validated_tickers.append(ticker.strip().upper())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tickers = []
        for ticker in validated_tickers:
            if ticker not in seen:
                seen.add(ticker)
                unique_tickers.append(ticker)
        
        return unique_tickers


class BatchScoreResponse(BaseModel):
    """
    Response model for batch score calculation (future enhancement).
    """
    results: List[ScoreResponse] = Field(
        ...,
        description="Successful score calculations"
    )
    errors: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Failed calculations with error details"
    )
    summary: Dict[str, int] = Field(
        ...,
        description="Batch processing summary",
        example={
            "requested": 10,
            "successful": 9,
            "failed": 1
        }
    )


# Request/Response models for future endpoints

class ScoreHistoryRequest(BaseModel):
    """Request model for score history analysis (future enhancement)."""
    ticker: str
    start_date: str
    end_date: str
    mode: Optional[str] = None


class PortfolioAnalysisRequest(BaseModel):
    """Request model for portfolio analysis (future enhancement)."""
    tickers: List[str] = Field(..., max_length=20)
    weights: List[float] = Field(..., description="Portfolio weights (must sum to 1.0)")
    date: str
    mode: Literal["Trader", "Investor"]
    
    @field_validator('weights')
    @classmethod
    def validate_weights(cls, v: List[float], info) -> List[float]:
        """Validate that weights sum to 1.0 and match ticker count."""
        if abs(sum(v) - 1.0) > 0.01:
            raise ValueError("Portfolio weights must sum to 1.0")
        
        # Note: We can't access 'tickers' here in Pydantic v2 easily,
        # so this validation would be done at the endpoint level
        return v


class SectorAnalysisResponse(BaseModel):
    """Response model for sector analysis (future enhancement)."""
    sector: str
    date: str
    mode: str
    stocks: List[ScoreResponse]
    sector_statistics: Dict[str, float]
    momentum_analysis: Dict[str, Any]