# Production Deployment Guide - GreyOak Score Engine (CP7)

This comprehensive guide covers deploying the GreyOak Score Engine in production environments with full CP7 security and hardening features.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Environment Setup](#environment-setup)
- [Docker Deployment](#docker-deployment)
- [Database Configuration](#database-configuration)
- [Security Configuration](#security-configuration)
- [Monitoring & Health Checks](#monitoring--health-checks)
- [Performance Tuning](#performance-tuning)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)

## Prerequisites

### System Requirements

**Minimum Production Requirements:**
- **CPU**: 2 cores (4 cores recommended)
- **Memory**: 2GB RAM (4GB recommended)
- **Storage**: 10GB available disk space
- **Network**: Stable internet connection for data feeds

**Software Dependencies:**
- **Docker**: 20.10+ 
- **Docker Compose**: 2.0+
- **PostgreSQL**: 15+ (containerized or external)
- **Load Balancer**: Nginx/HAProxy (for multi-instance deployments)

### Security Prerequisites

- **SSL/TLS Certificates**: Valid certificates for HTTPS endpoints
- **Firewall Configuration**: Proper network security rules
- **Secrets Management**: Secure storage for database credentials and API keys
- **Monitoring Tools**: Log aggregation and alerting systems

## Architecture Overview

### CP7 Production Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer / Proxy                    │
│              (Nginx/HAProxy + SSL Termination)              │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                GreyOak Score API                            │
│  ┌─────────────────────────────────────────────────────────┐│
│  │            Security Layer (CP7)                         ││
│  │  • CORS Protection (origin-based)                      ││
│  │  • Rate Limiting (60 req/min per IP)                   ││
│  │  • Trusted Host Validation                             ││
│  │  • Request Correlation IDs                             ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │          Application Layer                              ││
│  │  • FastAPI with Pydantic validation                    ││
│  │  • Six-pillar scoring engine                           ││
│  │  • Risk penalties & guardrails                         ││
│  │  • Connection pooling (2-20 connections)               ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              PostgreSQL Database                            │
│  • Score storage with time-series data                     │
│  • Alembic migrations for schema management                │
│  • Connection pooling and retry logic                      │
│  • Automated backups and point-in-time recovery           │
└─────────────────────────────────────────────────────────────┘
```

### Service Components

1. **API Service** (`greyoak-api`):
   - FastAPI application with CP7 security hardening
   - Uvicorn ASGI server with production configuration
   - Health checks for container orchestration

2. **Database Service** (`greyoak-db`):
   - PostgreSQL 15 with optimized configuration
   - Persistent volume for data storage
   - Automated health monitoring

3. **Admin Interface** (`greyoak-adminer`, dev only):
   - Web-based database administration
   - Available only in development profile

## Environment Setup

### 1. Clone and Prepare Repository

```bash
# Clone repository
git clone <repository-url>
cd greyoak-score-engine

# Navigate to backend directory
cd backend

# Create production environment file
cp .env.example .env.production
```

### 2. Configure Environment Variables

Edit `.env.production` with your production settings:

```bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Production Environment Configuration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Database Configuration (CRITICAL - Use strong credentials)
PGUSER=greyoak_prod
PGPASSWORD=<STRONG_RANDOM_PASSWORD>
PGDATABASE=greyoak_scores_prod
PGHOST=db
PGPORT=5432

# Alternative: Single DATABASE_URL (preferred for cloud deployments)
# DATABASE_URL=postgresql://greyoak_prod:password@db:5432/greyoak_scores_prod

# Application Configuration
APP_ENV=production
MODE=production
LOG_LEVEL=INFO

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Security Configuration (CP7) - CRITICAL FOR PRODUCTION
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
RATE_LIMIT=60
TRUSTED_HOSTS=yourdomain.com,app.yourdomain.com

# Database Connection Pool Configuration
DB_POOL_MIN_CONN=5
DB_POOL_MAX_CONN=50
DB_POOL_TIMEOUT=30

# Performance Configuration
API_TIMEOUT=30
WORKERS=4

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30s
HEALTH_CHECK_TIMEOUT=10s
HEALTH_CHECK_RETRIES=3
HEALTH_CHECK_START_PERIOD=30s
```

### 3. Security Configuration

**Generate Strong Passwords:**

```bash
# Generate secure database password
openssl rand -base64 32

# Generate application secrets (if needed)
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Configure CORS Origins:**

```bash
# Production domains only - NEVER use wildcards in production
CORS_ORIGINS=https://api.yourdomain.com,https://app.yourdomain.com

# For multiple environments
CORS_ORIGINS=https://api.yourdomain.com,https://staging.yourdomain.com
```

**Configure Trusted Hosts:**

```bash
# Limit Host header values to prevent Host header injection
TRUSTED_HOSTS=api.yourdomain.com,yourdomain.com
```

## Docker Deployment

### 1. Production Deployment

**Deploy with Production Configuration:**

```bash
# Build and start services
docker-compose -f docker-compose.yml --env-file .env.production up -d

# Verify services are running
docker-compose ps

# Check service logs
docker-compose logs -f api
docker-compose logs -f db
```

**Service Health Verification:**

```bash
# Check API health
curl -f http://localhost:8000/health

# Check application health (with database)
curl -f http://localhost:8000/api/v1/health

# Verify rate limiting headers
curl -I http://localhost:8000/api/v1/health
```

### 2. Development Deployment

**Deploy with Development Tools:**

```bash
# Start with development profile (includes Adminer)
docker-compose --profile dev --env-file .env up -d

# Access services
# API: http://localhost:8000
# Adminer: http://localhost:8080
# Database: localhost:5432
```

### 3. Scaling and Load Balancing

**Horizontal Scaling:**

```bash
# Scale API service to multiple instances
docker-compose up -d --scale api=3

# Use with load balancer configuration
# Update your Nginx/HAProxy to distribute load across instances
```

**Load Balancer Configuration (Nginx Example):**

```nginx
upstream greyoak_api {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    # SSL configuration
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    location / {
        proxy_pass http://greyoak_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://greyoak_api/health;
        access_log off;
    }
}
```

## Database Configuration

### 1. Database Initialization

**Apply Initial Migrations:**

```bash
# Initialize database schema
docker-compose exec api alembic upgrade head

# Verify migration status
docker-compose exec api alembic current

# Check database schema
docker-compose exec db psql -U greyoak_prod -d greyoak_scores_prod -c "\dt"
```

### 2. Database Optimization

**PostgreSQL Production Configuration:**

Create `postgresql.conf` overrides for production:

```sql
# Memory configuration
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB

# Connection configuration
max_connections = 100
shared_preload_libraries = 'pg_stat_statements'

# Logging configuration
log_statement = 'mod'
log_duration = on
log_min_duration_statement = 1000

# Performance monitoring
track_activities = on
track_counts = on
track_io_timing = on
```

**Database Maintenance:**

```bash
# Analyze tables for query optimization
docker-compose exec db psql -U greyoak_prod -d greyoak_scores_prod -c "ANALYZE;"

# Vacuum for space reclamation
docker-compose exec db psql -U greyoak_prod -d greyoak_scores_prod -c "VACUUM ANALYZE scores;"

# Check database statistics
docker-compose exec db psql -U greyoak_prod -d greyoak_scores_prod -c "
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del 
FROM pg_stat_user_tables WHERE tablename = 'scores';"
```

### 3. Backup and Recovery

**Automated Backup Script:**

```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/backups/greyoak"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="greyoak_scores_${TIMESTAMP}.sql"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create database backup
docker-compose exec -T db pg_dump -U greyoak_prod greyoak_scores_prod > "$BACKUP_DIR/$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_DIR/$BACKUP_FILE"

# Keep only last 30 days of backups
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

**Recovery Procedure:**

```bash
# Stop API service
docker-compose stop api

# Restore database
gunzip -c /backups/greyoak/greyoak_scores_20241008_120000.sql.gz | \
    docker-compose exec -T db psql -U greyoak_prod -d greyoak_scores_prod

# Run migrations to ensure schema is current
docker-compose exec api alembic upgrade head

# Start API service
docker-compose start api
```

## Security Configuration

### 1. CORS Configuration

**Production CORS Setup:**

```bash
# Restrict to specific domains only
CORS_ORIGINS=https://api.yourdomain.com,https://app.yourdomain.com

# Test CORS configuration
curl -H "Origin: https://api.yourdomain.com" \
     -i http://localhost:8000/api/v1/health
```

### 2. Rate Limiting Configuration

**Rate Limit Settings:**

```bash
# Configure rate limits per use case
RATE_LIMIT=60          # API endpoints: 60 requests per minute
# Health endpoints are automatically exempted

# Test rate limiting
for i in {1..65}; do
    curl -s -o /dev/null -w "%{http_code} " "http://localhost:8000/api/v1/health"
done
```

### 3. SSL/TLS Configuration

**SSL Certificate Setup:**

```bash
# Using Let's Encrypt with Certbot
certbot certonly --webroot -w /var/www/html -d api.yourdomain.com

# Or using custom certificates
mkdir -p /etc/ssl/greyoak
cp your-certificate.crt /etc/ssl/greyoak/
cp your-private-key.key /etc/ssl/greyoak/
chmod 600 /etc/ssl/greyoak/your-private-key.key
```

### 4. Network Security

**Firewall Configuration:**

```bash
# Allow only necessary ports
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Restrict database access (if not using Docker networks)
ufw allow from <api-server-ip> to any port 5432
```

## Monitoring & Health Checks

### 1. Health Check Endpoints

The GreyOak Score Engine provides two health check endpoints:

**Infrastructure Health Check:**
```bash
# Basic service availability (fast, no database check)
GET /health

# Response:
{
    "status": "healthy",
    "service": "greyoak-score-api", 
    "version": "1.0.0",
    "timestamp": 1633564800,
    "environment": "production",
    "check_type": "infrastructure"
}
```

**Application Health Check:**
```bash
# Comprehensive health check (includes database connectivity)
GET /api/v1/health

# Response:
{
    "status": "healthy",
    "service": "GreyOak Score API",
    "version": "1.0.0", 
    "timestamp": "2024-10-08T10:30:00Z",
    "components": {
        "database": {
            "status": "healthy",
            "details": "Connection pool: 5/20 connections"
        },
        "api": {
            "status": "healthy",
            "details": "All endpoints operational"
        }
    },
    "stats": {
        "total_scores": 1250,
        "unique_tickers": 150,
        "latest_date": "2024-10-08"
    }
}
```

### 2. Logging Configuration

**Structured JSON Logging:**

```bash
# View API logs
docker-compose logs -f api | jq .

# View error logs specifically
docker-compose logs api 2>&1 | grep ERROR | jq .

# Monitor rate limiting
docker-compose logs api | grep "rate limit" | jq .
```

**Log Aggregation (ELK Stack Example):**

```yaml
# docker-compose.logging.yml
version: "3.9"
services:
  api:
    logging:
      driver: "fluentd"
      options:
        fluentd-address: "localhost:24224"
        tag: "greyoak.api"
```

### 3. Metrics and Monitoring

**Performance Monitoring:**

```bash
# Container resource usage
docker stats greyoak-api greyoak-db

# Database performance
docker-compose exec db psql -U greyoak_prod -d greyoak_scores_prod -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;"
```

**Alerting Configuration (Prometheus Example):**

```yaml
# prometheus-alerts.yml
groups:
- name: greyoak-alerts
  rules:
  - alert: APIHighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 2m
    annotations:
      summary: "High error rate detected"
      
  - alert: DatabaseConnectionFailure
    expr: up{job="greyoak-db"} == 0
    for: 1m
    annotations:
      summary: "Database connection failed"
      
  - alert: HighMemoryUsage
    expr: container_memory_usage_bytes{name="greyoak-api"} > 1073741824
    for: 5m
    annotations:
      summary: "API container using >1GB memory"
```

## Performance Tuning

### 1. Application Performance

**Uvicorn Configuration:**

```bash
# Production uvicorn settings (in Dockerfile)
CMD ["uvicorn", "greyoak_score.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--access-log", \
     "--log-config", "/app/logging.conf"]
```

**Connection Pool Tuning:**

```bash
# Adjust based on load and database capacity
DB_POOL_MIN_CONN=5     # Minimum connections (always available)
DB_POOL_MAX_CONN=50    # Maximum connections (scale with traffic)
DB_POOL_TIMEOUT=30     # Connection timeout (seconds)

# Monitor pool usage
curl -s http://localhost:8000/api/v1/health | jq '.components.database.details'
```

### 2. Database Performance

**Query Optimization:**

```sql
-- Add indexes for common query patterns
CREATE INDEX CONCURRENTLY idx_scores_ticker_date ON scores(ticker, scoring_date DESC);
CREATE INDEX CONCURRENTLY idx_scores_mode_band ON scores(mode, band);
CREATE INDEX CONCURRENTLY idx_scores_created_at ON scores(created_at DESC);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM scores WHERE ticker = 'RELIANCE.NS' ORDER BY scoring_date DESC LIMIT 10;
```

### 3. System-Level Tuning

**Docker Resource Limits:**

```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
          
  db:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 2G
```

## Backup & Recovery

### 1. Backup Strategy

**Daily Automated Backups:**

```bash
# Cron job configuration (/etc/cron.d/greyoak-backup)
0 2 * * * /usr/local/bin/backup_greyoak.sh >> /var/log/greyoak-backup.log 2>&1
0 2 * * 0 /usr/local/bin/backup_greyoak_weekly.sh >> /var/log/greyoak-backup.log 2>&1
```

**Backup Verification:**

```bash
#!/bin/bash
# verify_backup.sh

LATEST_BACKUP=$(ls -t /backups/greyoak/*.gz | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "ERROR: No backup files found"
    exit 1
fi

# Test restore to temporary database
TEMP_DB="greyoak_test_$(date +%s)"
echo "Testing backup: $LATEST_BACKUP"

# Create temporary database and restore
docker-compose exec db createdb -U greyoak_prod $TEMP_DB
gunzip -c $LATEST_BACKUP | docker-compose exec -T db psql -U greyoak_prod -d $TEMP_DB

# Verify data integrity
RECORD_COUNT=$(docker-compose exec db psql -U greyoak_prod -d $TEMP_DB -t -c "SELECT COUNT(*) FROM scores;")

if [ "$RECORD_COUNT" -gt 0 ]; then
    echo "SUCCESS: Backup verified - $RECORD_COUNT records restored"
else
    echo "ERROR: Backup verification failed - no records found"
fi

# Cleanup
docker-compose exec db dropdb -U greyoak_prod $TEMP_DB
```

### 2. Disaster Recovery

**Recovery Procedures:**

```bash
# 1. Stop all services
docker-compose down

# 2. Restore database from backup
docker-compose up -d db
sleep 10

# 3. Create fresh database
docker-compose exec db createdb -U greyoak_prod greyoak_scores_prod

# 4. Restore from backup
gunzip -c /backups/greyoak/latest_backup.sql.gz | \
    docker-compose exec -T db psql -U greyoak_prod -d greyoak_scores_prod

# 5. Apply any pending migrations
docker-compose up -d api
docker-compose exec api alembic upgrade head

# 6. Verify system health
curl -f http://localhost:8000/api/v1/health
```

## Troubleshooting

### Common Issues and Solutions

#### 1. API Service Won't Start

**Symptoms:**
```
greyoak-api container exits immediately
```

**Diagnosis:**
```bash
# Check container logs
docker-compose logs api

# Check environment configuration
docker-compose exec api env | grep -E "(CORS|RATE|DB_)"

# Test configuration syntax
docker-compose config
```

**Solutions:**
```bash
# Fix environment variables
vi .env.production

# Rebuild container if needed
docker-compose build --no-cache api
docker-compose up -d api
```

#### 2. Database Connection Issues

**Symptoms:**
```
❌ Database initialization error: connection refused
API starting in degraded mode
```

**Diagnosis:**
```bash
# Check database container
docker-compose ps db
docker-compose logs db

# Test database connectivity
docker-compose exec db pg_isready -U greyoak_prod

# Check network connectivity
docker-compose exec api ping db
```

**Solutions:**
```bash
# Restart database service
docker-compose restart db

# Check database credentials
docker-compose exec db psql -U greyoak_prod -d greyoak_scores_prod -c "\conninfo"

# Reset database if corrupted
docker-compose down -v  # WARNING: This deletes all data
docker-compose up -d
```

#### 3. Rate Limiting Not Working

**Symptoms:**
```
No X-RateLimit-* headers in responses
Rate limiting bypassed
```

**Diagnosis:**
```bash
# Check rate limit configuration
curl -I http://localhost:8000/api/v1/health | grep -i ratelimit

# Verify middleware configuration
docker-compose logs api | grep "rate limit"
```

**Solutions:**
```bash
# Verify environment variables
echo $RATE_LIMIT

# Check SlowAPI middleware initialization
docker-compose logs api | grep -i "slowapi\|limiter"

# Restart service to reload configuration
docker-compose restart api
```

#### 4. CORS Issues

**Symptoms:**
```
CORS policy error in browser
No Access-Control-Allow-Origin header
```

**Diagnosis:**
```bash
# Test CORS headers
curl -H "Origin: https://yourdomain.com" -I http://localhost:8000/api/v1/health

# Check CORS configuration
echo $CORS_ORIGINS
```

**Solutions:**
```bash
# Update CORS origins in .env
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Restart API service
docker-compose restart api

# Test preflight requests
curl -X OPTIONS -H "Origin: https://yourdomain.com" http://localhost:8000/api/v1/health
```

#### 5. Performance Issues

**Symptoms:**
```
Slow API responses
High CPU/memory usage
Database query timeouts
```

**Diagnosis:**
```bash
# Monitor resource usage
docker stats

# Check database performance
docker-compose exec db psql -U greyoak_prod -d greyoak_scores_prod -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 5;"

# Monitor connection pool
curl -s http://localhost:8000/api/v1/health | jq '.components.database'
```

**Solutions:**
```bash
# Increase connection pool
DB_POOL_MAX_CONN=50

# Add database indexes
docker-compose exec db psql -U greyoak_prod -d greyoak_scores_prod -f optimization.sql

# Scale API instances
docker-compose up -d --scale api=3
```

### Log Analysis

**Key Log Patterns:**

```bash
# Connection pool issues
docker-compose logs api | grep -i "pool\|connection"

# Rate limiting activity
docker-compose logs api | grep -i "rate.*limit"

# Database errors
docker-compose logs api | grep -i "database\|psycopg2"

# Security events
docker-compose logs api | grep -i "cors\|origin\|host"
```

**Performance Monitoring:**

```bash
# API response times
docker-compose logs api | grep -E "HTTP/1\.[01]" | awk '{print $NF}' | sort -n

# Database query analysis
docker-compose exec db psql -U greyoak_prod -d greyoak_scores_prod -c "
SELECT substring(query for 50) as query_preview, 
       calls, 
       total_time/1000 as total_seconds,
       mean_time/1000 as avg_seconds
FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;"
```

## Maintenance

### Regular Maintenance Tasks

#### Daily Tasks

```bash
# Check service health
curl -f http://localhost:8000/health
curl -f http://localhost:8000/api/v1/health

# Monitor resource usage
docker stats --no-stream

# Review error logs
docker-compose logs --since 24h api | grep -i error
```

#### Weekly Tasks

```bash
# Database maintenance
docker-compose exec db psql -U greyoak_prod -d greyoak_scores_prod -c "ANALYZE;"

# Log rotation
journalctl --rotate
journalctl --vacuum-time=7d

# Security updates
docker-compose pull
docker-compose up -d --force-recreate
```

#### Monthly Tasks

```bash
# Full database vacuum
docker-compose exec db psql -U greyoak_prod -d greyoak_scores_prod -c "VACUUM FULL ANALYZE scores;"

# Backup verification
/usr/local/bin/verify_backup.sh

# Performance review
docker-compose exec db psql -U greyoak_prod -d greyoak_scores_prod -f monthly_performance_report.sql

# Update dependencies
docker-compose build --no-cache
```

### Upgrade Procedures

#### Application Upgrades

```bash
# 1. Backup current state
/usr/local/bin/backup_greyoak.sh

# 2. Pull new version
git pull origin main

# 3. Check for migration changes
docker-compose exec api alembic heads

# 4. Stop services
docker-compose down

# 5. Build new images
docker-compose build

# 6. Start services and apply migrations
docker-compose up -d
docker-compose exec api alembic upgrade head

# 7. Verify health
curl -f http://localhost:8000/api/v1/health
```

#### Database Schema Updates

```bash
# Review pending migrations
docker-compose exec api alembic show head

# Apply migrations with monitoring
docker-compose exec api alembic upgrade head

# Verify schema changes
docker-compose exec db psql -U greyoak_prod -d greyoak_scores_prod -c "\d+ scores"
```

## Security Checklist

### Pre-Deployment Security Review

- [ ] **Environment Variables**: All secrets properly configured and not hardcoded
- [ ] **CORS Configuration**: Origins restricted to specific domains (no wildcards)
- [ ] **Rate Limiting**: Enabled and configured appropriately for expected load
- [ ] **Trusted Hosts**: Host header validation configured
- [ ] **SSL/TLS**: Valid certificates installed and properly configured
- [ ] **Database Credentials**: Strong passwords, limited access
- [ ] **Network Security**: Firewall rules properly configured
- [ ] **Container Security**: Running as non-root user, read-only filesystem
- [ ] **Logging**: No sensitive data in logs, proper log rotation
- [ ] **Backup Security**: Backups encrypted and access controlled

### Ongoing Security Monitoring

- [ ] **Regular Updates**: Keep Docker images and dependencies updated
- [ ] **Log Monitoring**: Monitor for security events and anomalies
- [ ] **Access Review**: Regular review of database and system access
- [ ] **Certificate Management**: Monitor SSL certificate expiration
- [ ] **Security Scanning**: Regular vulnerability scans of containers
- [ ] **Incident Response**: Have procedures for security incidents

## Support and Resources

### Documentation Links

- [API Usage Guide](API_USAGE.md) - Comprehensive API documentation
- [Database Migrations](DB_MIGRATIONS.md) - Alembic migration management
- [Architecture Overview](architecture.md) - System design and components
- [Configuration Guide](configuration_guide.md) - Detailed configuration options

### Monitoring Resources

- Health Check Endpoints: `/health` (infra) and `/api/v1/health` (app)
- OpenAPI Documentation: `/docs` (Swagger UI) and `/redoc`
- Database Admin: Adminer (development only)

### Contact Information

- **Technical Support**: Configure based on your organization
- **Emergency Contacts**: Include on-call procedures
- **Documentation Updates**: Process for updating deployment procedures

---

**Last Updated**: CP7 Implementation - October 2024
**Version**: 1.0.0 (Production Ready)

This deployment guide covers all aspects of production deployment for the GreyOak Score Engine with CP7 security and hardening features. Follow the procedures carefully and maintain regular backups and monitoring for optimal system reliability.