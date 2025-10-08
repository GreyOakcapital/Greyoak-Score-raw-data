"""Input validation utilities."""

import re
from datetime import date, datetime
from typing import List, Optional

from greyoak_score.utils.constants import (
    CONFIDENCE_MAX,
    CONFIDENCE_MIN,
    RP_MAX,
    RP_MIN,
    SCORE_MAX,
    SCORE_MIN,
    VALID_BANDS,
    VALID_MODES,
)


def validate_ticker(ticker: str) -> str:
    """Validate and sanitize ticker symbol.
    
    Args:
        ticker: Ticker symbol to validate.
        
    Returns:
        Sanitized ticker (uppercase).
        
    Raises:
        ValueError: If ticker format is invalid.
    """
    if not ticker:
        raise ValueError("Ticker cannot be empty")
    
    # NSE tickers: alphanumeric + .NS suffix
    pattern = r"^[A-Z0-9]+\.NS$"
    ticker_upper = ticker.upper()
    
    if not re.match(pattern, ticker_upper):
        raise ValueError(
            f"Invalid ticker format '{ticker}'. "
            f"Expected format: TICKER.NS (e.g., RELIANCE.NS)"
        )
    
    return ticker_upper


def validate_date(date_str: str) -> date:
    """Validate date string in ISO 8601 format.
    
    Args:
        date_str: Date string (YYYY-MM-DD).
        
    Returns:
        Parsed date object.
        
    Raises:
        ValueError: If date format is invalid.
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(
            f"Invalid date format '{date_str}'. Expected YYYY-MM-DD (ISO 8601)"
        ) from e


def validate_mode(mode: str) -> str:
    """Validate scoring mode.
    
    Args:
        mode: Scoring mode.
        
    Returns:
        Validated mode.
        
    Raises:
        ValueError: If mode is invalid.
    """
    if mode not in VALID_MODES:
        raise ValueError(
            f"Invalid mode '{mode}'. Valid modes: {VALID_MODES}"
        )
    return mode


def validate_score(score: float) -> None:
    """Validate score is in valid range [0, 100].
    
    Args:
        score: Score value to validate.
        
    Raises:
        ValueError: If score is out of range.
    """
    if not (SCORE_MIN <= score <= SCORE_MAX):
        raise ValueError(
            f"Score {score} out of range [{SCORE_MIN}, {SCORE_MAX}]"
        )


def validate_risk_penalty(rp: float) -> None:
    """Validate risk penalty is in valid range [0, 20].
    
    Args:
        rp: Risk penalty value to validate.
        
    Raises:
        ValueError: If RP is out of range.
    """
    if not (RP_MIN <= rp <= RP_MAX):
        raise ValueError(
            f"Risk penalty {rp} out of range [{RP_MIN}, {RP_MAX}]"
        )


def validate_confidence(confidence: float) -> None:
    """Validate confidence is in valid range [0, 1].
    
    Args:
        confidence: Confidence value to validate.
        
    Raises:
        ValueError: If confidence is out of range.
    """
    if not (CONFIDENCE_MIN <= confidence <= CONFIDENCE_MAX):
        raise ValueError(
            f"Confidence {confidence} out of range [{CONFIDENCE_MIN}, {CONFIDENCE_MAX}]"
        )


def validate_band(band: str) -> None:
    """Validate band is a valid recommendation.
    
    Args:
        band: Band value to validate.
        
    Raises:
        ValueError: If band is invalid.
    """
    if band not in VALID_BANDS:
        raise ValueError(
            f"Invalid band '{band}'. Valid bands: {VALID_BANDS}"
        )
