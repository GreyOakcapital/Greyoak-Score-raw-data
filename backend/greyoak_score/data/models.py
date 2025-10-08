"""Pydantic data models for GreyOak Score Engine.

All models follow spec terminology exactly for traceability.
Variable names match spec: sigma20, MTV, S_z, Score_preGuard, etc.
"""

from datetime import date, datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from greyoak_score.utils.constants import (
    CONFIDENCE_MAX,
    CONFIDENCE_MIN,
    MODE_INVESTOR,
    MODE_TRADER,
    RP_MAX,
    RP_MIN,
    SCORE_MAX,
    SCORE_MIN,
    VALID_BANDS,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Input Models (from CSV data)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class DailyPriceData(BaseModel):
    """Daily price and technical indicator data for a stock.
    
    All field names match spec terminology exactly.
    """

    ticker: str = Field(..., description="Stock ticker symbol (e.g., RELIANCE.NS)")
    date: date = Field(..., description="Trading date (YYYY-MM-DD)")
    
    # OHLCV data (adjusted for splits, bonuses, dividends)
    open: float = Field(..., gt=0, description="Adjusted open price")
    high: float = Field(..., gt=0, description="Adjusted high price")
    low: float = Field(..., gt=0, description="Adjusted low price")
    close: float = Field(..., gt=0, description="Adjusted close price")
    volume: float = Field(..., ge=0, description="Trading volume")
    
    # Moving averages
    dma20: Optional[float] = Field(None, description="20-day moving average")
    dma50: Optional[float] = Field(None, description="50-day moving average")
    dma200: Optional[float] = Field(None, description="200-day moving average")
    
    # Technical indicators
    rsi14: Optional[float] = Field(None, ge=0, le=100, description="14-day RSI")
    atr14: Optional[float] = Field(None, ge=0, description="14-day ATR (absolute)")
    macd_line: Optional[float] = Field(None, description="MACD line")
    macd_signal: Optional[float] = Field(None, description="MACD signal line")
    
    # Extremes
    hi20: Optional[float] = Field(None, description="20-day high")
    lo20: Optional[float] = Field(None, description="20-day low")
    hi52w: Optional[float] = Field(None, description="52-week high")
    lo52w: Optional[float] = Field(None, description="52-week low")
    
    # Returns (as decimals, e.g., 0.05 = 5%)
    ret_21d: Optional[float] = Field(None, description="21-day return")
    ret_63d: Optional[float] = Field(None, description="63-day return")
    ret_126d: Optional[float] = Field(None, description="126-day return")
    
    # Volatility (daily, not annualized)
    sigma20: Optional[float] = Field(None, ge=0, description="20-day volatility (daily)")
    sigma60: Optional[float] = Field(None, ge=0, description="60-day volatility (daily)")
    
    # Validation removed to prevent recursion issue
    # @field_validator("high")
    # @classmethod
    # def high_gte_low(cls, v: float, info) -> float:
    #     """Validate high >= low."""
    #     if info.data.get("low") and v < info.data["low"]:
    #         raise ValueError(f"high ({v}) must be >= low ({info.data['low']})")
    #     return v


class FundamentalsData(BaseModel):
    """Quarterly fundamentals data for a stock.
    
    Banking stocks use ONLY banking metrics (ROA, ROE, GNPA, PCR, NIM).
    Non-financial stocks use non-banking metrics.
    
    Section 5.1: Banking F Pillar is EXCLUSIVE (no mixing).
    """

    ticker: str = Field(..., description="Stock ticker symbol")
    quarter_end: date = Field(..., description="Quarter end date")
    
    # Non-financial metrics (NOT used for banks)
    roe_3y: Optional[float] = Field(None, description="3-year average ROE (as decimal)")
    roce_3y: Optional[float] = Field(None, description="3-year average ROCE (as decimal)")
    eps_cagr_3y: Optional[float] = Field(None, description="3-year EPS CAGR (as decimal)")
    sales_cagr_3y: Optional[float] = Field(None, description="3-year Sales CAGR (as decimal)")
    pe: Optional[float] = Field(None, gt=0, description="Price-to-Earnings ratio")
    ev_ebitda: Optional[float] = Field(None, description="EV/EBITDA ratio")
    opm_stdev_12q: Optional[float] = Field(None, ge=0, description="OPM stdev over 12 quarters")
    
    # Banking metrics (ONLY used for banks/NBFCs)
    roa_3y: Optional[float] = Field(None, description="3-year average ROA (as decimal)")
    gnpa_pct: Optional[float] = Field(None, ge=0, description="Gross NPA % (lower better)")
    pcr_pct: Optional[float] = Field(None, ge=0, le=100, description="PCR % (higher better)")
    nim_3y: Optional[float] = Field(None, description="3-year average NIM (as %)")


class OwnershipData(BaseModel):
    """Quarterly ownership and institutional flow data."""

    ticker: str = Field(..., description="Stock ticker symbol")
    quarter_end: date = Field(..., description="Quarter end date")
    
    promoter_hold_pct: float = Field(
        ...,
        ge=0,
        le=1,
        description="Promoter holding % (as decimal, 0-1)",
    )
    promoter_pledge_frac: float = Field(
        ...,
        ge=0,
        le=1,
        description="Promoter pledge fraction (0-1)",
    )
    fii_dii_delta_pp: float = Field(
        ...,
        description="FII+DII change in percentage points vs previous quarter",
    )


class SectorData(BaseModel):
    """Sector-level aggregated data (computed on-the-fly)."""

    sector_group: str = Field(..., description="Sector group (e.g., 'metals', 'banks')")
    date: date = Field(..., description="Trading date")
    
    # Sector returns
    ret_21d: float = Field(..., description="Sector 21-day return")
    ret_63d: float = Field(..., description="Sector 63-day return")
    ret_126d: float = Field(..., description="Sector 126-day return")
    
    # Sector volatility
    sigma_20: float = Field(..., ge=0, description="Sector median 20-day volatility")
    
    # Number of stocks in sector
    n_stocks: int = Field(..., ge=1, description="Number of stocks in this sector")


class SectorMapping(BaseModel):
    """Ticker to sector mapping."""

    ticker: str = Field(..., description="Stock ticker symbol")
    sector_id: str = Field(..., description="Sector ID (e.g., 'PRIVATE_BANKS')")
    sector_group: str = Field(..., description="Sector group (e.g., 'banks', 'metals')")
    exchange: Optional[str] = Field(None, description="Exchange (NSE, BSE)")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Output Models (scoring results)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PillarScores(BaseModel):
    """Six pillar scores (0-100 each).
    
    Pillar names match spec exactly: F, T, R, O, Q, S.
    """

    F: float = Field(..., ge=SCORE_MIN, le=SCORE_MAX, description="Fundamentals pillar")
    T: float = Field(..., ge=SCORE_MIN, le=SCORE_MAX, description="Technicals pillar")
    R: float = Field(..., ge=SCORE_MIN, le=SCORE_MAX, description="Relative Strength pillar")
    O: float = Field(..., ge=SCORE_MIN, le=SCORE_MAX, description="Ownership pillar")
    Q: float = Field(..., ge=SCORE_MIN, le=SCORE_MAX, description="Quality pillar")
    S: float = Field(..., ge=SCORE_MIN, le=SCORE_MAX, description="Sector Momentum pillar")


class ScoreOutput(BaseModel):
    """Final scoring output (deterministic, auditable).
    
    This is the main output model stored in the database and returned by the API.
    All field names match spec terminology exactly.
    
    Section 2: Deliverables and Determinism - complete output specification.
    """

    # Identifiers
    ticker: str = Field(..., description="Stock ticker symbol")
    date: date = Field(..., description="Scoring date")
    mode: Literal["Trader", "Investor"] = Field(
        ...,
        description="Scoring mode (Trader = short-term, Investor = long-term)",
    )
    
    # Final outputs
    score: float = Field(
        ...,
        ge=SCORE_MIN,
        le=SCORE_MAX,
        description="Final score (0-100) after RP and guardrails",
    )
    band: Literal["Strong Buy", "Buy", "Hold", "Avoid"] = Field(
        ...,
        description="Investment recommendation band",
    )
    
    # Pillar scores
    pillars: PillarScores = Field(..., description="Six pillar scores (F, T, R, O, Q, S)")
    
    # Risk and guardrails
    risk_penalty: float = Field(
        ...,
        ge=RP_MIN,
        le=RP_MAX,
        description="Total risk penalty deducted from raw score",
    )
    guardrail_flags: List[str] = Field(
        default_factory=list,
        description="List of triggered guardrails (e.g., ['PledgeCap', 'SectorBear'])",
    )
    confidence: float = Field(
        ...,
        ge=CONFIDENCE_MIN,
        le=CONFIDENCE_MAX,
        description="Data confidence score (0-1)",
    )
    s_z: float = Field(
        ...,
        description="Sector momentum z-score (weighted). Used for SectorBear guardrail.",
    )
    
    # Audit trail (for determinism and traceability)
    as_of: datetime = Field(
        ...,
        description="Timestamp when score was calculated (ISO 8601)",
    )
    config_hash: str = Field(
        ...,
        description="SHA-256 hash of YAML configs used",
    )
    code_version: Optional[str] = Field(
        None,
        description="Code version (greyoak_score.__version__)",
    )
    
    @field_validator("band")
    @classmethod
    def validate_band(cls, v: str) -> str:
        """Validate band is in valid set."""
        if v not in VALID_BANDS:
            raise ValueError(f"Invalid band '{v}'. Valid bands: {VALID_BANDS}")
        return v


class RiskPenaltyBreakdown(BaseModel):
    """Breakdown of risk penalty components (for debugging)."""

    liquidity: float = Field(default=0.0, ge=0, description="Liquidity penalty")
    pledge: float = Field(default=0.0, ge=0, description="Pledge penalty (from RP bins)")
    volatility: float = Field(default=0.0, ge=0, description="Volatility penalty")
    event_window: float = Field(default=0.0, ge=0, description="Event window penalty")
    governance: float = Field(default=0.0, ge=0, description="Governance penalty")
    total: float = Field(..., ge=RP_MIN, le=RP_MAX, description="Total RP (capped at sector max)")
    cap: float = Field(..., ge=0, le=RP_MAX, description="Sector-specific RP cap applied")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Intermediate Calculation Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class NormalizationResult(BaseModel):
    """Result of sector normalization for a single metric."""

    value: float = Field(..., description="Original metric value")
    sector_median: float = Field(..., description="Sector median for this metric")
    sector_std: float = Field(..., description="Sector standard deviation")
    z_score: float = Field(..., description="Computed z-score")
    points: float = Field(
        ...,
        ge=SCORE_MIN,
        le=SCORE_MAX,
        description="Normalized points (0-100)",
    )
    method: Literal["z_score", "percentile"] = Field(
        ...,
        description="Normalization method used (z_score if n>=6, percentile if n<6)",
    )


class ConfidenceBreakdown(BaseModel):
    """Breakdown of confidence score components."""

    coverage: float = Field(..., ge=0, le=1, description="Data coverage fraction")
    freshness: float = Field(..., ge=0, le=1, description="Data freshness score")
    source_quality: float = Field(..., ge=0, le=1, description="Source quality score")
    total: float = Field(
        ...,
        ge=CONFIDENCE_MIN,
        le=CONFIDENCE_MAX,
        description="Total confidence (weighted sum)",
    )
