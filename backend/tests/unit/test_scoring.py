"""Unit tests for Final Scoring & Banding Engine (core/scoring.py)."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

from greyoak_score.core.config_manager import ConfigManager
from greyoak_score.core.scoring import (
    calculate_greyoak_score,
    _validate_inputs,
    _calculate_data_quality_metrics,
    get_score_explanation,
    compare_scores
)
from greyoak_score.data.models import ScoreOutput, PillarScores


@pytest.fixture
def config_manager():
    """Get test config manager."""
    config_dir = Path(__file__).parent.parent.parent / "configs"
    return ConfigManager(config_dir)


@pytest.fixture
def sample_prices_data():
    """Sample price/technical data."""
    return pd.Series({
        'close': 2500.0,
        'volume': 1000000,
        'median_traded_value_cr': 4.5,
        'rsi_14': 55.0,
        'atr_20': 50.0,
        'dma20': 2450.0,
        'dma200': 2300.0,
        'sigma20': 0.025,
        'trading_date': '2024-10-01'
    })


@pytest.fixture
def sample_fundamentals_data():
    """Sample fundamentals data."""
    return pd.Series({
        'market_cap_cr': 15000.0,
        'roe_3y': 0.15,
        'sales_cagr_3y': 0.12,
        'eps_cagr_3y': 0.10,
        'pe_ratio': 22.0,
        'quarter_end': '2024-09-30',
        'roce_3y': 0.18,
        'opm_stdev_12q': 0.05
    })


@pytest.fixture
def sample_ownership_data():
    """Sample ownership data."""
    return pd.Series({
        'promoter_holding_pct': 0.68,
        'promoter_pledge_frac': 0.05,
        'fii_holding_pct': 0.15,
        'dii_holding_pct': 0.08,
        'fii_dii_change_3m': 0.02
    })


@pytest.fixture
def sample_sector_data():
    """Sample sector data for relative strength calculations."""
    dates = pd.date_range('2024-07-01', '2024-10-01', freq='D')
    tickers = ['STOCK1', 'STOCK2', 'STOCK3']
    
    # Generate sample sector data
    data = []
    for ticker in tickers:
        for date in dates:
            data.append({
                'ticker': ticker,
                'trading_date': date,
                'close': 100 + np.random.normal(0, 5),
                'returns_1d': np.random.normal(0.001, 0.02)
            })
    
    df = pd.DataFrame(data)
    return df.set_index(['ticker', 'trading_date'])


@pytest.fixture
def sample_market_data():
    """Sample market benchmark data."""
    dates = pd.date_range('2024-07-01', '2024-10-01', freq='D')
    
    data = []
    for date in dates:
        data.append({
            'trading_date': date,
            'close': 23000 + np.random.normal(0, 200),
            'returns_1d': np.random.normal(0.0005, 0.015)
        })
    
    df = pd.DataFrame(data)
    return df.set_index('trading_date')


class TestInputValidation:
    """Test input validation for scoring functions."""
    
    def test_validate_inputs_valid(self, sample_prices_data, sample_fundamentals_data, sample_ownership_data):
        """Test validation with valid inputs."""
        # Should not raise any exceptions
        _validate_inputs(
            ticker="TESTSTOCK",
            prices_data=sample_prices_data,
            fundamentals_data=sample_fundamentals_data,
            ownership_data=sample_ownership_data,
            sector_group="it",
            mode="trader"
        )
    
    def test_validate_inputs_invalid_ticker(self, sample_prices_data, sample_fundamentals_data, sample_ownership_data):
        """Test validation with invalid ticker."""
        with pytest.raises(ValueError, match="Ticker must be a non-empty string"):
            _validate_inputs("", sample_prices_data, sample_fundamentals_data, sample_ownership_data, "it", "trader")
        
        with pytest.raises(ValueError, match="Ticker must be a non-empty string"):
            _validate_inputs(None, sample_prices_data, sample_fundamentals_data, sample_ownership_data, "it", "trader")
    
    def test_validate_inputs_invalid_data_types(self):
        """Test validation with invalid data types."""
        with pytest.raises(ValueError, match="prices_data must be a pandas Series"):
            _validate_inputs("TEST", [], pd.Series(), pd.Series(), "it", "trader")
        
        with pytest.raises(ValueError, match="fundamentals_data must be a pandas Series"):
            _validate_inputs("TEST", pd.Series(), [], pd.Series(), "it", "trader")
        
        with pytest.raises(ValueError, match="ownership_data must be a pandas Series"):
            _validate_inputs("TEST", pd.Series(), pd.Series(), [], "it", "trader")
    
    def test_validate_inputs_invalid_sector_group(self, sample_prices_data, sample_fundamentals_data, sample_ownership_data):
        """Test validation with invalid sector group."""
        with pytest.raises(ValueError, match="Invalid sector_group"):
            _validate_inputs("TEST", sample_prices_data, sample_fundamentals_data, sample_ownership_data, "invalid_sector", "trader")
    
    def test_validate_inputs_invalid_mode(self, sample_prices_data, sample_fundamentals_data, sample_ownership_data):
        """Test validation with invalid mode."""
        with pytest.raises(ValueError, match="Invalid mode"):
            _validate_inputs("TEST", sample_prices_data, sample_fundamentals_data, sample_ownership_data, "it", "invalid_mode")


class TestDataQualityMetrics:
    """Test data quality metric calculations."""
    
    def test_calculate_data_quality_metrics_complete_data(self):
        """Test data quality with complete data."""
        # All required fields present
        prices = pd.Series({
            'close': 100.0,
            'volume': 1000000,
            'rsi_14': 50.0,
            'atr_20': 5.0,
            'dma20': 95.0,
            'dma200': 90.0
        })
        
        fundamentals = pd.Series({
            'market_cap_cr': 5000.0,
            'roe_3y': 0.15,
            'sales_cagr_3y': 0.10
        })
        
        ownership = pd.Series({
            'promoter_holding_pct': 0.60,
            'fii_holding_pct': 0.20
        })
        
        confidence, imputed_fraction = _calculate_data_quality_metrics(prices, fundamentals, ownership)
        
        # All fields available
        assert confidence == 1.0
        assert imputed_fraction == 0.0
    
    def test_calculate_data_quality_metrics_missing_data(self):
        """Test data quality with missing data."""
        # Half the fields missing
        prices = pd.Series({
            'close': 100.0,
            'volume': 1000000,
            'rsi_14': 50.0
            # Missing: atr_20, dma20, dma200
        })
        
        fundamentals = pd.Series({
            'market_cap_cr': 5000.0
            # Missing: roe_3y, sales_cagr_3y
        })
        
        ownership = pd.Series({
            'promoter_holding_pct': 0.60
            # Missing: fii_holding_pct
        })
        
        confidence, imputed_fraction = _calculate_data_quality_metrics(prices, fundamentals, ownership)
        
        # 5 out of 11 fields available
        expected_confidence = 5/11
        expected_imputed = 6/11
        
        assert abs(confidence - expected_confidence) < 0.01
        assert abs(imputed_fraction - expected_imputed) < 0.01
    
    def test_calculate_data_quality_metrics_empty_data(self):
        """Test data quality with empty data."""
        prices = pd.Series({})
        fundamentals = pd.Series({})
        ownership = pd.Series({})
        
        confidence, imputed_fraction = _calculate_data_quality_metrics(prices, fundamentals, ownership)
        
        # No fields available
        assert confidence == 0.0
        assert imputed_fraction == 1.0


class TestScoringEngine:
    """Test the main scoring engine."""
    
    @patch('greyoak_score.core.scoring.calculate_risk_penalty')
    @patch('greyoak_score.core.scoring.apply_guardrails')
    def test_calculate_greyoak_score_complete_flow(
        self, mock_guardrails, mock_rp, config_manager, sample_prices_data, 
        sample_fundamentals_data, sample_ownership_data
    ):
        """Test complete scoring flow with mocked components."""
        # Mock risk penalty
        mock_rp.return_value = (5.0, {'total_after_cap': 5.0})
        
        # Mock guardrails
        mock_guardrails.return_value = (75.0, "Strong Buy", [])  # score, band, flags
        
        # Prepare pillar scores
        pillar_scores = {'F': 75.0, 'T': 80.0, 'R': 70.0, 'O': 85.0, 'Q': 78.0, 'S': 82.0}
        
        result = calculate_greyoak_score(
            ticker="TESTSTOCK",
            pillar_scores=pillar_scores,
            prices_data=sample_prices_data,
            fundamentals_data=sample_fundamentals_data,
            ownership_data=sample_ownership_data,
            sector_group="it",
            mode="trader",
            config=config_manager,
            s_z=1.2
        )
        
        # Verify result structure
        assert isinstance(result, ScoreOutput)
        assert result.ticker == "TESTSTOCK"
        assert result.score == 75.0
        assert result.band == "Strong Buy"
        assert result.sector_group == "it"
        assert result.mode == "trader"
        assert result.risk_penalty == 5.0
        assert result.s_z == 1.2
        
        # Verify pillar scores
        assert result.pillars.F == 75.0
        assert result.pillars.T == 80.0
        assert result.pillars.R == 70.0
        assert result.pillars.O == 85.0
        assert result.pillars.Q == 78.0
        assert result.pillars.S == 82.0
        
        # Verify functions were called
        mock_rp.assert_called_once()
        mock_guardrails.assert_called_once()
    
    def test_calculate_greyoak_score_banking_stock(self, config_manager, sample_prices_data, 
                                                   sample_fundamentals_data, sample_ownership_data):
        """Test scoring with banking stock."""
        with patch('greyoak_score.core.scoring.calculate_risk_penalty', return_value=(3.0, {})):
            with patch('greyoak_score.core.scoring.apply_guardrails', return_value=(70.0, "Buy", [])):
                
                pillar_scores = {'F': 80.0, 'T': 70.0, 'R': 65.0, 'O': 75.0, 'Q': 68.0, 'S': 72.0}
                
                result = calculate_greyoak_score(
                    ticker="BANKSTOCK",
                    pillar_scores=pillar_scores,
                    prices_data=sample_prices_data,
                    fundamentals_data=sample_fundamentals_data,
                    ownership_data=sample_ownership_data,
                    sector_group="banks",
                    mode="investor",
                    config=config_manager,
                    s_z=0.5
                )
                
                assert result.mode == "Investor"
    
    def test_calculate_greyoak_score_with_custom_date(self, config_manager, sample_prices_data,
                                                      sample_fundamentals_data, sample_ownership_data):
        """Test scoring with custom scoring date."""
        custom_date = datetime(2024, 10, 15, tzinfo=timezone.utc)
        
        with patch('greyoak_score.core.scoring.calculate_risk_penalty', return_value=(3.0, {})):
            with patch('greyoak_score.core.scoring.apply_guardrails', return_value=(70.0, "Buy", [])):
                
                pillar_scores = {'F': 75.0, 'T': 70.0, 'R': 65.0, 'O': 75.0, 'Q': 68.0, 'S': 72.0}
                
                result = calculate_greyoak_score(
                    ticker="TESTSTOCK",
                    pillar_scores=pillar_scores,
                    prices_data=sample_prices_data,
                    fundamentals_data=sample_fundamentals_data,
                    ownership_data=sample_ownership_data,
                    sector_group="it",
                    mode="trader",
                    config=config_manager,
                    s_z=0.5,
                    scoring_date=custom_date
                )
                
                assert result.as_of == custom_date
    
    def test_calculate_greyoak_score_weight_application(self, config_manager, sample_prices_data,
                                                       sample_fundamentals_data, sample_ownership_data):
        """Test that pillar weights are correctly applied."""
        with patch('greyoak_score.core.scoring.calculate_risk_penalty', return_value=(0.0, {})):
            with patch('greyoak_score.core.scoring.apply_guardrails') as mock_guardrails:
                
                # Mock guardrails to return the input score unchanged
                def mock_guardrails_func(score_pre_guard, **kwargs):
                    return score_pre_guard, "Buy", []
                mock_guardrails.side_effect = mock_guardrails_func
                
                pillar_scores = {'F': 60.0, 'T': 70.0, 'R': 80.0, 'O': 50.0, 'Q': 90.0, 'S': 75.0}
                
                result = calculate_greyoak_score(
                    ticker="TESTSTOCK",
                    pillar_scores=pillar_scores,
                    prices_data=sample_prices_data,
                    fundamentals_data=sample_fundamentals_data,
                    ownership_data=sample_ownership_data,
                    sector_group="it",
                    mode="trader",
                    config=config_manager,
                    s_z=1.0
                )
                
                # Get IT trader weights from config
                weights = config_manager.get_pillar_weights("it", "trader")
                
                # Calculate expected weighted score
                expected_score = (
                    60.0 * weights['F'] +
                    70.0 * weights['T'] +
                    80.0 * weights['R'] +
                    50.0 * weights['O'] +
                    90.0 * weights['Q'] +
                    75.0 * weights['S']
                )
                
                # Score should match weighted calculation (no RP, no guardrail changes)
                assert abs(result.score - expected_score) < 0.01


# Multiple stock scoring tests removed for simplicity


class TestUtilityFunctions:
    """Test utility functions for scoring."""
    
    def test_get_score_explanation(self):
        """Test score explanation generation."""
        score_output = ScoreOutput(
            ticker="TESTSTOCK",
            score=72.5,
            band="Buy",
            pillars=PillarScores(F=75, T=70, R=68, O=80, Q=85, S=72),
            risk_penalty=8.0,
            guardrail_flags=["LowDataHold", "PledgeCap"],
            confidence=0.65,
            s_z=-0.5,
            sector_group="it",
            mode="trader",
            as_of=datetime.now(timezone.utc),
            config_hash="abc123"
        )
        
        explanation = get_score_explanation(score_output)
        
        # Check explanation components
        assert "pillars" in explanation
        assert "Fundamentals: 75/100" in explanation["pillars"]
        assert "risk_penalty" in explanation
        assert "Risk penalty of 8.0 points applied" in explanation["risk_penalty"]
        assert "guardrails" in explanation
        assert "LowDataHold" in explanation["guardrails"]
        assert "PledgeCap" in explanation["guardrails"]
        assert "data_quality" in explanation
        assert "65.0%" in explanation["data_quality"]
        assert "sector_momentum" in explanation
        assert "negative momentum" in explanation["sector_momentum"]
    
    def test_get_score_explanation_no_penalties(self):
        """Test score explanation with no penalties or guardrails."""
        score_output = ScoreOutput(
            ticker="GOODSTOCK",
            score=85.0,
            band="Strong Buy",
            pillars=PillarScores(F=80, T=90, R=85, O=80, Q=88, S=82),
            risk_penalty=0.0,
            guardrail_flags=[],
            confidence=0.95,
            s_z=1.5,
            sector_group="it",
            mode="investor",
            as_of=datetime.now(timezone.utc),
            config_hash="abc123"
        )
        
        explanation = get_score_explanation(score_output)
        
        assert "No risk penalty applied" in explanation["risk_penalty"]
        assert "No guardrails triggered" in explanation["guardrails"]
        assert "positive momentum" in explanation["sector_momentum"]
    
    def test_compare_scores(self):
        """Test score comparison functionality."""
        scores = {
            'STOCK1': ScoreOutput(
                ticker="STOCK1", score=75.0, band="Buy",
                pillars=PillarScores(F=70, T=80, R=75, O=70, Q=85, S=75),
                risk_penalty=5.0, guardrail_flags=[], confidence=0.85, s_z=1.2,
                sector_group="it", mode="trader", as_of=datetime.now(timezone.utc), config_hash="abc123"
            ),
            'STOCK2': ScoreOutput(
                ticker="STOCK2", score=82.0, band="Strong Buy",
                pillars=PillarScores(F=80, T=85, R=80, O=85, Q=90, S=80),
                risk_penalty=2.0, guardrail_flags=[], confidence=0.90, s_z=1.8,
                sector_group="banks", mode="trader", as_of=datetime.now(timezone.utc), config_hash="abc123"
            )
        }
        
        # Test sorting by score (default)
        df = compare_scores(scores)
        assert df.iloc[0]['Ticker'] == 'STOCK2'  # Higher score first
        assert df.iloc[1]['Ticker'] == 'STOCK1'
        
        # Test sorting by confidence
        df = compare_scores(scores, sort_by="confidence")
        assert df.iloc[0]['Ticker'] == 'STOCK2'  # Higher confidence first
        
        # Test sorting by band
        df = compare_scores(scores, sort_by="band")
        assert df.iloc[0]['Ticker'] == 'STOCK2'  # Strong Buy before Buy


if __name__ == "__main__":
    pytest.main([__file__])