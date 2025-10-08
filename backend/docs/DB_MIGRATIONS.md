# Database Migrations - GreyOak Score Engine

This document explains database migration management using Alembic for the GreyOak Score Engine PostgreSQL database.

## Overview

The GreyOak Score Engine uses [Alembic](https://alembic.sqlalchemy.org/) for database schema versioning and migration management. Alembic provides:

- **Version Control**: Track database schema changes over time
- **Forward Migrations**: Apply schema changes to upgrade database
- **Backward Migrations**: Rollback schema changes if needed
- **Environment Configuration**: Support for development, staging, and production environments
- **Autogeneration**: Generate migrations from model changes (when using SQLAlchemy ORM)

## Database Schema

### Primary Table: `scores`

The main table stores GreyOak score calculations with the following structure:

```sql
CREATE TABLE scores (
    ticker VARCHAR(20) NOT NULL,
    scoring_date TIMESTAMP NOT NULL,
    mode VARCHAR(20) NOT NULL,
    f_score FLOAT,
    t_score FLOAT,
    r_score FLOAT,
    o_score FLOAT,
    q_score FLOAT,
    s_score FLOAT,
    weighted_score FLOAT,
    risk_penalty FLOAT,
    final_score FLOAT,
    band ENUM('Strong Buy', 'Buy', 'Hold', 'Avoid'),
    guardrails VARCHAR(500),
    as_of TIMESTAMP,
    f_z FLOAT,
    t_z FLOAT,
    r_z FLOAT,
    o_z FLOAT,
    q_z FLOAT,
    s_z FLOAT,  -- Note: Column name is s_z, not sector_z
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (ticker, scoring_date, mode)
);
```

### Indexes

Performance-optimized indexes are created for common query patterns:

```sql
CREATE INDEX idx_scores_ticker ON scores(ticker);
CREATE INDEX idx_scores_band ON scores(band);
CREATE INDEX idx_scores_scoring_date ON scores(scoring_date);
CREATE INDEX idx_scores_mode ON scores(mode);
```

### Enum Type

The `band_enum` type defines valid investment band values:

```sql
CREATE TYPE band_enum AS ENUM ('Strong Buy', 'Buy', 'Hold', 'Avoid');
```

## Configuration

### Environment Variables

Alembic reads database configuration from environment variables (in priority order):

1. **DATABASE_URL** (single connection string):
   ```bash
   DATABASE_URL=postgresql://greyoak:password@db:5432/greyoak_scores
   ```

2. **Individual PG* variables** (fallback):
   ```bash
   PGUSER=greyoak
   PGPASSWORD=your_secure_password
   PGHOST=db
   PGPORT=5432
   PGDATABASE=greyoak_scores
   ```

### Alembic Configuration Files

- **`alembic.ini`**: Main configuration file with logging and migration settings
- **`alembic/env.py`**: Environment setup script with dynamic DATABASE_URL construction
- **`alembic/script.py.mako`**: Template for generating migration files

## Common Migration Commands

### Initialize Alembic (Already Done)

```bash
cd /app/backend
alembic init alembic
```

### Check Current Database Version

```bash
alembic current
```

### View Migration History

```bash
alembic history --verbose
```

### Show Pending Migrations

```bash
alembic show head
```

### Apply All Pending Migrations

```bash
alembic upgrade head
```

### Apply Specific Migration

```bash
alembic upgrade <revision_id>
```

### Rollback to Previous Version

```bash
alembic downgrade -1
```

### Rollback to Specific Version

```bash
alembic downgrade <revision_id>
```

### Create New Migration (Manual)

```bash
alembic revision -m "Description of changes"
```

### Generate Migration from Model Changes (Auto)

```bash
alembic revision --autogenerate -m "Description of changes"
```
*Note: Autogenerate requires SQLAlchemy ORM models. The GreyOak engine uses raw SQL.*

## Docker Integration

### Development Environment

Migrations are automatically applied during container startup:

```bash
docker-compose --profile dev up -d
```

The API container runs migrations before starting the application:

```bash
alembic upgrade head && uvicorn greyoak_score.api.main:app --host 0.0.0.0 --port 8000
```

### Production Environment

```bash
docker-compose up -d
```

### Manual Migration in Docker

```bash
# Access the API container
docker exec -it greyoak-api bash

# Run migrations manually
alembic upgrade head

# Check current version
alembic current
```

## Migration Workflow

### 1. Schema Changes

When making database schema changes:

1. **Create Migration File**:
   ```bash
   alembic revision -m "Add new column to scores table"
   ```

2. **Edit Migration File**: Add upgrade/downgrade logic in the generated file:
   ```python
   def upgrade() -> None:
       op.add_column('scores', sa.Column('new_field', sa.String(100)))

   def downgrade() -> None:
       op.drop_column('scores', 'new_field')
   ```

3. **Test Migration**: 
   ```bash
   # Apply migration
   alembic upgrade head
   
   # Test rollback
   alembic downgrade -1
   
   # Re-apply for production
   alembic upgrade head
   ```

### 2. Deployment Process

For production deployments:

1. **Backup Database**: Always backup before applying migrations
2. **Test in Staging**: Apply migrations in staging environment first
3. **Apply to Production**: Use Docker deployment with automatic migration
4. **Verify Schema**: Confirm migrations applied correctly
5. **Monitor Application**: Ensure application works with new schema

## Migration Files

### Current Migrations

- **`183eb85141bf_initial_schema_with_scores_table.py`**: Initial database schema with scores table, indexes, and enum types

### File Structure

```
backend/
├── alembic/
│   ├── versions/
│   │   └── 183eb85141bf_initial_schema_with_scores_table.py
│   ├── env.py          # Environment configuration
│   ├── README          # Alembic documentation
│   └── script.py.mako  # Migration template
├── alembic.ini         # Alembic configuration
└── greyoak_score/
    └── data/
        └── persistence.py  # Database access layer
```

## Troubleshooting

### Common Issues

#### 1. Connection Errors

```bash
# Error: could not translate host name "db" to address
# Solution: Ensure PostgreSQL container is running
docker-compose up -d db

# Or use localhost for local development
PGHOST=localhost alembic current
```

#### 2. Permission Errors

```bash
# Error: permission denied for schema public
# Solution: Check database user permissions
docker exec -it greyoak-db psql -U greyoak -d greyoak_scores -c "\du"
```

#### 3. Migration Conflicts

```bash
# Error: Multiple head revisions
# Solution: Merge migrations or resolve conflicts
alembic merge -m "merge multiple heads" <rev1> <rev2>
```

#### 4. Schema Out of Sync

```bash
# Error: Database schema doesn't match migrations
# Solution: Create migration to match current state
alembic revision --autogenerate -m "Sync database with current state"
```

### Verification Commands

Check database connectivity:
```bash
# From host
psql postgresql://greyoak:password@localhost:5432/greyoak_scores -c "SELECT 1"

# From container
docker exec greyoak-db psql -U greyoak -d greyoak_scores -c "SELECT COUNT(*) FROM scores"
```

Verify table structure:
```bash
docker exec greyoak-db psql -U greyoak -d greyoak_scores -c "\d scores"
```

Check migration status:
```bash
docker exec greyoak-api alembic current
docker exec greyoak-api alembic history
```

## Best Practices

### Migration Development

1. **Always Test Migrations**: Test both upgrade and downgrade operations
2. **Use Descriptive Names**: Migration messages should clearly describe changes
3. **Small, Atomic Changes**: Keep migrations focused and reversible
4. **Backup Before Production**: Always backup production database before migrations
5. **Review Generated SQL**: Check generated SQL before applying to production

### Environment Management

1. **Separate Environments**: Use different databases for development/staging/production
2. **Environment Variables**: Never hardcode database credentials
3. **Connection Pooling**: Use connection pooling in production (already implemented)
4. **Health Checks**: Monitor database connectivity and migration status

### Performance Considerations

1. **Large Table Migrations**: Plan for downtime when modifying large tables
2. **Index Creation**: Create indexes concurrently when possible
3. **Data Migration**: Separate data migrations from schema migrations
4. **Lock Management**: Understand table locks during migrations

## Security Notes

1. **Credential Management**: Use secure passwords and rotate regularly
2. **Network Security**: Restrict database access to application containers only
3. **Backup Security**: Encrypt and secure database backups
4. **Migration Auditing**: Track who applies migrations and when

## Related Documentation

- [API Usage Guide](API_USAGE.md) - Database integration with FastAPI
- [Deployment Guide](DEPLOYMENT.md) - Production deployment with migrations
- [Architecture Overview](architecture.md) - System architecture and data flow
- [Configuration Guide](configuration_guide.md) - Application configuration

For more information on Alembic features and advanced usage, see the [official Alembic documentation](https://alembic.sqlalchemy.org/).