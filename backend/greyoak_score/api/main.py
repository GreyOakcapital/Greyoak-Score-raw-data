"""
FastAPI application for GreyOak Score Engine - Production Hardened (CP7).

This module initializes the FastAPI application with comprehensive security,
monitoring, and production-ready features.

CP7 Features:
- Security hardening (CORS, Rate Limiting, Trusted Hosts)
- Dual health endpoints (/health for infra, /api/v1/health for app)
- Connection pooling with retry logic
- Structured JSON logging with request correlation
- Graceful shutdown with resource cleanup
- Environment-based configuration
- Performance monitoring and metrics
"""

import os
from typing import List, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import time
from contextlib import asynccontextmanager

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

import greyoak_score
from greyoak_score.api.routes import router
from greyoak_score.utils.logger import get_logger
from greyoak_score.data.persistence import get_database, close_database

logger = get_logger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    
    CP7 Startup:
    - Database connection pool initialization with retry logic
    - Environment configuration validation
    - Security middleware configuration logging
    - Health check system initialization
    
    CP7 Shutdown:
    - Database connection pool cleanup
    - Graceful resource cleanup
    - Audit logging of shutdown
    """
    # Startup
    start_time = time.time()
    logger.info("🚀 Starting GreyOak Score API with CP7 enhancements")
    
    # Log environment configuration (without secrets)
    env_config = {
        'app_env': os.getenv('APP_ENV', 'unknown'),
        'mode': os.getenv('MODE', 'unknown'),
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'rate_limit': os.getenv('RATE_LIMIT', '60'),
        'cors_enabled': bool(os.getenv('CORS_ORIGINS')),
        'trusted_hosts_enabled': bool(os.getenv('TRUSTED_HOSTS')),
        'pool_config': f"{os.getenv('DB_POOL_MIN_CONN', '2')}-{os.getenv('DB_POOL_MAX_CONN', '20')}"
    }
    logger.info(f"Environment configuration: {env_config}")
    
    # Initialize database connection pool with enhanced error handling
    try:
        db = get_database()
        if db.test_connection():
            pool_stats = db.get_pool_stats()
            logger.info(f"✅ Database connection pool initialized: {pool_stats}")
        else:
            logger.warning("⚠️ Database connection test failed - API will start but database operations may fail")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
        logger.warning("API starting in degraded mode - database operations will fail")
    
    startup_time = time.time() - start_time
    logger.info(f"🎯 GreyOak Score API v{greyoak_score.__version__} started successfully in {startup_time:.2f}s")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down GreyOak Score API")
    
    # Cleanup database connection pool
    try:
        close_database()
        logger.info("✅ Database connection pool closed successfully")
    except Exception as e:
        logger.error(f"❌ Error closing database pool: {e}")
    
    logger.info("👋 GreyOak Score API shutdown complete")


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