"""Final Scoring & Banding Engine - Section 6 of GreyOak Score specification.

Orchestrates the complete scoring pipeline:
1. Calculate all six pillars (F, T, R, O, Q, S)
2. Apply pillar weights for sector/mode
3. Calculate risk penalty
4. Subtract RP from weighted score
5. Apply sequential guardrails 
6. Generate final score and band
7. Return complete ScoreOutput with metadata
"""

from typing import Dict, Any, Optional, Tuple, Literal
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

from greyoak_score.core.config_manager import ConfigManager
from greyoak_score.core.risk_penalty import calculate_risk_penalty
from greyoak_score.core.guardrails import apply_guardrails
# Pillar imports removed - scores are now provided as input
from greyoak_score.data.models import ScoreOutput, PillarScores
from greyoak_score.utils.logger import get_logger

logger = get_logger(__name__)


def calculate_greyoak_score(
    ticker: str,
    pillar_scores: Dict[str, float],  # Pre-calculated pillar scores {F: 75.0, T: 80.0, ...}
    prices_data: pd.Series,
    fundamentals_data: pd.Series, 
    ownership_data: pd.Series,
    sector_group: str,
    mode: Literal["trader", "investor"],
    config: ConfigManager,
    s_z: float = 0.0,  # Sector momentum z-score (for guardrails)
    scoring_date: Optional[datetime] = None
) -> ScoreOutput:
    """
    Calculate complete GreyOak Score from pre-calculated pillars, RP, and guardrails.
    
    This is the main scoring orchestrator that combines pillar scores with weights,
    calculates risk penalty, applies guardrails, and generates final score.
    
    Args:
        ticker: Stock ticker symbol
        pillar_scores: Pre-calculated pillar scores {F: 75.0, T: 80.0, R: 70.0, O: 85.0, Q: 78.0, S: 82.0}
        prices_data: Latest price/technical data for the stock
        fundamentals_data: Latest fundamental data for the stock
        ownership_data: Latest ownership/promoter data for the stock
        sector_group: Sector classification (e.g., "it", "banks", "metals")
        mode: Trading mode ("trader" or "investor")
        config: Configuration manager instance
        s_z: Sector momentum z-score (for SectorBear guardrail)
        scoring_date: Date for scoring (defaults to current UTC time)
        
    Returns:
        ScoreOutput: Complete score results with metadata
        
    Raises:
        ValueError: If required data is missing or invalid
        KeyError: If sector/mode configuration is not found
    """
    if scoring_date is None:
        scoring_date = datetime.now(timezone.utc)
    
    logger.info(f"Starting GreyOak Score calculation for {ticker}", extra={
        'ticker': ticker,
        'sector': sector_group,
        'mode': mode,
        'scoring_date': scoring_date.isoformat()
    })
    
    # Validate inputs
    _validate_inputs(ticker, prices_data, fundamentals_data, ownership_data, sector_group, mode)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 1: Extract pillar scores from input
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    logger.debug(f"Using provided pillar scores for {ticker}")
    
    pillar_f = pillar_scores.get('F', 50.0)
    pillar_t = pillar_scores.get('T', 50.0)
    pillar_r = pillar_scores.get('R', 50.0)
    pillar_o = pillar_scores.get('O', 50.0)
    pillar_q = pillar_scores.get('Q', 50.0)
    pillar_s = pillar_scores.get('S', 50.0)
    
    pillars = PillarScores(
        F=round(pillar_f, 2),
        T=round(pillar_t, 2), 
        R=round(pillar_r, 2),
        O=round(pillar_o, 2),
        Q=round(pillar_q, 2),
        S=round(pillar_s, 2)
    )
    
    logger.debug(f"Pillars calculated: F={pillars.F}, T={pillars.T}, R={pillars.R}, O={pillars.O}, Q={pillars.Q}, S={pillars.S}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 2: Apply pillar weights for sector/mode
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    weights = config.get_pillar_weights(sector_group, mode)
    
    weighted_score = (
        pillars.F * weights['F'] +
        pillars.T * weights['T'] +
        pillars.R * weights['R'] + 
        pillars.O * weights['O'] +
        pillars.Q * weights['Q'] +
        pillars.S * weights['S']
    )
    
    logger.debug(f"Weighted score: {weighted_score:.2f} (weights: {weights})")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 3: Calculate risk penalty
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    risk_penalty, rp_breakdown = calculate_risk_penalty(
        ticker=ticker,
        prices_data=prices_data,
        fundamentals_data=fundamentals_data,
        ownership_data=ownership_data,
        sector_group=sector_group,
        mode=mode,
        config=config,
        scoring_date=scoring_date
    )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 4: Subtract RP from weighted score
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    score_pre_guard = max(0.0, weighted_score - risk_penalty)
    
    logger.debug(f"Score after RP: {score_pre_guard:.2f} (was {weighted_score:.2f}, RP={risk_penalty:.1f})")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 5: Calculate confidence and imputation metrics
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    confidence, imputed_fraction = _calculate_data_quality_metrics(
        prices_data, fundamentals_data, ownership_data
    )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 6: Apply sequential guardrails 
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    final_score, final_band, guardrail_flags = apply_guardrails(
        score_pre_guard=score_pre_guard,
        ticker=ticker,
        prices_data=prices_data,
        fundamentals_data=fundamentals_data,
        ownership_data=ownership_data,
        sector_group=sector_group,
        mode=mode,
        config=config,
        confidence=confidence,
        imputed_fraction=imputed_fraction,
        s_z=s_z,
        risk_penalty=risk_penalty
    )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 7: Package results
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    score_output = ScoreOutput(
        ticker=ticker,
        date=scoring_date.date(),  # Use date for scoring_date field
        score=round(final_score, 2),
        band=final_band,
        pillars=pillars,
        risk_penalty=round(risk_penalty, 2),
        guardrail_flags=guardrail_flags,
        confidence=round(confidence, 3),
        s_z=round(s_z, 3),
        mode=mode.capitalize(),  # Capitalize mode
        as_of=scoring_date,
        config_hash=config.config_hash
    )
    
    logger.info(
        f"GreyOak Score calculated for {ticker}: {final_score:.2f} ({final_band})",
        extra={
            'ticker': ticker,
            'score': final_score,
            'band': final_band,
            'risk_penalty': risk_penalty,
            'guardrail_flags': guardrail_flags,
            'confidence': confidence,
            's_z': s_z
        }
    )
    
    return score_output


def _validate_inputs(
    ticker: str,
    prices_data: pd.Series,
    fundamentals_data: pd.Series,
    ownership_data: pd.Series,
    sector_group: str,
    mode: str
) -> None:
    """Validate required inputs for scoring."""
    if not ticker or not isinstance(ticker, str):
        raise ValueError("Ticker must be a non-empty string")
    
    if not isinstance(prices_data, pd.Series):
        raise ValueError("prices_data must be a pandas Series")
    
    if not isinstance(fundamentals_data, pd.Series):
        raise ValueError("fundamentals_data must be a pandas Series")
    
    if not isinstance(ownership_data, pd.Series):
        raise ValueError("ownership_data must be a pandas Series")
    
    if sector_group not in ["it", "banks", "metals", "energy", "fmcg", "pharma", "psu_banks", "auto_caps", "diversified"]:
        raise ValueError(f"Invalid sector_group: {sector_group}")
    
    if mode not in ["trader", "investor"]:
        raise ValueError(f"Invalid mode: {mode}. Must be 'trader' or 'investor'")


def _calculate_data_quality_metrics(
    prices_data: pd.Series,
    fundamentals_data: pd.Series,
    ownership_data: pd.Series
) -> Tuple[float, float]:
    """
    Calculate confidence and imputation fraction from data quality.
    
    Args:
        prices_data: Price/technical data
        fundamentals_data: Fundamental data  
        ownership_data: Ownership data
        
    Returns:
        (confidence, imputed_fraction)
        confidence: Overall data confidence [0, 1]
        imputed_fraction: Fraction of data that was imputed [0, 1]
    """
    # Required fields for each data type
    required_price_fields = ['close', 'volume', 'rsi_14', 'atr_20', 'dma20', 'dma200']
    required_fundamental_fields = ['market_cap_cr', 'roe_3y', 'sales_cagr_3y']
    required_ownership_fields = ['promoter_holding_pct', 'fii_holding_pct']
    
    all_required_fields = required_price_fields + required_fundamental_fields + required_ownership_fields
    
    # Count available and missing data
    available_count = 0
    imputed_count = 0
    
    # Check price data
    for field in required_price_fields:
        value = prices_data.get(field, np.nan)
        if pd.notna(value):
            available_count += 1
        else:
            imputed_count += 1
    
    # Check fundamental data
    for field in required_fundamental_fields:
        value = fundamentals_data.get(field, np.nan)
        if pd.notna(value):
            available_count += 1
        else:
            imputed_count += 1
    
    # Check ownership data
    for field in required_ownership_fields:
        value = ownership_data.get(field, np.nan)
        if pd.notna(value):
            available_count += 1
        else:
            imputed_count += 1
    
    total_fields = len(all_required_fields)
    
    # Calculate metrics
    confidence = available_count / total_fields
    imputed_fraction = imputed_count / total_fields
    
    return confidence, imputed_fraction


# score_multiple_stocks function removed for simplicity


def get_score_explanation(score_output: ScoreOutput) -> Dict[str, str]:
    """
    Generate detailed explanation of how the score was calculated.
    
    Args:
        score_output: Complete score results
        
    Returns:
        Dict with explanation components
    """
    explanations = {}
    
    # Pillar contributions
    explanations['pillars'] = (
        f"Fundamentals: {score_output.pillars.F}/100, "
        f"Technicals: {score_output.pillars.T}/100, "
        f"Relative Strength: {score_output.pillars.R}/100, "
        f"Ownership: {score_output.pillars.O}/100, "
        f"Quality: {score_output.pillars.Q}/100, "
        f"Sector Momentum: {score_output.pillars.S}/100"
    )
    
    # Risk penalty impact
    if score_output.risk_penalty > 0:
        explanations['risk_penalty'] = f"Risk penalty of {score_output.risk_penalty} points applied"
    else:
        explanations['risk_penalty'] = "No risk penalty applied"
    
    # Guardrail impacts
    if score_output.guardrail_flags:
        explanations['guardrails'] = f"Guardrails triggered: {', '.join(score_output.guardrail_flags)}"
    else:
        explanations['guardrails'] = "No guardrails triggered"
    
    # Data quality
    explanations['data_quality'] = f"Data confidence: {score_output.confidence:.1%}"
    
    # Sector momentum
    if score_output.s_z > 0:
        explanations['sector_momentum'] = f"Sector showing positive momentum (z-score: {score_output.s_z:.2f})"
    else:
        explanations['sector_momentum'] = f"Sector showing negative momentum (z-score: {score_output.s_z:.2f})"
    
    return explanations


def compare_scores(
    score_outputs: Dict[str, ScoreOutput],
    sort_by: Literal["score", "band", "confidence"] = "score"
) -> pd.DataFrame:
    """
    Compare multiple score outputs in a tabular format.
    
    Args:
        score_outputs: Dict mapping ticker to ScoreOutput
        sort_by: Field to sort by
        
    Returns:
        DataFrame with comparison table
    """
    data = []
    
    for ticker, output in score_outputs.items():
        data.append({
            'Ticker': ticker,
            'Score': output.score,
            'Band': output.band,
            'F': output.pillars.F,
            'T': output.pillars.T, 
            'R': output.pillars.R,
            'O': output.pillars.O,
            'Q': output.pillars.Q,
            'S': output.pillars.S,
            'RP': output.risk_penalty,
            'Flags': len(output.guardrail_flags),
            'Confidence': output.confidence
        })
    
    df = pd.DataFrame(data)
    
    # Sort by specified field
    if sort_by == "score":
        df = df.sort_values('Score', ascending=False)
    elif sort_by == "band":
        band_order = {"Strong Buy": 4, "Buy": 3, "Hold": 2, "Avoid": 1}
        df['band_order'] = df['Band'].map(band_order)
        df = df.sort_values('band_order', ascending=False).drop('band_order', axis=1)
    elif sort_by == "confidence":
        df = df.sort_values('Confidence', ascending=False)
    
    return df.reset_index(drop=True)