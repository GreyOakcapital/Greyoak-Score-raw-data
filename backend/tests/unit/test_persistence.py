"""Unit tests for PostgreSQL Persistence Layer (data/persistence.py)."""

import pytest
import psycopg2
from datetime import date, datetime, timezone
from unittest.mock import patch, MagicMock
import os

from greyoak_score.data.persistence import ScoreDatabase, get_database
from greyoak_score.data.models import ScoreOutput, PillarScores


@pytest.fixture
def sample_score_output():
    """Create a sample ScoreOutput for testing."""
    return ScoreOutput(
        ticker="TESTSTOCK.NS",
        scoring_date=date(2024, 10, 8),
        mode="Trader",
        score=75.5,
        band="Buy",
        pillars=PillarScores(F=70.0, T=80.0, R=75.0, O=65.0, Q=85.0, S=78.0),
        risk_penalty=5.5,
        guardrail_flags=["LowDataHold"],
        confidence=0.85,
        s_z=1.2,
        as_of=datetime(2024, 10, 8, 10, 30, 0, tzinfo=timezone.utc),
        config_hash="abc123def456",
        code_version="1.0.0"
    )


@pytest.fixture
def mock_db():
    """Create a database instance with mocked connection for unit tests."""
    db = ScoreDatabase("postgresql://test:test@localhost:5432/test")
    return db


class TestDatabaseInitialization:
    """Test database initialization and connection management."""
    
    def test_init_with_custom_url(self):
        """Test initialization with custom database URL."""
        custom_url = "postgresql://user:pass@host:5432/dbname"
        db = ScoreDatabase(custom_url)
        assert db.database_url == custom_url
    
    def test_init_with_environment_variables(self):
        """Test initialization using environment variables."""
        with patch.dict(os.environ, {
            'PGUSER': 'testuser',
            'PGPASSWORD': 'testpass',
            'PGHOST': 'testhost',
            'PGPORT': '5433',
            'PGDATABASE': 'testdb'
        }):
            db = ScoreDatabase()
            expected_url = "postgresql://testuser:testpass@testhost:5433/testdb"
            assert db.database_url == expected_url
    
    def test_init_with_defaults(self):
        """Test initialization with default values when env vars are missing."""
        # Clear relevant env vars by removing them entirely
        env_vars = ['PGUSER', 'PGPASSWORD', 'PGHOST', 'PGPORT', 'PGDATABASE']
        with patch.dict(os.environ, {}, clear=True):
            # Ensure the env vars don't exist
            for var in env_vars:
                os.environ.pop(var, None)
            db = ScoreDatabase()
            expected_url = "postgresql://greyoak:greyoak_pw_change_in_production@db:5432/greyoak_scores"
            assert db.database_url == expected_url
    
    def test_safe_connection_info(self, mock_db):
        """Test that connection info doesn't expose credentials."""
        mock_db.database_url = "postgresql://user:secret@host:5432/db"
        safe_info = mock_db._get_safe_connection_info()
        assert "secret" not in safe_info
        assert "postgresql://***:***@host:5432/db" == safe_info


class TestConnectionManagement:
    """Test database connection context manager and error handling."""
    
    def test_connection_context_manager_success(self, mock_db):
        """Test successful connection context manager."""
        mock_conn = MagicMock()
        
        with patch('psycopg2.connect', return_value=mock_conn) as mock_connect:
            with mock_db.get_connection() as conn:
                assert conn == mock_conn
        
        mock_connect.assert_called_once_with(mock_db.database_url)
        mock_conn.close.assert_called_once()
    
    def test_connection_context_manager_error(self, mock_db):
        """Test connection context manager with database error."""
        with patch('psycopg2.connect', side_effect=psycopg2.Error("Connection failed")):
            with pytest.raises(psycopg2.Error):
                with mock_db.get_connection():
                    pass
    
    def test_connection_context_manager_rollback_on_error(self, mock_db):
        """Test that connection is rolled back on error."""
        mock_conn = MagicMock()
        
        with patch('psycopg2.connect', return_value=mock_conn):
            with pytest.raises(ValueError):
                with mock_db.get_connection() as conn:
                    raise ValueError("Test error")
        
        mock_conn.rollback.assert_called_once()
        mock_conn.close.assert_called_once()
    
    def test_test_connection_success(self, mock_db):
        """Test successful connection test."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [1]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('psycopg2.connect', return_value=mock_conn):
            result = mock_db.test_connection()
        
        assert result is True
        mock_cursor.execute.assert_called_once_with("SELECT 1")
    
    def test_test_connection_failure(self, mock_db):
        """Test failed connection test."""
        with patch('psycopg2.connect', side_effect=psycopg2.Error("Connection failed")):
            result = mock_db.test_connection()
        
        assert result is False


class TestSaveScore:
    """Test score saving functionality."""
    
    def test_save_score_success(self, mock_db, sample_score_output):
        """Test successful score saving."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [123]  # Mock returned ID
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('psycopg2.connect', return_value=mock_conn):
            result = mock_db.save_score(sample_score_output)
        
        assert result == 123
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        
        # Verify the SQL query was called with correct parameters
        call_args = mock_cursor.execute.call_args
        assert "INSERT INTO scores" in call_args[0][0]
        assert "ON CONFLICT" in call_args[0][0]
        
        # Verify parameters
        params = call_args[0][1]
        assert params[0] == sample_score_output.ticker
        assert params[1] == sample_score_output.scoring_date
        assert params[2] == sample_score_output.mode
    
    def test_save_score_invalid_input(self, mock_db):
        """Test saving invalid score input."""
        with pytest.raises(ValueError, match="Input must be a ScoreOutput instance"):
            mock_db.save_score("invalid_input")
    
    def test_save_score_empty_ticker(self, mock_db, sample_score_output):
        """Test saving score with empty ticker."""
        sample_score_output.ticker = ""
        
        with pytest.raises(ValueError, match="Ticker cannot be empty"):
            mock_db.save_score(sample_score_output)
    
    def test_save_score_invalid_score_range(self, mock_db, sample_score_output):
        """Test saving score with invalid score value."""
        sample_score_output.score = 150.0  # Invalid: > 100
        
        with pytest.raises(ValueError, match="Score must be between 0-100"):
            mock_db.save_score(sample_score_output)
    
    def test_save_score_database_error(self, mock_db, sample_score_output):
        """Test handling of database errors during save."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = psycopg2.Error("Database error")
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('psycopg2.connect', return_value=mock_conn):
            with pytest.raises(psycopg2.Error):
                mock_db.save_score(sample_score_output)


class TestGetScore:
    """Test score retrieval functionality."""
    
    def test_get_score_found(self, mock_db):
        """Test successful score retrieval."""
        # Mock database row
        mock_row = {
            'ticker': 'TESTSTOCK.NS',
            'date': date(2024, 10, 8),
            'mode': 'Trader',
            'score': 75.5,
            'band': 'Buy',
            'f_pillar': 70.0,
            't_pillar': 80.0,
            'r_pillar': 75.0,
            'o_pillar': 65.0,
            'q_pillar': 85.0,
            's_pillar': 78.0,
            'risk_penalty': 5.5,
            'guardrail_flags': ["LowDataHold"],
            'confidence': 0.85,
            's_z': 1.2,
            'as_of': datetime(2024, 10, 8, 10, 30, 0, tzinfo=timezone.utc),
            'config_hash': 'abc123def456',
            'code_version': '1.0.0'
        }
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = mock_row
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('psycopg2.connect', return_value=mock_conn):
            result = mock_db.get_score('TESTSTOCK.NS', date(2024, 10, 8), 'Trader')
        
        assert result is not None
        assert isinstance(result, ScoreOutput)
        assert result.ticker == 'TESTSTOCK.NS'
        assert result.score == 75.5
        assert result.band == 'Buy'
        
        # Verify SQL query
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0].strip()  # Remove whitespace
        assert "SELECT * FROM scores" in query
        assert "WHERE ticker = %s AND date = %s AND mode = %s" in query
    
    def test_get_score_not_found(self, mock_db):
        """Test score retrieval when no record exists."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('psycopg2.connect', return_value=mock_conn):
            result = mock_db.get_score('NONEXISTENT.NS', date(2024, 10, 8), 'Trader')
        
        assert result is None
    
    def test_get_score_invalid_ticker(self, mock_db):
        """Test get_score with invalid ticker."""
        with pytest.raises(ValueError, match="Ticker cannot be empty"):
            mock_db.get_score("", date(2024, 10, 8), 'Trader')
    
    def test_get_score_invalid_mode(self, mock_db):
        """Test get_score with invalid mode."""
        with pytest.raises(ValueError, match="Invalid mode"):
            mock_db.get_score("TEST.NS", date(2024, 10, 8), 'InvalidMode')


class TestGetScoresByTicker:
    """Test ticker-based score queries."""
    
    def test_get_scores_by_ticker_basic(self, mock_db):
        """Test basic ticker query without filters."""
        mock_rows = [
            {'ticker': 'TEST.NS', 'date': date(2024, 10, 8), 'mode': 'Trader', 'score': 75.0,
             'band': 'Buy', 'f_pillar': 70.0, 't_pillar': 80.0, 'r_pillar': 75.0,
             'o_pillar': 65.0, 'q_pillar': 85.0, 's_pillar': 78.0, 'risk_penalty': 5.0,
             'guardrail_flags': [], 'confidence': 0.85, 's_z': 1.2,
             'as_of': datetime.now(timezone.utc), 'config_hash': 'abc123', 'code_version': '1.0.0'}
        ]
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = mock_rows
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('psycopg2.connect', return_value=mock_conn):
            results = mock_db.get_scores_by_ticker('TEST.NS')
        
        assert len(results) == 1
        assert isinstance(results[0], ScoreOutput)
        assert results[0].ticker == 'TEST.NS'
    
    def test_get_scores_by_ticker_with_filters(self, mock_db):
        """Test ticker query with date and mode filters."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('psycopg2.connect', return_value=mock_conn):
            mock_db.get_scores_by_ticker(
                'TEST.NS',
                start_date=date(2024, 10, 1),
                end_date=date(2024, 10, 8),
                mode='Trader',
                limit=10
            )
        
        # Verify SQL query construction
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        assert "WHERE ticker = %s" in query
        assert "AND date >= %s" in query
        assert "AND date <= %s" in query
        assert "AND mode = %s" in query
        assert "LIMIT %s" in query
        
        assert params == ['TEST.NS', date(2024, 10, 1), date(2024, 10, 8), 'Trader', 10]
    
    def test_get_scores_by_ticker_invalid_mode(self, mock_db):
        """Test ticker query with invalid mode."""
        with pytest.raises(ValueError, match="Invalid mode"):
            mock_db.get_scores_by_ticker('TEST.NS', mode='InvalidMode')


class TestGetScoresByBand:
    """Test band-based score queries."""
    
    def test_get_scores_by_band_success(self, mock_db):
        """Test successful band-based query."""
        mock_rows = [
            {'ticker': 'STOCK1.NS', 'date': date(2024, 10, 8), 'mode': 'Trader', 'score': 80.0,
             'band': 'Strong Buy', 'f_pillar': 75.0, 't_pillar': 85.0, 'r_pillar': 80.0,
             'o_pillar': 70.0, 'q_pillar': 90.0, 's_pillar': 82.0, 'risk_penalty': 2.0,
             'guardrail_flags': [], 'confidence': 0.90, 's_z': 1.5,
             'as_of': datetime.now(timezone.utc), 'config_hash': 'xyz789', 'code_version': '1.0.0'}
        ]
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = mock_rows
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('psycopg2.connect', return_value=mock_conn):
            results = mock_db.get_scores_by_band('Strong Buy', date(2024, 10, 8), 'Trader')
        
        assert len(results) == 1
        assert results[0].band == 'Strong Buy'
        assert results[0].score == 80.0
        
        # Verify SQL query
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]
        assert "WHERE band = %s AND date = %s AND mode = %s" in query
        assert "ORDER BY score DESC" in query
    
    def test_get_scores_by_band_invalid_band(self, mock_db):
        """Test band query with invalid band."""
        with pytest.raises(ValueError, match="Invalid band"):
            mock_db.get_scores_by_band('Invalid Band', date(2024, 10, 8), 'Trader')
    
    def test_get_scores_by_band_invalid_mode(self, mock_db):
        """Test band query with invalid mode."""
        with pytest.raises(ValueError, match="Invalid mode"):
            mock_db.get_scores_by_band('Buy', date(2024, 10, 8), 'InvalidMode')


class TestUtilityFunctions:
    """Test utility and helper functions."""
    
    def test_get_database_singleton(self):
        """Test singleton database instance."""
        db1 = get_database()
        db2 = get_database()
        assert db1 is db2  # Should be the same instance
    
    def test_row_to_score_output_conversion(self, mock_db):
        """Test database row to ScoreOutput conversion."""
        row = {
            'ticker': 'TEST.NS',
            'date': date(2024, 10, 8),
            'mode': 'Trader',
            'score': 75.0,
            'band': 'Buy',
            'f_pillar': 70.0,
            't_pillar': 80.0,
            'r_pillar': 75.0,
            'o_pillar': 65.0,
            'q_pillar': 85.0,
            's_pillar': 78.0,
            'risk_penalty': 5.0,
            'guardrail_flags': ["LowDataHold"],
            'confidence': 0.85,
            's_z': 1.2,
            'as_of': datetime(2024, 10, 8, 10, 30, tzinfo=timezone.utc),
            'config_hash': 'abc123',
            'code_version': '1.0.0'
        }
        
        result = mock_db._row_to_score_output(row)
        
        assert isinstance(result, ScoreOutput)
        assert result.ticker == 'TEST.NS'
        assert result.score == 75.0
        assert result.pillars.F == 70.0
        assert result.guardrail_flags == ["LowDataHold"]
    
    def test_row_to_score_output_invalid_data(self, mock_db):
        """Test conversion with invalid row data."""
        invalid_row = {'ticker': 'TEST', 'invalid_field': 'value'}
        
        with pytest.raises(ValueError, match="Invalid database row"):
            mock_db._row_to_score_output(invalid_row)


class TestDatabaseStats:
    """Test database statistics functionality."""
    
    def test_get_database_stats_success(self, mock_db):
        """Test successful database stats retrieval."""
        mock_stats_row = {
            'total_scores': 100,
            'unique_tickers': 20,
            'unique_dates': 5,
            'earliest_date': date(2024, 10, 1),
            'latest_date': date(2024, 10, 8),
            'trader_scores': 60,
            'investor_scores': 40
        }
        
        mock_band_rows = [
            ('Buy', 40),
            ('Hold', 30),
            ('Strong Buy', 20),
            ('Avoid', 10)
        ]
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = mock_stats_row
        mock_cursor.fetchall.return_value = mock_band_rows
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('psycopg2.connect', return_value=mock_conn):
            stats = mock_db.get_database_stats()
        
        assert stats['total_scores'] == 100
        assert stats['unique_tickers'] == 20
        assert 'band_distribution' in stats
        assert stats['band_distribution']['Buy'] == 40
    
    def test_get_database_stats_error(self, mock_db):
        """Test database stats with error."""
        with patch('psycopg2.connect', side_effect=psycopg2.Error("Database error")):
            stats = mock_db.get_database_stats()
        
        assert 'error' in stats
        assert 'Database error' in stats['error']


if __name__ == "__main__":
    pytest.main([__file__])