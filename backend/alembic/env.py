"""
Alembic Environment Configuration for GreyOak Score Engine

This module configures Alembic migrations for the GreyOak Score database schema.
It dynamically constructs the DATABASE_URL from environment variables and provides
both offline and online migration capabilities.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, create_engine, MetaData, Table, Column, String, Float, DateTime, Enum

from alembic import context

# Add the project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Define the target metadata for GreyOak Score tables
# We define the schema here since we don't use SQLAlchemy ORM models
target_metadata = MetaData()

# Define the scores table schema
scores_table = Table(
    'scores',
    target_metadata,
    Column('ticker', String(20), primary_key=True),
    Column('scoring_date', DateTime, primary_key=True),
    Column('mode', String(20), primary_key=True),
    Column('f_score', Float),
    Column('t_score', Float),
    Column('r_score', Float),
    Column('o_score', Float),
    Column('q_score', Float),
    Column('s_score', Float),
    Column('weighted_score', Float),
    Column('risk_penalty', Float),
    Column('final_score', Float),
    Column('band', Enum('Strong Buy', 'Buy', 'Hold', 'Avoid', name='band_enum')),
    Column('guardrails', String(500)),
    Column('as_of', DateTime),
    Column('f_z', Float),
    Column('t_z', Float),
    Column('r_z', Float),
    Column('o_z', Float),
    Column('q_z', Float),
    Column('s_z', Float),  # NOTE: This is s_z, not sector_z as per user instructions
    Column('created_at', DateTime),
    Column('updated_at', DateTime),
)


def get_database_url() -> str:
    """
    Construct DATABASE_URL from environment variables.
    
    Priority:
    1. DATABASE_URL env var (if set)
    2. Individual PG* environment variables
    
    Returns:
        str: Complete PostgreSQL connection URL
    """
    # Check for direct DATABASE_URL first
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url
    
    # Construct from individual environment variables
    user = os.getenv('PGUSER', 'greyoak')
    password = os.getenv('PGPASSWORD', 'greyoak_pw')
    host = os.getenv('PGHOST', 'db')
    port = os.getenv('PGPORT', '5432')
    database = os.getenv('PGDATABASE', 'greyoak_scores')
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Override the sqlalchemy.url in configuration
    configuration = config.get_section(config.config_ini_section, {})
    configuration['sqlalchemy.url'] = get_database_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
