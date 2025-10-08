# GreyOak Score Engine

**Deterministic, sector-aware stock scoring engine for NSE/BSE equities**

Version: 1.0.0 | Status: Phase 1 (CP1 Complete)

---

## Overview

GreyOak Score Engine produces daily **0-100 scores** and **investment bands** (Strong Buy/Buy/Hold/Avoid) for Indian equities across **Short Term (Trader)** and **Long Term (Investor)** modes.

**Key Features:**
- ✅ Six-pillar scoring system (F, T, R, O, Q, S)
- ✅ Sector-aware normalization
- ✅ Risk penalty system
- ✅ Sequential guardrails
- ✅ Configuration-driven (zero hard-coded values)
- ✅ Deterministic output (audit trail)
- ✅ PostgreSQL persistence
- ✅ FastAPI endpoints

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.10+
- Make (optional, for convenience commands)

### Setup

```bash
# 1. Install dependencies and pre-commit hooks
make setup

# 2. Start services (API + PostgreSQL + Adminer)
make run

# Or run in background:
make run-bg
```

### Access Services

- **API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **Adminer (DB UI)**: http://localhost:8080
  - System: PostgreSQL
  - Server: `db`
  - Username: `greyoak`
  - Password: `greyoak_pw`
  - Database: `greyoak_scores`

### Run Tests

```bash
# Run all tests with coverage
make test

# Run linters (black, ruff, mypy)
make lint

# Format code
make fmt

# Validate configuration files
make validate-config
```

---

## Project Structure

```
/app/backend/
├── greyoak_score/          # Main package
│   ├── core/               # Core scoring engine
│   │   ├── config_manager.py
│   │   ├── data_hygiene.py
│   │   ├── normalization.py
│   │   ├── risk_penalty.py
│   │   ├── guardrails.py
│   │   └── scoring.py
│   ├── pillars/            # Six pillar calculators
│   │   ├── fundamentals.py
│   │   ├── technicals.py
│   │   ├── relative_strength.py
│   │   ├── ownership.py
│   │   ├── quality.py
│   │   └── sector_momentum.py
│   ├── data/               # Data layer
│   │   ├── models.py
│   │   ├── ingestion.py
│   │   └── persistence.py
│   ├── api/                # FastAPI endpoints
│   │   ├── main.py
│   │   └── routes.py
│   └── utils/              # Utilities
│       ├── constants.py
│       ├── logger.py
│       └── validators.py
├── configs/                # YAML configurations
│   ├── score.yaml
│   ├── sector_map.yaml
│   ├── freshness.yaml
│   └── data_sources.yaml
├── data/                   # Sample CSV data
├── tests/                  # Test suite
│   ├── unit/
│   ├── integration/
│   ├── validation/
│   └── api/
├── scripts/                # Utility scripts
│   ├── generate_sample_data.py
│   └── validate_config.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── Makefile
└── README.md
```

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
