"""
FastAPI application for GreyOak Score Engine.

This module initializes the FastAPI application with proper configuration,
middleware, exception handling, and route registration.

Key Features:
- RESTful API endpoints for score calculation and retrieval
- Automatic OpenAPI/Swagger documentation
- Input validation with Pydantic models
- Proper error handling and HTTP status codes
- CORS support for web applications
- Health check endpoints for monitoring
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

import greyoak_score
from greyoak_score.api.routes import router
from greyoak_score.utils.logger import get_logger
from greyoak_score.data.persistence import get_database

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    
    Handles:
    - Database connection testing on startup
    - Resource cleanup on shutdown
    """
    # Startup
    logger.info("Starting GreyOak Score API")
    
    # Test database connection
    try:
        db = get_database()
        if db.test_connection():
            logger.info("Database connection test successful")
        else:
            logger.warning("Database connection test failed - API will start but database operations may fail")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
    
    logger.info(f"GreyOak Score API v{greyoak_score.__version__} started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down GreyOak Score API")


# Initialize FastAPI application
app = FastAPI(
    title="GreyOak Score API",
    description="""
    **GreyOak Score Engine API** - Professional stock scoring system for Indian equities.
    
    ## Features
    
    * **Calculate Scores**: Generate comprehensive 0-100 scores with investment bands
    * **Six Pillars**: Fundamentals, Technicals, Relative Strength, Ownership, Quality, Sector Momentum  
    * **Risk Management**: Built-in risk penalties and sequential guardrails
    * **Dual Modes**: Trader (short-term) and Investor (long-term) perspectives
    * **Audit Trail**: Complete deterministic scoring with configuration tracking
    
    ## Quick Start
    
    1. **Calculate a score**: `POST /api/v1/calculate`
    2. **Get score history**: `GET /api/v1/scores/{ticker}`
    3. **Find by investment band**: `GET /api/v1/scores/band/{band}`
    
    ## Investment Bands
    
    * **Strong Buy** (75-100): High conviction opportunities
    * **Buy** (65-74): Good investment prospects  
    * **Hold** (50-64): Neutral outlook, maintain positions
    * **Avoid** (0-49): High risk, avoid or exit
    
    ## Modes
    
    * **Trader**: Short-term focus (1-6 months), technical emphasis
    * **Investor**: Long-term focus (12-24 months), fundamental emphasis
    """,
    version=greyoak_score.__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "GreyOak Score Engine",  
        "email": "support@greyoak.com",
    },
    license_info={
        "name": "Proprietary",
        "url": "https://greyoak.com/license",
    },
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to catch unhandled exceptions.
    
    Logs the full exception details and returns a user-friendly error response.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True, extra={
        'method': request.method,
        'url': str(request.url),
        'client': request.client.host if request.client else 'unknown'
    })
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": id(request)  # Simple request ID for debugging
        }
    )


# Register API routes
app.include_router(router)


@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint providing API information and navigation.
    
    Returns basic API information and links to documentation.
    """
    return {
        "service": "GreyOak Score API",
        "version": greyoak_score.__version__,
        "description": "Professional stock scoring engine for Indian equities",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_spec": "/openapi.json"
        },
        "endpoints": {
            "calculate_score": "POST /api/v1/calculate",
            "get_scores": "GET /api/v1/scores/{ticker}",
            "get_by_band": "GET /api/v1/scores/band/{band}",
            "health_check": "GET /api/v1/health"
        },
        "modes": ["Trader", "Investor"],
        "bands": ["Strong Buy", "Buy", "Hold", "Avoid"]
    }


@app.get("/health", tags=["monitoring"])
async def health_check():
    """
    Simple health check endpoint for monitoring and load balancers.
    
    Returns basic health status without database connectivity check.
    """
    return {
        "status": "healthy",
        "service": "greyoak-score-api",
        "version": greyoak_score.__version__
    }


# For debugging and development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "greyoak_score.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )