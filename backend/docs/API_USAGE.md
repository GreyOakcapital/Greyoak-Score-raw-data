# API Usage Guide - GreyOak Score Engine (CP7)

This comprehensive guide covers all aspects of using the GreyOak Score Engine API, including authentication, rate limiting, error handling, and detailed endpoint documentation.

## Table of Contents

- [Overview](#overview)
- [Base URL & Authentication](#base-url--authentication)
- [Rate Limiting & Security](#rate-limiting--security)
- [Request/Response Format](#requestresponse-format)
- [Error Handling](#error-handling)
- [API Endpoints](#api-endpoints)
- [Usage Examples](#usage-examples)
- [SDKs & Libraries](#sdks--libraries)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The GreyOak Score Engine API provides a comprehensive stock scoring system for Indian equities, generating deterministic 0-100 scores across six analytical pillars with risk management and investment band recommendations.

### Key Features (CP7)

- **Deterministic Scoring**: Consistent, reproducible scores with full audit trail
- **Six Pillars Analysis**: Fundamentals, Technicals, Relative Strength, Ownership, Quality, Sector Momentum
- **Risk Management**: Built-in risk penalties and sequential guardrails
- **Investment Bands**: Clear recommendations (Strong Buy, Buy, Hold, Avoid)
- **Dual Modes**: Trader (short-term) and Investor (long-term) perspectives
- **Security Hardening**: Rate limiting, CORS protection, request correlation
- **Real-time Health**: Comprehensive health monitoring and diagnostics

### API Specifications

- **Protocol**: REST API over HTTPS
- **Data Format**: JSON request/response
- **Authentication**: IP-based rate limiting (extensible for API keys)
- **Rate Limiting**: 60 requests per minute per IP address
- **Versioning**: URL path versioning (`/api/v1/`)

## Base URL & Authentication

### Base URL

```
Production: https://api.yourdomain.com
Development: http://localhost:8000
```

### Authentication (Current)

The API currently uses **IP-based rate limiting** without requiring authentication tokens. Future versions may include API key authentication.

```bash
# No authentication headers required currently
curl -X GET "https://api.yourdomain.com/api/v1/health"
```

### Future Authentication (Planned)

```bash
# Future API key authentication
curl -X GET "https://api.yourdomain.com/api/v1/health" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "X-API-Version: v1"
```

## Rate Limiting & Security

### Rate Limits (CP7)

| Endpoint Type | Rate Limit | Headers | Notes |
|---------------|------------|---------|-------|
| API Endpoints | 60 req/min per IP | `X-RateLimit-*` | Calculate, scores, bands |
| Health Checks | Unlimited | None | `/health` and `/api/v1/health` |
| Documentation | Unlimited | None | `/docs`, `/redoc` |

### Rate Limiting Headers

The API returns rate limiting information in response headers:

```bash
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1633564800
```

### CORS Policy

The API implements strict CORS policy based on configuration:

- **Allowed Origins**: Configured via `CORS_ORIGINS` environment variable
- **Allowed Methods**: GET, POST, PUT, DELETE, OPTIONS, HEAD
- **Allowed Headers**: All standard headers
- **Credentials**: Supported for authenticated requests

### Security Headers

All responses include security headers:

```bash
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
```

## Request/Response Format

### Content Type

All requests must use JSON content type:

```bash
Content-Type: application/json
Accept: application/json
```

### Request Headers

**Required Headers:**
```bash
Content-Type: application/json
```

**Optional Headers:**
```bash
User-Agent: YourApp/1.0.0
X-Correlation-ID: unique-request-id  # For tracking
```

### Response Format

All API responses follow a consistent structure:

**Successful Response:**
```json
{
  "success": true,
  "data": {
    // Response payload
  },
  "meta": {
    "timestamp": "2024-10-08T10:30:00Z",
    "version": "1.0.0",
    "request_id": "req_1633564800123456"
  }
}
```

**Error Response:**
```json
{
  "error": "Error Type",
  "message": "Human-readable error description",
  "details": {
    // Additional error context
  },
  "request_id": "req_1633564800123456"
}
```

## Error Handling

### Standard Error Schema (CP7)

All error responses follow the standardized error schema with correlation IDs:

```json
{
  "error": "Validation Error",
  "message": "The request data is invalid. Please check the required fields and formats.",
  "details": [
    {
      "type": "missing",
      "loc": ["body", "ticker"],
      "msg": "field required",
      "input": {}
    }
  ],
  "request_id": "req_1633564800123456"
}
```

### HTTP Status Codes

| Status Code | Error Type | Description |
|-------------|------------|-------------|
| `200` | Success | Request completed successfully |
| `400` | Bad Request | Invalid request parameters |
| `404` | Not Found | Resource not found |
| `422` | Validation Error | Request data validation failed |
| `429` | Rate Limited | Too many requests (60/min exceeded) |
| `500` | Internal Error | Unexpected server error |
| `503` | Service Unavailable | Service temporarily unavailable |

### Error Types

#### 1. Validation Errors (422)

```json
{
  "error": "Validation Error",
  "message": "The request data is invalid. Please check the required fields and formats.",
  "details": [
    {
      "type": "value_error",
      "loc": ["body", "mode"],
      "msg": "Invalid mode. Must be 'Trader' or 'Investor'",
      "input": "BadMode"
    }
  ],
  "request_id": "req_1633564800123456"
}
```

#### 2. Rate Limiting Errors (429)

```json
{
  "error": "Rate Limit Exceeded", 
  "message": "Too many requests. Please try again in 60 seconds.",
  "details": {
    "limit": 60,
    "window": "60 seconds",
    "retry_after": 45
  },
  "request_id": "req_1633564800123456"
}
```

#### 3. Not Found Errors (404)

```json
{
  "error": "HTTP 404",
  "message": "Not Found",
  "request_id": "req_1633564800123456"
}
```

#### 4. Internal Server Errors (500)

```json
{
  "error": "Internal Server Error",
  "message": "An unexpected error occurred. Please try again later or contact support.",
  "request_id": "req_1633564800123456"
}
```

## API Endpoints

### 1. Calculate Score

Generate a comprehensive GreyOak Score for a stock.

**Endpoint:**
```
POST /api/v1/calculate
```

**Rate Limit:** 60 requests/minute per IP

**Request Schema:**
```json
{
  "ticker": "string",      // Stock ticker (e.g., "RELIANCE.NS")
  "date": "string",        // Date in YYYY-MM-DD format
  "mode": "string"         // "Trader" or "Investor"
}
```

**Response Schema:**
```json
{
  "ticker": "RELIANCE.NS",
  "date": "2024-10-08",
  "mode": "Investor", 
  "score": 74.25,
  "band": "Buy",
  "pillars": {
    "F": 78.5,    // Fundamentals
    "T": 72.0,    // Technicals  
    "R": 81.2,    // Relative Strength
    "O": 69.8,    // Ownership
    "Q": 76.4,    // Quality
    "S": 70.1     // Sector Momentum
  },
  "risk_penalty": 3.75,
  "guardrails": ["LowDataHold"],
  "confidence": 85.2,
  "as_of": "2024-10-08T10:30:00Z",
  "config_hash": "abc123...",
  "code_version": "1.0.0"
}
```

**Example Request:**
```bash
curl -X POST "https://api.yourdomain.com/api/v1/calculate" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "RELIANCE.NS",
    "date": "2024-10-08", 
    "mode": "Investor"
  }'
```

**Example Response:**
```json
{
  "ticker": "RELIANCE.NS",
  "date": "2024-10-08",
  "mode": "Investor",
  "score": 74.25,
  "band": "Buy",
  "pillars": {
    "F": 78.5,
    "T": 72.0,
    "R": 81.2,
    "O": 69.8,
    "Q": 76.4,
    "S": 70.1
  },
  "risk_penalty": 3.75,
  "guardrails": ["LowDataHold"],
  "confidence": 85.2,
  "as_of": "2024-10-08T10:30:00Z"
}
```

### 2. Get Score History

Retrieve historical scores for a specific ticker.

**Endpoint:**
```
GET /api/v1/scores/{ticker}
```

**Rate Limit:** 60 requests/minute per IP

**Path Parameters:**
- `ticker` (string): Stock ticker symbol (e.g., "RELIANCE.NS")

**Query Parameters:**
- `start_date` (optional): Start date filter (YYYY-MM-DD)
- `end_date` (optional): End date filter (YYYY-MM-DD)
- `mode` (optional): Filter by mode ("Trader" or "Investor")
- `limit` (optional): Max results (1-1000, default: 100)

**Response Schema:**
```json
[
  {
    "ticker": "RELIANCE.NS",
    "date": "2024-10-08",
    "mode": "Investor",
    "score": 74.25,
    "band": "Buy",
    // ... full score details
  },
  // ... more historical scores
]
```

**Example Request:**
```bash
curl "https://api.yourdomain.com/api/v1/scores/RELIANCE.NS?mode=Investor&limit=10"
```

**Example with Filters:**
```bash
curl "https://api.yourdomain.com/api/v1/scores/RELIANCE.NS?start_date=2024-10-01&end_date=2024-10-08&mode=Investor"
```

### 3. Get Stocks by Band

Retrieve all stocks with a specific investment band on a given date.

**Endpoint:**
```
GET /api/v1/scores/band/{band}
```

**Rate Limit:** 60 requests/minute per IP

**Path Parameters:**
- `band` (string): Investment band ("Strong Buy", "Buy", "Hold", "Avoid")

**Query Parameters:**
- `date` (required): Score date (YYYY-MM-DD)
- `mode` (required): Scoring mode ("Trader" or "Investor")  
- `limit` (optional): Max results (1-500, default: 50)

**Response Schema:**
```json
{
  "band": "Buy",
  "date": "2024-10-08",
  "mode": "Investor",
  "count": 25,
  "average_score": 69.8,
  "stocks": [
    {
      "ticker": "RELIANCE.NS",
      "score": 74.25,
      "band": "Buy",
      // ... score details
    },
    // ... more stocks in this band
  ]
}
```

**Example Request:**
```bash
curl "https://api.yourdomain.com/api/v1/scores/band/Buy?date=2024-10-08&mode=Investor&limit=20"
```

### 4. Health Check (Application)

Comprehensive health check including database connectivity.

**Endpoint:**
```
GET /api/v1/health
```

**Rate Limit:** Unlimited (exempt)

**Response Schema:**
```json
{
  "status": "healthy",
  "service": "GreyOak Score API", 
  "version": "1.0.0",
  "timestamp": "2024-10-08T10:30:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "details": "Connection pool: 5/20 connections",
      "response_time_ms": 15
    },
    "api": {
      "status": "healthy", 
      "details": "All endpoints operational"
    }
  },
  "stats": {
    "total_scores": 1250,
    "unique_tickers": 150,
    "unique_dates": 30,
    "latest_date": "2024-10-08",
    "band_distribution": {
      "Strong Buy": 15,
      "Buy": 45,
      "Hold": 60,
      "Avoid": 30
    }
  },
  "performance": {
    "uptime_seconds": 86400,
    "request_count_today": 1500
  }
}
```

**Status Values:**
- `healthy`: All systems operational
- `degraded`: API running but some components (e.g., database) have issues
- `unhealthy`: Critical system failures

**Example Request:**
```bash
curl "https://api.yourdomain.com/api/v1/health"
```

### 5. Health Check (Infrastructure)

Basic service availability check for load balancers.

**Endpoint:**
```
GET /health
```

**Rate Limit:** Unlimited (exempt)

**Response Schema:**
```json
{
  "status": "healthy",
  "service": "greyoak-score-api",
  "version": "1.0.0", 
  "timestamp": 1633564800,
  "environment": "production",
  "check_type": "infrastructure"
}
```

**Example Request:**
```bash
curl "https://api.yourdomain.com/health"
```

### 6. API Documentation

Interactive API documentation and schema.

**Endpoints:**
```
GET /docs          # Swagger UI
GET /redoc         # ReDoc UI  
GET /openapi.json  # OpenAPI schema
```

**Rate Limit:** Unlimited

**Example:**
```bash
# Access interactive documentation
open https://api.yourdomain.com/docs

# Download OpenAPI schema
curl "https://api.yourdomain.com/openapi.json" > greyoak-api-schema.json
```

## Usage Examples

### Basic Workflow

```python
import requests
import json

# Configuration
BASE_URL = "https://api.yourdomain.com"
HEADERS = {"Content-Type": "application/json"}

# 1. Check API health
health = requests.get(f"{BASE_URL}/api/v1/health")
print(f"API Status: {health.json()['status']}")

# 2. Calculate score for a stock
score_request = {
    "ticker": "RELIANCE.NS",
    "date": "2024-10-08", 
    "mode": "Investor"
}

response = requests.post(
    f"{BASE_URL}/api/v1/calculate",
    headers=HEADERS,
    json=score_request
)

if response.status_code == 200:
    score = response.json()
    print(f"Score: {score['score']:.2f}, Band: {score['band']}")
else:
    error = response.json()
    print(f"Error: {error['message']}")

# 3. Get historical scores
history = requests.get(
    f"{BASE_URL}/api/v1/scores/RELIANCE.NS?mode=Investor&limit=5"
)

scores = history.json()
for score in scores:
    print(f"{score['date']}: {score['score']:.2f} ({score['band']})")

# 4. Find all "Buy" stocks
buy_stocks = requests.get(
    f"{BASE_URL}/api/v1/scores/band/Buy?date=2024-10-08&mode=Investor"
)

result = buy_stocks.json()
print(f"Found {result['count']} Buy-rated stocks")
```

### Error Handling

```python
import requests
from requests.exceptions import RequestException
import time

def make_api_request(url, method="GET", data=None, max_retries=3):
    """Make API request with error handling and retry logic."""
    
    for attempt in range(max_retries):
        try:
            if method == "POST":
                response = requests.post(url, json=data, headers=HEADERS, timeout=30)
            else:
                response = requests.get(url, timeout=30)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                print(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                continue
            
            # Handle other errors
            if response.status_code >= 400:
                error_data = response.json()
                print(f"API Error: {error_data.get('message', 'Unknown error')}")
                print(f"Request ID: {error_data.get('request_id')}")
                return None
            
            return response.json()
            
        except RequestException as e:
            print(f"Network error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            
    print("Max retries exceeded")
    return None

# Usage example
result = make_api_request(
    "https://api.yourdomain.com/api/v1/calculate",
    method="POST",
    data={"ticker": "RELIANCE.NS", "date": "2024-10-08", "mode": "Investor"}
)
```

### Batch Processing

```python
import asyncio
import aiohttp
import json
from typing import List, Dict

async def calculate_scores_batch(tickers: List[str], date: str, mode: str):
    """Calculate scores for multiple tickers efficiently."""
    
    BASE_URL = "https://api.yourdomain.com"
    results = []
    
    # Rate limiting: max 60 requests per minute
    semaphore = asyncio.Semaphore(10)  # Concurrent requests
    
    async def calculate_single_score(session, ticker):
        async with semaphore:
            try:
                async with session.post(
                    f"{BASE_URL}/api/v1/calculate",
                    json={"ticker": ticker, "date": date, "mode": mode}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"ticker": ticker, "success": True, "data": data}
                    elif response.status == 429:
                        # Rate limited - wait and retry
                        await asyncio.sleep(60)
                        return await calculate_single_score(session, ticker)
                    else:
                        error_data = await response.json()
                        return {"ticker": ticker, "success": False, "error": error_data}
            except Exception as e:
                return {"ticker": ticker, "success": False, "error": str(e)}
    
    async with aiohttp.ClientSession(
        headers={"Content-Type": "application/json"},
        timeout=aiohttp.ClientTimeout(total=30)
    ) as session:
        tasks = [calculate_single_score(session, ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks)
    
    return results

# Usage
tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFC.NS", "ICICIBANK.NS"]
results = asyncio.run(calculate_scores_batch(tickers, "2024-10-08", "Investor"))

for result in results:
    if result["success"]:
        data = result["data"]
        print(f"{result['ticker']}: {data['score']:.2f} ({data['band']})")
    else:
        print(f"{result['ticker']}: Error - {result['error']}")
```

### Real-time Monitoring

```python
import requests
import time
import json
from datetime import datetime

def monitor_api_health(interval_seconds=60):
    """Monitor API health and performance."""
    
    BASE_URL = "https://api.yourdomain.com"
    
    while True:
        try:
            start_time = time.time()
            
            # Check infrastructure health
            infra_health = requests.get(f"{BASE_URL}/health", timeout=10)
            infra_status = infra_health.json()["status"]
            
            # Check application health
            app_health = requests.get(f"{BASE_URL}/api/v1/health", timeout=30)
            app_data = app_health.json()
            
            response_time = (time.time() - start_time) * 1000
            
            # Log health status
            timestamp = datetime.now().isoformat()
            health_log = {
                "timestamp": timestamp,
                "infrastructure_status": infra_status,
                "application_status": app_data["status"],
                "response_time_ms": round(response_time, 2),
                "database_status": app_data["components"]["database"]["status"],
                "total_scores": app_data["stats"]["total_scores"]
            }
            
            print(json.dumps(health_log))
            
            # Alert on issues
            if infra_status != "healthy" or app_data["status"] != "healthy":
                print(f"ALERT: API health issue detected at {timestamp}")
            
            if response_time > 5000:  # 5 seconds
                print(f"ALERT: High response time: {response_time:.2f}ms")
                
        except Exception as e:
            error_log = {
                "timestamp": datetime.now().isoformat(),
                "error": "Health check failed",
                "details": str(e)
            }
            print(json.dumps(error_log))
        
        time.sleep(interval_seconds)

# Start monitoring
monitor_api_health(interval_seconds=30)
```

## SDKs & Libraries

### Official Python SDK (Planned)

```python
# Future official SDK
from greyoak_client import GreyOakClient

client = GreyOakClient(
    base_url="https://api.yourdomain.com",
    api_key="your_api_key"  # Future authentication
)

# Calculate score
score = client.calculate_score("RELIANCE.NS", "2024-10-08", "Investor")
print(f"Score: {score.score}, Band: {score.band}")

# Get history
history = client.get_score_history("RELIANCE.NS", mode="Investor", limit=10)
for score in history:
    print(f"{score.date}: {score.score} ({score.band})")
```

### Community Libraries

**JavaScript/Node.js Example:**

```javascript
// Example Node.js implementation
const axios = require('axios');

class GreyOakClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        this.client = axios.create({
            baseURL: baseUrl,
            timeout: 30000,
            headers: {'Content-Type': 'application/json'}
        });
        
        // Add retry logic for rate limiting
        this.client.interceptors.response.use(
            response => response,
            async error => {
                if (error.response?.status === 429) {
                    const retryAfter = error.response.headers['retry-after'] || 60;
                    await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
                    return this.client.request(error.config);
                }
                throw error;
            }
        );
    }
    
    async calculateScore(ticker, date, mode) {
        try {
            const response = await this.client.post('/api/v1/calculate', {
                ticker, date, mode
            });
            return response.data;
        } catch (error) {
            throw new Error(`API Error: ${error.response?.data?.message || error.message}`);
        }
    }
    
    async getScoreHistory(ticker, options = {}) {
        try {
            const params = new URLSearchParams(options);
            const response = await this.client.get(`/api/v1/scores/${ticker}?${params}`);
            return response.data;
        } catch (error) {
            throw new Error(`API Error: ${error.response?.data?.message || error.message}`);
        }
    }
}

// Usage
const client = new GreyOakClient('https://api.yourdomain.com');

client.calculateScore('RELIANCE.NS', '2024-10-08', 'Investor')
    .then(score => console.log(`Score: ${score.score}, Band: ${score.band}`))
    .catch(error => console.error(error.message));
```

## Best Practices

### 1. Rate Limit Management

```python
import time
from functools import wraps

def rate_limit_handler(max_requests_per_minute=60):
    """Decorator to handle rate limiting automatically."""
    min_interval = 60.0 / max_requests_per_minute
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            
            last_called[0] = time.time()
            return func(*args, **kwargs)
        return wrapper
    return decorator

@rate_limit_handler(max_requests_per_minute=50)  # Conservative limit
def calculate_score_with_rate_limit(ticker, date, mode):
    # Your API call here
    pass
```

### 2. Error Handling & Retry Logic

```python
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def create_session_with_retries():
    """Create requests session with retry logic."""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "OPTIONS", "POST"],
        backoff_factor=1
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

# Usage
session = create_session_with_retries()
response = session.post(url, json=data, timeout=30)
```

### 3. Response Caching

```python
import requests_cache
from datetime import timedelta

# Cache responses to reduce API calls
session = requests_cache.CachedSession(
    'greyoak_cache',
    expire_after=timedelta(minutes=5)
)

# Cached requests
response = session.get('https://api.yourdomain.com/api/v1/health')
```

### 4. Correlation ID Tracking

```python
import uuid
import requests

def make_tracked_request(url, method="GET", data=None):
    """Make API request with correlation ID for tracking."""
    correlation_id = str(uuid.uuid4())
    
    headers = {
        "Content-Type": "application/json",
        "X-Correlation-ID": correlation_id
    }
    
    print(f"Making request with correlation ID: {correlation_id}")
    
    if method == "POST":
        response = requests.post(url, json=data, headers=headers)
    else:
        response = requests.get(url, headers=headers)
    
    # Log response correlation ID
    response_id = response.json().get("request_id")
    print(f"Response correlation ID: {response_id}")
    
    return response
```

### 5. Bulk Operations

```python
def process_scores_in_batches(tickers, date, mode, batch_size=10):
    """Process multiple tickers in batches to respect rate limits."""
    results = []
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        batch_results = []
        
        for ticker in batch:
            try:
                score = calculate_score_with_rate_limit(ticker, date, mode)
                batch_results.append({"ticker": ticker, "success": True, "data": score})
            except Exception as e:
                batch_results.append({"ticker": ticker, "success": False, "error": str(e)})
        
        results.extend(batch_results)
        
        # Progress logging
        processed = min(i + batch_size, len(tickers))
        print(f"Processed {processed}/{len(tickers)} tickers")
        
        # Brief pause between batches
        time.sleep(1)
    
    return results
```

## Troubleshooting

### Common Issues

#### 1. Rate Limit Exceeded (429)

**Problem:** Getting `429 Too Many Requests` errors.

**Solution:**
```python
# Check rate limit headers
response = requests.get(url)
print(f"Limit: {response.headers.get('X-RateLimit-Limit')}")
print(f"Remaining: {response.headers.get('X-RateLimit-Remaining')}")
print(f"Reset: {response.headers.get('X-RateLimit-Reset')}")

# Implement backoff
if response.status_code == 429:
    retry_after = int(response.headers.get('Retry-After', 60))
    time.sleep(retry_after)
```

#### 2. CORS Errors

**Problem:** Browser CORS policy errors.

**Solution:**
```javascript
// Ensure proper CORS headers
fetch('https://api.yourdomain.com/api/v1/health', {
    method: 'GET',
    headers: {
        'Content-Type': 'application/json',
    },
    mode: 'cors'  // Important for CORS requests
})
.then(response => response.json())
.then(data => console.log(data));
```

#### 3. Validation Errors (422)

**Problem:** Request validation failures.

**Solution:**
```python
# Check validation details
if response.status_code == 422:
    error_data = response.json()
    for error in error_data["details"]:
        print(f"Field: {error['loc'][-1]}")
        print(f"Error: {error['msg']}")
        print(f"Value: {error.get('input')}")
```

#### 4. Connection Timeouts

**Problem:** Requests timing out.

**Solution:**
```python
import requests

# Increase timeout values
response = requests.post(
    url, 
    json=data, 
    timeout=(10, 60)  # (connection_timeout, read_timeout)
)

# Or use session with default timeout
session = requests.Session()
session.timeout = 30
response = session.post(url, json=data)
```

### Debugging Tools

#### Request/Response Logging

```python
import logging
import http.client as http_client

# Enable detailed HTTP logging
http_client.HTTPConnection.debuglevel = 1

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
```

#### Response Analysis

```python
def analyze_response(response):
    """Analyze API response for debugging."""
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    
    if response.headers.get('content-type', '').startswith('application/json'):
        data = response.json()
        if 'request_id' in data:
            print(f"Request ID: {data['request_id']}")
        print(f"Response: {json.dumps(data, indent=2)}")
    else:
        print(f"Response Text: {response.text[:500]}")
```

### API Testing

#### Health Check Validation

```bash
#!/bin/bash
# test_api_health.sh

BASE_URL="https://api.yourdomain.com"

echo "Testing API Health..."

# Test infrastructure health
echo "1. Infrastructure Health:"
curl -s "$BASE_URL/health" | jq .

# Test application health  
echo "2. Application Health:"
curl -s "$BASE_URL/api/v1/health" | jq .

# Test rate limiting headers
echo "3. Rate Limiting Headers:"
curl -I "$BASE_URL/api/v1/health" | grep -i "ratelimit"

# Test CORS headers
echo "4. CORS Headers:"
curl -H "Origin: https://yourdomain.com" -I "$BASE_URL/api/v1/health" | grep -i "access-control"

echo "Health check complete!"
```

#### Load Testing

```python
import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor

async def load_test_api(concurrent_requests=10, total_requests=100):
    """Basic load test for the API."""
    
    BASE_URL = "https://api.yourdomain.com"
    success_count = 0
    error_count = 0
    
    async def make_request(session):
        nonlocal success_count, error_count
        try:
            async with session.get(f"{BASE_URL}/api/v1/health") as response:
                if response.status == 200:
                    success_count += 1
                else:
                    error_count += 1
        except Exception:
            error_count += 1
    
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(concurrent_requests)
        
        async def bounded_request():
            async with semaphore:
                await make_request(session)
        
        tasks = [bounded_request() for _ in range(total_requests)]
        await asyncio.gather(*tasks)
    
    duration = time.time() - start_time
    
    print(f"Load Test Results:")
    print(f"Total Requests: {total_requests}")
    print(f"Concurrent: {concurrent_requests}")
    print(f"Duration: {duration:.2f}s")
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Requests/sec: {total_requests/duration:.2f}")

# Run load test
asyncio.run(load_test_api(concurrent_requests=5, total_requests=50))
```

## Support & Resources

### Documentation Links

- **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment procedures
- **Database Migrations**: [DB_MIGRATIONS.md](DB_MIGRATIONS.md) - Schema management
- **Architecture Overview**: [architecture.md](architecture.md) - System design
- **Configuration Guide**: [configuration_guide.md](configuration_guide.md) - Setup options

### Interactive Documentation

- **Swagger UI**: `/docs` - Interactive API testing interface
- **ReDoc**: `/redoc` - Clean API documentation
- **OpenAPI Schema**: `/openapi.json` - Machine-readable API specification

### Community Resources

- **GitHub Issues**: Report bugs and request features
- **API Examples**: Community-contributed code examples
- **SDKs**: Third-party client libraries

### Getting Help

1. **Check Health Endpoints**: Verify API status first
2. **Review Error Messages**: Use `request_id` for support requests
3. **Check Rate Limits**: Verify you're within limits
4. **Validate Requests**: Ensure proper JSON format and required fields
5. **Monitor CORS**: Check browser console for CORS issues

---

**Last Updated**: CP7 Implementation - October 2024  
**API Version**: 1.0.0  
**Rate Limits**: 60 requests/minute per IP

This API usage guide covers all aspects of integrating with the GreyOak Score Engine API. For additional support or questions, refer to the comprehensive error messages and correlation IDs provided in all API responses.