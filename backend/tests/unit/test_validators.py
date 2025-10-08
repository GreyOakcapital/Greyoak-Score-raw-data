"""Unit tests for input validators."""

import pytest
from datetime import date

from greyoak_score.utils.validators import (
    validate_ticker,
    validate_date,
    validate_mode,
    validate_score,
    validate_risk_penalty,
    validate_confidence,
    validate_band,
)


class TestTickerValidation:
    """Test ticker symbol validation."""

    def test_valid_ticker(self):
        """Test valid ticker symbols."""
        assert validate_ticker("RELIANCE.NS") == "RELIANCE.NS"
        assert validate_ticker("TCS.NS") == "TCS.NS"
        assert validate_ticker("hdfcbank.ns") == "HDFCBANK.NS"  # Uppercase

    def test_invalid_ticker_no_suffix(self):
        """Test invalid ticker without .NS suffix."""
        with pytest.raises(ValueError, match="Invalid ticker format"):
            validate_ticker("RELIANCE")

    def test_invalid_ticker_empty(self):
        """Test empty ticker."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_ticker("")

    def test_invalid_ticker_special_chars(self):
        """Test ticker with special characters."""
        with pytest.raises(ValueError, match="Invalid ticker format"):
            validate_ticker("RELI@NCE.NS")


class TestDateValidation:
    """Test date validation."""

    def test_valid_date(self):
        """Test valid date string."""
        result = validate_date("2024-10-08")
        assert result == date(2024, 10, 8)

    def test_invalid_date_format(self):
        """Test invalid date format."""
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date("10/08/2024")

    def test_invalid_date_values(self):
        """Test invalid date values."""
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date("2024-13-01")  # Month 13


class TestModeValidation:
    """Test mode validation."""

    def test_valid_modes(self):
        """Test valid modes."""
        assert validate_mode("Trader") == "Trader"
        assert validate_mode("Investor") == "Investor"

    def test_invalid_mode(self):
        """Test invalid mode."""
        with pytest.raises(ValueError, match="Invalid mode"):
            validate_mode("Short")


class TestScoreValidation:
    """Test score validation."""

    def test_valid_scores(self):
        """Test scores in valid range [0, 100]."""
        validate_score(0.0)  # Should not raise
        validate_score(50.5)  # Should not raise
        validate_score(100.0)  # Should not raise

    def test_negative_score(self):
        """Test negative score."""
        with pytest.raises(ValueError, match="out of range"):
            validate_score(-1.0)

    def test_score_above_max(self):
        """Test score above 100."""
        with pytest.raises(ValueError, match="out of range"):
            validate_score(101.0)


class TestRiskPenaltyValidation:
    """Test risk penalty validation."""

    def test_valid_rp(self):
        """Test RP in valid range [0, 20]."""
        validate_risk_penalty(0.0)  # Should not raise
        validate_risk_penalty(10.5)  # Should not raise
        validate_risk_penalty(20.0)  # Should not raise

    def test_negative_rp(self):
        """Test negative RP."""
        with pytest.raises(ValueError, match="out of range"):
            validate_risk_penalty(-1.0)

    def test_rp_above_max(self):
        """Test RP above 20."""
        with pytest.raises(ValueError, match="out of range"):
            validate_risk_penalty(21.0)


class TestConfidenceValidation:
    """Test confidence validation."""

    def test_valid_confidence(self):
        """Test confidence in valid range [0, 1]."""
        validate_confidence(0.0)  # Should not raise
        validate_confidence(0.5)  # Should not raise
        validate_confidence(1.0)  # Should not raise

    def test_negative_confidence(self):
        """Test negative confidence."""
        with pytest.raises(ValueError, match="out of range"):
            validate_confidence(-0.1)

    def test_confidence_above_max(self):
        """Test confidence above 1.0."""
        with pytest.raises(ValueError, match="out of range"):
            validate_confidence(1.1)


class TestBandValidation:
    """Test band validation."""

    def test_valid_bands(self):
        """Test valid band values."""
        validate_band("Strong Buy")  # Should not raise
        validate_band("Buy")  # Should not raise
        validate_band("Hold")  # Should not raise
        validate_band("Avoid")  # Should not raise

    def test_invalid_band(self):
        """Test invalid band value."""
        with pytest.raises(ValueError, match="Invalid band"):
            validate_band("Neutral")
