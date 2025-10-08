"""
PostgreSQL Persistence Layer for GreyOak Scores.

This module provides database operations for saving and retrieving 
GreyOak Score results with proper transaction handling and security.

Key Features:
- UPSERT functionality (ON CONFLICT) for idempotent saves
- Parameterized queries for SQL injection prevention
- Connection pooling and transaction management
- Query methods: by ticker, by band, with date filters
- Proper error handling and logging
"""

import os
import json
from typing import List, Optional, Dict, Any
from datetime import date, datetime
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from contextlib import contextmanager
import logging

from greyoak_score.data.models import ScoreOutput, PillarScores
from greyoak_score.utils.logger import get_logger
import greyoak_score

logger = get_logger(__name__)


class ScoreDatabase:
    """
    PostgreSQL persistence layer for GreyOak Scores.
    
    Manages database connections and provides CRUD operations for score data.
    Uses the schema defined in db_init/01_schema.sql with proper constraints
    and indexes for optimal performance.
    
    Database Schema:
    - scores table with s_z column (not sector_z) 
    - Unique constraint on (ticker, date, mode)
    - Indexes on ticker, date, band for query optimization
    - JSON storage for guardrail_flags array
    - Audit trail columns for determinism tracking
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database connection manager.
        
        Args:
            database_url: PostgreSQL connection string. If None, uses environment variables.
        """
        if database_url:
            self.database_url = database_url
        else:
            # Build connection string from environment variables
            pguser = os.getenv('PGUSER', 'greyoak')
            pgpassword = os.getenv('PGPASSWORD', 'greyoak_pw_change_in_production')
            pghost = os.getenv('PGHOST', 'db')  # Docker service name
            pgport = os.getenv('PGPORT', '5432')
            pgdatabase = os.getenv('PGDATABASE', 'greyoak_scores')
            
            self.database_url = f"postgresql://{pguser}:{pgpassword}@{pghost}:{pgport}/{pgdatabase}"
        
        logger.info(f"Database initialized with host: {self._get_safe_connection_info()}")
    
    def _get_safe_connection_info(self) -> str:
        """Get connection info without exposing credentials."""
        try:
            parts = self.database_url.split('@')[1]  # Everything after @
            return f"postgresql://***:***@{parts}"
        except Exception:
            return "postgresql://***:***@***"
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections with proper cleanup.
        
        Yields:
            psycopg2.connection: Database connection with autocommit disabled
            
        Raises:
            psycopg2.Error: If connection fails
        """
        conn = None
        try:
            conn = psycopg2.connect(self.database_url)
            yield conn
        except psycopg2.Error as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def test_connection(self) -> bool:
        """
        Test database connectivity.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    return result[0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def save_score(self, score: ScoreOutput) -> int:
        """
        Save a score to the database using UPSERT for idempotent operations.
        
        Uses ON CONFLICT (ticker, date, mode) DO UPDATE to handle duplicates.
        This ensures the same score calculation can be run multiple times safely.
        
        Args:
            score: ScoreOutput from the scoring engine
            
        Returns:
            int: Database ID of the inserted/updated row
            
        Raises:
            psycopg2.Error: If database operation fails
            ValueError: If score data is invalid
        """
        if not isinstance(score, ScoreOutput):
            raise ValueError("Input must be a ScoreOutput instance")
        
        # Validate critical fields
        if not score.ticker or not score.ticker.strip():
            raise ValueError("Ticker cannot be empty")
        
        if not (0 <= score.score <= 100):
            raise ValueError(f"Score must be between 0-100, got {score.score}")
        
        logger.debug(f"Saving score for {score.ticker} on {score.date} ({score.mode})")
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # UPSERT query with parameterized values (SQL injection safe)
                    cur.execute("""
                        INSERT INTO scores (
                            ticker, date, mode, score, band,
                            f_pillar, t_pillar, r_pillar, o_pillar, q_pillar, s_pillar,
                            risk_penalty, guardrail_flags, confidence, s_z,
                            as_of, config_hash, code_version
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s
                        )
                        ON CONFLICT (ticker, date, mode) 
                        DO UPDATE SET
                            score = EXCLUDED.score,
                            band = EXCLUDED.band,
                            f_pillar = EXCLUDED.f_pillar,
                            t_pillar = EXCLUDED.t_pillar,
                            r_pillar = EXCLUDED.r_pillar,
                            o_pillar = EXCLUDED.o_pillar,
                            q_pillar = EXCLUDED.q_pillar,
                            s_pillar = EXCLUDED.s_pillar,
                            risk_penalty = EXCLUDED.risk_penalty,
                            guardrail_flags = EXCLUDED.guardrail_flags,
                            confidence = EXCLUDED.confidence,
                            s_z = EXCLUDED.s_z,
                            as_of = EXCLUDED.as_of,
                            config_hash = EXCLUDED.config_hash,
                            code_version = EXCLUDED.code_version
                        RETURNING id
                    """, (
                        score.ticker,
                        score.date,
                        score.mode,
                        float(score.score),
                        score.band,
                        float(score.pillars.F),
                        float(score.pillars.T),
                        float(score.pillars.R),
                        float(score.pillars.O),
                        float(score.pillars.Q),
                        float(score.pillars.S),
                        float(score.risk_penalty),
                        Json(score.guardrail_flags),  # JSON serialization
                        float(score.confidence),
                        float(score.s_z),
                        score.as_of,
                        score.config_hash,
                        getattr(score, 'code_version', greyoak_score.__version__)
                    ))
                    
                    row_id = cur.fetchone()[0]
                    conn.commit()
                    
                    logger.info(f"Score saved for {score.ticker} with ID {row_id}")
                    return row_id
                    
        except psycopg2.Error as e:
            logger.error(f"Database error saving score for {score.ticker}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving score for {score.ticker}: {e}")
            raise
    
    def get_score(
        self, 
        ticker: str, 
        date: date, 
        mode: str
    ) -> Optional[ScoreOutput]:
        """
        Retrieve a specific score from the database.
        
        Args:
            ticker: Stock ticker (e.g., 'RELIANCE.NS')
            date: Score date
            mode: 'Trader' or 'Investor'
            
        Returns:
            ScoreOutput if found, None if not found
            
        Raises:
            psycopg2.Error: If database query fails
        """
        if not ticker or not ticker.strip():
            raise ValueError("Ticker cannot be empty")
        
        if mode not in ['Trader', 'Investor']:
            raise ValueError(f"Invalid mode: {mode}. Must be 'Trader' or 'Investor'")
        
        logger.debug(f"Retrieving score for {ticker} on {date} ({mode})")
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM scores 
                        WHERE ticker = %s AND date = %s AND mode = %s
                    """, (ticker, date, mode))
                    
                    row = cur.fetchone()
                    if not row:
                        logger.debug(f"No score found for {ticker} on {date} ({mode})")
                        return None
                    
                    logger.debug(f"Score found for {ticker} on {date} ({mode})")
                    return self._row_to_score_output(row)
                    
        except psycopg2.Error as e:
            logger.error(f"Database error retrieving score for {ticker}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving score for {ticker}: {e}")
            raise
    
    def get_scores_by_ticker(
        self,
        ticker: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        mode: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[ScoreOutput]:
        """
        Get all scores for a ticker with optional filters.
        
        Args:
            ticker: Stock ticker
            start_date: Optional start date filter (inclusive)
            end_date: Optional end date filter (inclusive)
            mode: Optional mode filter ('Trader' or 'Investor')
            limit: Optional limit on number of results
            
        Returns:
            List of ScoreOutput objects ordered by date DESC
            
        Raises:
            psycopg2.Error: If database query fails
        """
        if not ticker or not ticker.strip():
            raise ValueError("Ticker cannot be empty")
        
        if mode and mode not in ['Trader', 'Investor']:
            raise ValueError(f"Invalid mode: {mode}. Must be 'Trader' or 'Investor'")
        
        logger.debug(f"Retrieving scores for {ticker} with filters: start_date={start_date}, end_date={end_date}, mode={mode}")
        
        # Build dynamic query with parameterized values
        query = "SELECT * FROM scores WHERE ticker = %s"
        params = [ticker]
        
        if start_date:
            query += " AND date >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= %s"
            params.append(end_date)
        
        if mode:
            query += " AND mode = %s"
            params.append(mode)
        
        query += " ORDER BY date DESC"
        
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    
                    results = [self._row_to_score_output(row) for row in rows]
                    logger.debug(f"Retrieved {len(results)} scores for {ticker}")
                    
                    return results
                    
        except psycopg2.Error as e:
            logger.error(f"Database error retrieving scores for {ticker}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving scores for {ticker}: {e}")
            raise
    
    def get_scores_by_band(
        self,
        band: str,
        date: date,
        mode: str,
        limit: Optional[int] = None
    ) -> List[ScoreOutput]:
        """
        Get all stocks with a specific investment band on a given date.
        
        Useful for generating investment recommendations or portfolio screening.
        Results are ordered by score DESC (best scores first).
        
        Args:
            band: 'Strong Buy', 'Buy', 'Hold', or 'Avoid'
            date: Score date
            mode: 'Trader' or 'Investor'
            limit: Optional limit on number of results
            
        Returns:
            List of ScoreOutput objects ordered by score DESC
            
        Raises:
            ValueError: If band or mode is invalid
            psycopg2.Error: If database query fails
        """
        valid_bands = ['Strong Buy', 'Buy', 'Hold', 'Avoid']
        if band not in valid_bands:
            raise ValueError(f"Invalid band: {band}. Must be one of {valid_bands}")
        
        if mode not in ['Trader', 'Investor']:
            raise ValueError(f"Invalid mode: {mode}. Must be 'Trader' or 'Investor'")
        
        logger.debug(f"Retrieving {band} stocks for {date} ({mode})")
        
        query = """
            SELECT * FROM scores 
            WHERE band = %s AND date = %s AND mode = %s
            ORDER BY score DESC
        """
        params = [band, date, mode]
        
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    
                    results = [self._row_to_score_output(row) for row in rows]
                    logger.info(f"Retrieved {len(results)} {band} stocks for {date} ({mode})")
                    
                    return results
                    
        except psycopg2.Error as e:
            logger.error(f"Database error retrieving {band} stocks: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving {band} stocks: {e}")
            raise
    
    def get_latest_scores(
        self,
        mode: str,
        limit: Optional[int] = None
    ) -> List[ScoreOutput]:
        """
        Get the most recent scores for all tickers in a given mode.
        
        Args:
            mode: 'Trader' or 'Investor'
            limit: Optional limit on number of results
            
        Returns:
            List of ScoreOutput objects for the latest date, ordered by score DESC
        """
        if mode not in ['Trader', 'Investor']:
            raise ValueError(f"Invalid mode: {mode}. Must be 'Trader' or 'Investor'")
        
        query = """
            WITH latest_date AS (
                SELECT MAX(date) as max_date FROM scores WHERE mode = %s
            )
            SELECT s.* FROM scores s
            INNER JOIN latest_date ld ON s.date = ld.max_date
            WHERE s.mode = %s
            ORDER BY s.score DESC
        """
        params = [mode, mode]
        
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    
                    results = [self._row_to_score_output(row) for row in rows]
                    logger.info(f"Retrieved {len(results)} latest scores for {mode} mode")
                    
                    return results
                    
        except psycopg2.Error as e:
            logger.error(f"Database error retrieving latest scores: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving latest scores: {e}")
            raise
    
    def _row_to_score_output(self, row: Dict[str, Any]) -> ScoreOutput:
        """
        Convert database row to ScoreOutput model.
        
        Args:
            row: Dictionary-like row from database query
            
        Returns:
            ScoreOutput: Validated Pydantic model instance
            
        Raises:
            ValueError: If row data is invalid
        """
        try:
            return ScoreOutput(
                ticker=row['ticker'],
                date=row['date'],
                mode=row['mode'],
                score=float(row['score']),
                band=row['band'],
                pillars=PillarScores(
                    F=float(row['f_pillar']),
                    T=float(row['t_pillar']),
                    R=float(row['r_pillar']),
                    O=float(row['o_pillar']),
                    Q=float(row['q_pillar']),
                    S=float(row['s_pillar'])
                ),
                risk_penalty=float(row['risk_penalty']),
                guardrail_flags=row['guardrail_flags'] if isinstance(row['guardrail_flags'], list) else [],
                confidence=float(row['confidence']),
                s_z=float(row['s_z']),
                as_of=row['as_of'],
                config_hash=row['config_hash'],
                code_version=row.get('code_version', greyoak_score.__version__)
            )
        except Exception as e:
            logger.error(f"Error converting database row to ScoreOutput: {e}")
            logger.error(f"Row data: {dict(row)}")
            raise ValueError(f"Invalid database row: {e}")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics for monitoring and debugging.
        
        Returns:
            Dict with database statistics
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get basic counts
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_scores,
                            COUNT(DISTINCT ticker) as unique_tickers,
                            COUNT(DISTINCT date) as unique_dates,
                            MIN(date) as earliest_date,
                            MAX(date) as latest_date,
                            COUNT(CASE WHEN mode = 'Trader' THEN 1 END) as trader_scores,
                            COUNT(CASE WHEN mode = 'Investor' THEN 1 END) as investor_scores
                        FROM scores
                    """)
                    
                    stats = dict(cur.fetchone())
                    
                    # Get band distribution
                    cur.execute("""
                        SELECT band, COUNT(*) as count
                        FROM scores
                        GROUP BY band
                        ORDER BY count DESC
                    """)
                    
                    stats['band_distribution'] = dict(cur.fetchall())
                    
                    return stats
                    
        except Exception as e:
            logger.error(f"Error retrieving database stats: {e}")
            return {"error": str(e)}


# Convenience singleton instance for easy access
_db_instance = None

def get_database() -> ScoreDatabase:
    """
    Get singleton database instance.
    
    Returns:
        ScoreDatabase: Shared database instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = ScoreDatabase()
    return _db_instance