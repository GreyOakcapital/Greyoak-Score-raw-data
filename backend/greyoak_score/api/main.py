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

# Load environment variables explicitly
from dotenv import load_dotenv
load_dotenv()

import greyoak_score
from greyoak_score.api.routes import router
from greyoak_score.utils.logger import get_logger
from greyoak_score.data.persistence import get_database, close_database

logger = get_logger(__name__)

# Initialize rate limiter with headers enabled (CP7 fix)
limiter = Limiter(key_func=get_remote_address, headers_enabled=True)


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


# Initialize FastAPI application with CP7 security enhancements
app = FastAPI(
    title="GreyOak Score API",
    description="""
    **GreyOak Score Engine API** - Production-ready stock scoring system for Indian equities.
    
    ## 🎯 Features (CP7 Enhanced)
    
    * **Calculate Scores**: Generate comprehensive 0-100 scores with investment bands
    * **Six Pillars**: Fundamentals, Technicals, Relative Strength, Ownership, Quality, Sector Momentum  
    * **Risk Management**: Built-in risk penalties and sequential guardrails
    * **Dual Modes**: Trader (short-term) and Investor (long-term) perspectives
    * **Audit Trail**: Complete deterministic scoring with configuration tracking
    
    ## 🔒 Security Features (CP7)
    
    * **Rate Limiting**: 60 requests/minute per IP (configurable)
    * **CORS Protection**: Configurable origin restrictions
    * **Trusted Hosts**: Host header validation
    * **Connection Pooling**: Efficient database connections (2-20 pool)
    * **Health Monitoring**: Dual health endpoints for infrastructure and application
    
    ## 🚀 Quick Start
    
    1. **Calculate a score**: `POST /api/v1/calculate`
    2. **Get score history**: `GET /api/v1/scores/{ticker}`
    3. **Find by investment band**: `GET /api/v1/scores/band/{band}`
    4. **Health check**: `GET /health` (infra) or `GET /api/v1/health` (app)
    
    ## 📊 Investment Bands
    
    * **Strong Buy** (75-100): High conviction opportunities
    * **Buy** (65-74): Good investment prospects  
    * **Hold** (50-64): Neutral outlook, maintain positions
    * **Avoid** (0-49): High risk, avoid or exit
    
    ## ⚡ Modes
    
    * **Trader**: Short-term focus (1-6 months), technical emphasis
    * **Investor**: Long-term focus (12-24 months), fundamental emphasis
    
    ## 🏥 Health Endpoints
    
    * **`GET /health`**: Infrastructure health check (no database)
    * **`GET /api/v1/health`**: Application health check (with database)
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

# Configure security middleware (CP7)
def setup_security_middleware():
    """Configure security middleware based on environment variables."""
    
    # 1. Rate Limiting Middleware
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    logger.info("✅ Rate limiting middleware configured")
    
    # 2. Trusted Host Middleware
    trusted_hosts = os.getenv('TRUSTED_HOSTS')
    if trusted_hosts:
        hosts = [host.strip() for host in trusted_hosts.split(',')]
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=hosts
        )
        logger.info(f"✅ Trusted hosts middleware configured: {hosts}")
    else:
        logger.warning("⚠️ TRUSTED_HOSTS not configured - all hosts allowed")
    
    # 3. CORS Middleware (CP7 fix for environment variable loading)
    cors_origins = os.getenv('CORS_ORIGINS')
    if cors_origins:
        # Parse comma-separated origins and strip whitespace
        origins = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],  # Allow all methods including OPTIONS
            allow_headers=["*"],
        )
        logger.info(f"✅ CORS middleware configured with origins: {origins}")
    else:
        # For development, allow localhost origins if no CORS_ORIGINS set
        # In production, this should be explicitly configured
        dev_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000", 
            "http://localhost:8000",
            "http://127.0.0.1:8000"
        ]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=dev_origins,
            allow_credentials=True,
            allow_methods=["*"],  # Allow all methods including OPTIONS
            allow_headers=["*"],
        )
        logger.warning(f"⚠️ CORS_ORIGINS not configured - using development defaults: {dev_origins}")

# Apply security configuration
setup_security_middleware()


# Enhanced exception handlers (CP7)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors with detailed field information.
    """
    request_id = f"req_{int(time.time() * 1000000)}"  # Microsecond timestamp
    
    logger.warning(f"Validation error [{request_id}]: {exc}", extra={
        'method': request.method,
        'url': str(request.url),
        'client': request.client.host if request.client else 'unknown',
        'request_id': request_id
    })
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": "The request data is invalid. Please check the required fields and formats.",
            "details": exc.errors(),
            "request_id": request_id
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handle HTTP exceptions with consistent response format.
    """
    request_id = f"req_{int(time.time() * 1000000)}"
    
    logger.warning(f"HTTP exception [{request_id}]: {exc.status_code} - {exc.detail}", extra={
        'method': request.method,
        'url': str(request.url),
        'client': request.client.host if request.client else 'unknown',
        'status_code': exc.status_code,
        'request_id': request_id
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP {exc.status_code}",
            "message": exc.detail,
            "request_id": request_id
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions with enhanced logging.
    """
    request_id = f"req_{int(time.time() * 1000000)}"
    
    logger.error(f"Unhandled exception [{request_id}]: {exc}", exc_info=True, extra={
        'method': request.method,
        'url': str(request.url),
        'client': request.client.host if request.client else 'unknown',
        'request_id': request_id,
        'exception_type': type(exc).__name__
    })
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later or contact support.",
            "request_id": request_id
        }
    )


# Register API routes
app.include_router(router)


@app.get("/", tags=["root"])
@limiter.exempt  # Exempt root endpoint from rate limiting
async def root():
    """
    Root endpoint providing API information and navigation (CP7 Enhanced).
    
    Returns comprehensive API information including security features.
    """
    return {
        "service": "GreyOak Score API",
        "version": greyoak_score.__version__,
        "description": "Production-ready stock scoring engine for Indian equities (CP7)",
        "features": {
            "security": {
                "rate_limiting": "60 req/min per IP",
                "cors_protection": "Configurable origins",
                "trusted_hosts": "Host header validation",
                "connection_pooling": "2-20 database connections"
            },
            "monitoring": {
                "infrastructure_health": "GET /health",
                "application_health": "GET /api/v1/health"
            }
        },
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
        "configuration": {
            "modes": ["Trader", "Investor"],
            "bands": ["Strong Buy", "Buy", "Hold", "Avoid"],
            "pillars": ["F", "T", "R", "O", "Q", "S"]
        },
        "environment": {
            "app_env": os.getenv('APP_ENV', 'unknown'),
            "mode": os.getenv('MODE', 'unknown')
        }
    }


@app.get("/health", tags=["monitoring"])
@limiter.exempt  # Exempt health endpoint from rate limiting
async def infrastructure_health():
    """
    Infrastructure health check endpoint (CP7).
    
    For load balancers, monitoring systems, and Kubernetes health checks.
    Returns basic status without database connectivity check for fast response.
    
    This endpoint is exempt from rate limiting and should always be accessible.
    """
    return {
        "status": "healthy",
        "service": "greyoak-score-api",
        "version": greyoak_score.__version__,
        "timestamp": int(time.time()),
        "environment": os.getenv('APP_ENV', 'unknown'),
        "check_type": "infrastructure"
    }


# For debugging and development
if __name__ == "__main__":
    import uvicorn
    
    # Development configuration
    config = {
        "app": "greyoak_score.api.main:app",
        "host": "0.0.0.0",
        "port": 8000,
        "reload": True,
        "log_level": "info",
        "workers": 1
    }
    
    logger.info(f"Starting development server with config: {config}")
    uvicorn.run(**config)