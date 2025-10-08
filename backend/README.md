# GreyOak Score Engine

**Production-Ready Stock Scoring System for Indian Equities (CP7)**

[![Production Status](https://img.shields.io/badge/Status-Production%20Ready-green)]()
[![API Version](https://img.shields.io/badge/API-v1.0.0-blue)]()
[![Security](https://img.shields.io/badge/Security-CP7%20Hardened-brightgreen)]()
[![Test Coverage](https://img.shields.io/badge/Coverage->80%25-success)]()

**Version**: 1.0.0 | **Status**: CP7 Complete (Production Ready) | **Last Updated**: October 2024

---

## Overview

GreyOak Score Engine is a **production-ready, deterministic stock scoring system** for Indian equities (NSE/BSE) that generates comprehensive **0-100 scores** and **investment bands** (Strong Buy/Buy/Hold/Avoid) across **dual modes** for different investment horizons.

### 🎯 **Key Features (CP7)**

#### **Core Scoring System**
- ✅ **Six-Pillar Analysis**: Fundamentals (F), Technicals (T), Relative Strength (R), Ownership (O), Quality (Q), Sector Momentum (S)
- ✅ **Dual Investment Modes**: Trader (1-6 months) & Investor (12-24 months) with different pillar weights
- ✅ **Risk Management**: Multi-factor risk penalty system with sector-specific caps
- ✅ **Sequential Guardrails**: Six hard-coded guardrails in specific order for downside protection
- ✅ **Sector-Aware Normalization**: Z-score and ECDF normalization with sector groups
- ✅ **Deterministic Output**: Complete audit trail with configuration hashing

#### **Production Infrastructure (CP7)**
- ✅ **Security Hardening**: CORS protection, rate limiting (60 req/min), trusted hosts, correlation IDs
- ✅ **Database Management**: PostgreSQL with connection pooling (2-20 connections), Alembic migrations
- ✅ **API Excellence**: FastAPI with Pydantic validation, OpenAPI docs, comprehensive error handling
- ✅ **Container Security**: Docker multi-stage builds, non-root user, read-only filesystem
- ✅ **Health Monitoring**: Dual health endpoints, structured logging, performance metrics
- ✅ **Configuration Management**: Environment-based config, zero hardcoded values

#### **Reliability & Performance**
- ✅ **High Availability**: Connection pooling, retry logic, graceful degradation
- ✅ **Comprehensive Testing**: >80% test coverage, unit/integration/performance tests
- ✅ **Production Documentation**: Complete deployment, API usage, and troubleshooting guides
- ✅ **Monitoring Ready**: Health checks, metrics, alerting endpoints

---

## 🚀 Quick Start

### Prerequisites

**System Requirements:**
- **Docker & Docker Compose**: 20.10+ and 2.0+
- **Python**: 3.10+ (for local development)
- **Memory**: 2GB RAM minimum (4GB recommended)
- **Storage**: 10GB available space

### Production Deployment

```bash
# 1. Clone repository and navigate to backend
git clone <repository-url> && cd greyoak-score-engine/backend

# 2. Configure production environment
cp .env.example .env.production
# Edit .env.production with your settings (CORS_ORIGINS, database credentials, etc.)

# 3. Deploy with Docker Compose
docker-compose --env-file .env.production up -d

# 4. Apply database migrations
docker-compose exec api alembic upgrade head

# 5. Verify deployment
curl -f http://localhost:8000/health
curl -f http://localhost:8000/api/v1/health
```

### Development Setup

```bash
# 1. Install dependencies and pre-commit hooks
make setup

# 2. Start development services (with Adminer)
docker-compose --profile dev up -d

# 3. Run tests with coverage
make test
```

### Access Services

| Service | URL | Description |
|---------|-----|-------------|
| **API** | http://localhost:8000 | Main scoring API |
| **API Docs** | http://localhost:8000/docs | Interactive Swagger UI |
| **ReDoc** | http://localhost:8000/redoc | Clean API documentation |
| **Health Check** | http://localhost:8000/health | Infrastructure health |
| **App Health** | http://localhost:8000/api/v1/health | Application health |
| **Adminer** | http://localhost:8080 | Database UI (dev only) |

### Quick API Test

```bash
# Test API health
curl -s http://localhost:8000/api/v1/health | jq .

# Calculate a score (example with mock data)
curl -X POST "http://localhost:8000/api/v1/calculate" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "RELIANCE.NS",
    "date": "2024-10-08",
    "mode": "Investor"
  }' | jq .
```

---

## 🏗️ Architecture & Structure

### System Architecture (CP7)

```
┌─────────────────────────────────────────────────────────────┐
│                 Load Balancer / Proxy                       │
│              (Nginx/HAProxy + SSL/TLS)                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              GreyOak Score API (CP7)                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │         Security Layer (Production Hardened)            ││
│  │  • CORS Protection (origin-based)                      ││
│  │  • Rate Limiting (60 req/min per IP)                   ││
│  │  • Request Correlation IDs                             ││
│  │  • Trusted Host Validation                             ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Application Layer                          ││
│  │  • FastAPI + Pydantic Validation                       ││
│  │  • Six-Pillar Scoring Engine                           ││
│  │  • Risk Penalties & Sequential Guardrails              ││
│  │  • Connection Pool (2-20 connections)                  ││
│  │  • Health Monitoring & Metrics                         ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│            PostgreSQL Database (15+)                        │
│  • Score storage with audit trail                          │
│  • Alembic migrations for schema management                │
│  • Connection pooling with retry logic                     │
│  • Performance optimization & indexing                     │
└─────────────────────────────────────────────────────────────┘
```

### Project Structure

```
backend/
├── greyoak_score/              # 📦 Main Package
│   ├── __init__.py
│   ├── version.py
│   ├── core/                   # 🧠 Core Scoring Engine
│   │   ├── config_manager.py   #   Configuration management
│   │   ├── data_hygiene.py     #   Data cleaning & validation
│   │   ├── normalization.py    #   Sector normalization (z-score/ECDF)
│   │   ├── risk_penalty.py     #   Risk penalty calculations
│   │   ├── guardrails.py       #   Sequential guardrail system
│   │   └── scoring.py          #   Final scoring orchestration
│   ├── pillars/                # 📊 Six Pillar Calculators
│   │   ├── base.py             #   Base pillar class
│   │   ├── fundamentals.py     #   (F) Financial metrics & ratios
│   │   ├── technicals.py       #   (T) Technical indicators
│   │   ├── relative_strength.py#   (R) Momentum & performance
│   │   ├── ownership.py        #   (O) Institutional ownership
│   │   ├── quality.py          #   (Q) Financial quality metrics
│   │   └── sector_momentum.py  #   (S) Sector-relative performance
│   ├── data/                   # 💾 Data Layer (CP7)
│   │   ├── models.py           #   Pydantic data models
│   │   ├── ingestion.py        #   Data loading & processing
│   │   ├── persistence.py      #   PostgreSQL with connection pooling
│   │   └── indicators.py       #   Technical indicator calculations
│   ├── api/                    # 🌐 FastAPI Layer (CP7)
│   │   ├── main.py             #   Application with security hardening
│   │   ├── routes.py           #   API endpoints with rate limiting
│   │   ├── schemas.py          #   Request/response validation
│   │   └── dependencies.py     #   Dependency injection
│   └── utils/                  # 🔧 Utilities
│       ├── constants.py        #   Application constants
│       ├── logger.py           #   Structured logging
│       └── validators.py       #   Custom validation logic
├── configs/                    # ⚙️ Configuration Files
│   ├── score.yaml              #   Pillar weights, bands, thresholds
│   ├── sector_map.yaml         #   Sector mapping & groups
│   ├── freshness.yaml          #   Data freshness requirements
│   ├── data_sources.yaml       #   Data vendor configuration
│   └── barriers.yaml           #   Market barrier definitions
├── data/                       # 📈 Sample Data
│   ├── prices.csv              #   Historical price data
│   ├── fundamentals.csv        #   Financial statement data
│   ├── ownership.csv           #   Institutional holdings
│   └── sector_map.csv          #   Sector classifications
├── tests/                      # 🧪 Test Suite (>80% Coverage)
│   ├── conftest.py             #   Test configuration
│   ├── fixtures/               #   Test data & golden examples
│   ├── unit/                   #   Unit tests (individual modules)
│   ├── integration/            #   Integration tests (full pipeline)
│   ├── validation/             #   Validation tests (business rules)
│   ├── api/                    #   API endpoint tests
│   └── performance/            #   Performance & load tests
├── docs/                       # 📚 Documentation (CP7)
│   ├── architecture.md         #   System architecture overview
│   ├── api_reference.md        #   API documentation
│   ├── configuration_guide.md  #   Configuration management
│   ├── runbook.md             #   Operations runbook
│   ├── DEPLOYMENT.md          #   Production deployment guide
│   ├── API_USAGE.md           #   Comprehensive API usage
│   └── DB_MIGRATIONS.md       #   Database migration procedures
├── scripts/                    # 🔨 Utility Scripts
│   ├── generate_sample_data.py #   Sample data generation
│   ├── run_scoring.py          #   Scoring execution
│   ├── validate_config.py      #   Configuration validation
│   └── init_db.py              #   Database initialization
├── alembic/                    # 🗃️ Database Migrations (CP7)
│   ├── versions/               #   Migration files
│   ├── env.py                  #   Alembic environment
│   └── script.py.mako          #   Migration template
├── .env.example               # 🔐 Environment template
├── alembic.ini                # ⚙️ Alembic configuration
├── docker-compose.yml         # 🐳 Container orchestration
├── Dockerfile                 # 📦 Container definition
├── requirements.txt           # 📋 Python dependencies
├── requirements-dev.txt       # 🔧 Development dependencies
├── pytest.ini                # 🧪 Test configuration
├── logging.conf              # 📝 Logging configuration
├── Makefile                  # 🛠️ Development commands
└── README.md                 # 📖 This file
```

### Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Runtime** | Python | 3.10+ | Core application language |
| **API Framework** | FastAPI | 0.104+ | REST API with automatic docs |
| **Database** | PostgreSQL | 15+ | Time-series score storage |
| **Validation** | Pydantic | 2.12+ | Data validation & serialization |
| **Data Processing** | Pandas/NumPy | Latest | Numerical computations |
| **Statistics** | SciPy | Latest | Statistical functions |
| **Configuration** | PyYAML | Latest | YAML configuration files |
| **Testing** | Pytest | Latest | Test framework with coverage |
| **Migration** | Alembic | 1.13+ | Database schema management |
| **Security** | SlowAPI | 0.1.9+ | Rate limiting middleware |
| **Containers** | Docker | 20.10+ | Application containerization |
| **Orchestration** | Docker Compose | 2.0+ | Multi-service deployment |

---

## Configuration

All parameters are externalized in YAML files (no hard-coded values):

- **score.yaml**: Pillar weights, RP parameters, guardrail thresholds, band cutoffs
- **sector_map.yaml**: Ticker-to-sector mapping, sector group definitions
- **freshness.yaml**: Data freshness SLOs, confidence weights
- **data_sources.yaml**: Vendor configuration (future use)

Validate configs after editing:

```bash
make validate-config
```

---

## Testing

### Test Coverage Target

**>80% coverage** (enforced by pytest)

### Test Categories

- **Unit tests**: Each module independently (`tests/unit/`)
- **Integration tests**: Full pipeline (`tests/integration/`)
- **Validation tests**: Score ranges, weight sums, determinism (`tests/validation/`)
- **Golden test**: RELIANCE worked example from spec Section 9

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Golden test (RELIANCE example)
pytest tests/integration/test_reliance_golden.py -v
```

---

## Code Quality

### Pre-commit Hooks (ENFORCED)

All commits are automatically checked for:
- ✅ **Black**: Code formatting
- ✅ **Ruff**: Linting (PEP 8, imports, complexity)
- ✅ **Mypy**: Type checking (strict mode)

### Manual Checks

```bash
# Run all linters
make lint

# Auto-format code
make fmt
```

---

## Development

### Adding New Features

1. Create feature branch
2. Write tests first (TDD)
3. Implement feature
4. Run `make lint` and `make test`
5. Commit (pre-commit hooks will run)
6. Submit PR

### Variable Naming Convention

**MUST match spec terminology exactly:**

✅ **Correct**: `sigma20`, `MTV`, `S_z`, `Score_preGuard`, `hi_20d`, `ret_21d`

❌ **Wrong**: `sigma_20`, `mtv`, `s_z`, `score_pre_guard`, `hi20d`, `ret21d`

**Reason**: Grep-ability, spec traceability, debugging clarity

### Logging Levels

- **INFO**: Module start/end, API calls, score calculations
- **DEBUG**: Pillar values, RP components, guardrail checks, intermediate calculations
- **ERROR**: Exceptions with full traceback

---

## API Endpoints

### `POST /score/run`

Trigger scoring for a specific date/mode.

**Query Parameters:**
- `date`: Trading date (YYYY-MM-DD)
- `mode`: Scoring mode (`Trader` or `Investor`)

### `GET /score/{ticker}/{date}/{mode}`

Retrieve score for a specific stock.

### `GET /score/{date}/{mode}`

Retrieve all scores for a date/mode.

### `GET /health`

System health check.

**Full API documentation**: http://localhost:8000/docs

---

## Database Schema

### `scores` Table

```sql
CREATE TABLE scores (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20),
    date DATE,
    mode VARCHAR(10),
    score NUMERIC(5,2),
    band VARCHAR(20),
    f_pillar NUMERIC(5,2),
    t_pillar NUMERIC(5,2),
    r_pillar NUMERIC(5,2),
    o_pillar NUMERIC(5,2),
    q_pillar NUMERIC(5,2),
    s_pillar NUMERIC(5,2),
    risk_penalty NUMERIC(5,2),
    guardrail_flags JSONB,
    confidence NUMERIC(4,3),
    s_z NUMERIC(6,3),  -- Sector momentum z-score
    as_of TIMESTAMP WITH TIME ZONE,
    config_hash VARCHAR(64),
    UNIQUE(ticker, date, mode)
);
```

---

## Troubleshooting

### Services not starting?

```bash
# Check service status
docker-compose ps

# View logs
make logs

# Restart services
make stop
make run
```

### Tests failing?

```bash
# Check coverage report
pytest --cov-report=html
open htmlcov/index.html

# Run specific test
pytest tests/unit/test_config_manager.py::TestConfigManagerLoading::test_load_all_configs -v
```

### Configuration errors?

```bash
# Validate configs
make validate-config

# Check config hash
python -c "from greyoak_score.core.config_manager import ConfigManager; from pathlib import Path; print(ConfigManager(Path('configs')).config_hash)"
```

---

## Next Steps (Phase 2)

- [ ] Data ingestion (CSV readers)
- [ ] Data hygiene (winsorization, imputation)
- [ ] Sector normalization (z-scores, ECDF)
- [ ] Six pillar calculations
- [ ] Risk penalty & guardrails
- [ ] Final scoring & banding
- [ ] API implementation
- [ ] RELIANCE golden test

---

## License

Proprietary - GreyOak Capital Intelligence

---

## Support

For issues or questions, please contact the development team.
