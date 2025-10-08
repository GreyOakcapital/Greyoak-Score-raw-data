"""Risk Penalty Calculator - Section 7.1 of GreyOak Score specification."""

from typing import Dict, Tuple, Literal, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from greyoak_score.core.config_manager import ConfigManager
from greyoak_score.utils.logger import get_logger

logger = get_logger(__name__)


def calculate_risk_penalty(
    ticker: str,
    prices_data: pd.Series,
    fundamentals_data: pd.Series,
    ownership_data: pd.Series,
    sector_group: str,
    mode: Literal["trader", "investor"],
    config: ConfigManager,
    scoring_date: Optional[datetime] = None
) -> Tuple[float, Dict[str, float]]:
    """
    Calculate Risk Penalty (Section 7.1).
    
    RP components (additive, capped by sector):
    1. Liquidity penalty (MTV-based)
    2. Pledge bins (separate from O pillar penalty)
    3. Volatility penalty (stock vs sector sigma)
    4. Event window penalty (earnings/board meetings)
    5. Governance penalty (auditor flags, board resignations)
    
    Args:
        ticker: Stock ticker
        prices_data: Latest price/technical data for stock
        fundamentals_data: Latest fundamental data for stock
        ownership_data: Latest ownership data for stock
        sector_group: Sector classification
        mode: Trading mode ("trader" or "investor")
        config: Configuration manager
        scoring_date: Date for scoring (for event window calculation)
    
    Returns:
        (total_rp, breakdown_dict)
        total_rp: Capped RP value (0-20)
        breakdown_dict: Component breakdown for logging
    """
    if scoring_date is None:
        scoring_date = datetime.now(timezone.utc)
    
    logger.debug(f"Calculating Risk Penalty for {ticker}", extra={
        'ticker': ticker,
        'sector': sector_group,
        'mode': mode
    })
    
    breakdown = {}
    
    # Get RP configuration components
    
    # 1. LIQUIDITY PENALTY (MTV-based)
    mtv_cr = prices_data.get('median_traded_value_cr', np.nan)
    
    if pd.isna(mtv_cr):
        # Estimate from volume and close price if MTV not available
        volume = prices_data.get('volume', 0)
        close = prices_data.get('close', 0)
        if volume > 0 and close > 0:
            # Rough estimate: MTV ≈ volume * close / 10^7 (₹Cr)
            mtv_cr = (volume * close) / 1e7
        else:
            mtv_cr = 0.0
    
    liq_penalty = _calculate_liquidity_penalty(mtv_cr, mode, config)
    breakdown['liquidity'] = liq_penalty
    
    # 2. PLEDGE BINS (for RP, separate from O pillar)
    pledge_frac = ownership_data.get('promoter_pledge_frac', 0.0)
    pledge_penalty = _calculate_pledge_penalty(pledge_frac, config)
    breakdown['pledge'] = pledge_penalty
    
    # 3. VOLATILITY PENALTY
    stock_sigma = prices_data.get('sigma20', np.nan)
    vol_penalty = _calculate_volatility_penalty(stock_sigma, sector_group, config)
    breakdown['volatility'] = vol_penalty
    
    # 4. EVENT WINDOW PENALTY
    event_penalty = _calculate_event_penalty(ticker, fundamentals_data, scoring_date, config)
    breakdown['event'] = event_penalty
    
    # 5. GOVERNANCE PENALTY
    gov_penalty = _calculate_governance_penalty(fundamentals_data, config)
    breakdown['governance'] = gov_penalty
    
    # 6. SUM AND APPLY SECTOR-SPECIFIC CAP
    total_before_cap = sum(breakdown.values())
    
    # Get sector-specific cap
    sector_cap = config.get_rp_cap(sector_group)
    total_rp = min(total_before_cap, sector_cap)
    
    breakdown['total_before_cap'] = total_before_cap
    breakdown['sector_cap'] = sector_cap
    breakdown['total_after_cap'] = total_rp
    
    logger.info(
        f"Risk Penalty calculated: {total_rp:.1f} (capped at {sector_cap})",
        extra={
            'ticker': ticker,
            'rp_total': total_rp,
            'rp_breakdown': breakdown
        }
    )
    
    return total_rp, breakdown


def _calculate_liquidity_penalty(
    mtv_cr: float,
    mode: str,
    config: ConfigManager
) -> float:
    """Calculate liquidity penalty based on MTV (₹Cr)."""
    if pd.isna(mtv_cr) or mtv_cr < 0:
        mtv_cr = 0.0
    
    # Get liquidity penalty bins for mode
    liquidity_bins = config.get_liquidity_penalties(mode)
    
    # Find applicable penalty (bins are sorted descending by threshold)
    for bin_config in liquidity_bins:
        if mtv_cr >= bin_config["threshold"]:
            return float(bin_config["penalty"])
    
    # If no threshold matches, return highest penalty (should not happen)
    return 10.0


def _calculate_pledge_penalty(pledge_frac: float, config: ConfigManager) -> float:
    """Calculate pledge penalty for RP (separate from O pillar penalty)."""
    if pd.isna(pledge_frac) or pledge_frac < 0:
        pledge_frac = 0.0
    
    # Get pledge penalty bins (sorted descending by threshold)
    pledge_bins = config.get_pledge_bins()
    
    # Find applicable penalty
    for bin_config in pledge_bins:
        if pledge_frac > bin_config["threshold"]:
            return float(bin_config["penalty"])
    
    # No penalty if below all thresholds
    return 0.0


def _calculate_volatility_penalty(
    stock_sigma: float,
    sector_group: str,
    config: ConfigManager
) -> float:
    """Calculate volatility penalty (stock vs sector sigma)."""
    if pd.isna(stock_sigma) or stock_sigma <= 0:
        return 0.0
    
    # Get volatility penalty parameters
    vol_params = config.get_volatility_params()
    threshold_multiplier = vol_params.get("multiplier", 2.5)
    penalty = vol_params.get("penalty", 5.0)
    
    # Estimate sector volatility based on sector type
    # TODO: In full implementation, would use actual sector median sigma
    sector_volatility_estimates = {
        "it": 0.02,
        "banks": 0.025,
        "diversified": 0.03,
        "metals": 0.04,
        "energy": 0.035,
        "fmcg": 0.02,
        "pharma": 0.025,
        "psu_banks": 0.03,
        "auto_caps": 0.03
    }
    
    estimated_sector_sigma = sector_volatility_estimates.get(sector_group, 0.03)
    
    if stock_sigma > threshold_multiplier * estimated_sector_sigma:
        return float(penalty)
    else:
        return 0.0


def _calculate_event_penalty(
    ticker: str,
    fundamentals_data: pd.Series,
    scoring_date: datetime,
    config: ConfigManager
) -> float:
    """Calculate event window penalty (earnings/board meetings)."""
    # For this implementation, we'll use a simple heuristic
    # In production, would have actual earnings calendar data
    
    event_params = config.get_event_window_params()
    window_days = event_params.get("days", 2)
    penalty = event_params.get("penalty", 2.0)
    
    # Check if we have quarter_end date
    quarter_end = fundamentals_data.get('quarter_end')
    if pd.isna(quarter_end):
        return 0.0
    
    # Simple heuristic: earnings typically announced 1-2 months after quarter end
    try:
        if isinstance(quarter_end, str):
            quarter_end = pd.to_datetime(quarter_end).date()
        elif hasattr(quarter_end, 'date'):
            quarter_end = quarter_end.date()
        
        # Estimate earnings announcement ~45 days after quarter end
        estimated_earnings_date = pd.Timestamp(quarter_end) + pd.Timedelta(days=45)
        
        days_to_earnings = (estimated_earnings_date.date() - scoring_date.date()).days
        
        if abs(days_to_earnings) <= window_days:
            return float(penalty)
        else:
            return 0.0
    
    except (ValueError, TypeError):
        return 0.0


def _calculate_governance_penalty(fundamentals_data: pd.Series, config: ConfigManager) -> float:
    """Calculate governance penalty (auditor flags, board changes)."""
    # In this implementation, we'll use simple proxies
    # In production, would have actual governance event data
    
    gov_penalty = 0.0
    gov_params = config.get_governance_penalties()
    
    # Check for financial stress indicators as proxy for governance issues
    # Low ROE could indicate governance issues
    roe = fundamentals_data.get('roe_3y', np.nan)
    if not pd.isna(roe) and roe < 0.05:  # Very low ROE
        # Use auditor qualification penalty as proxy for financial stress
        gov_penalty += gov_params.get("auditor_qualification", 2.0)
    
    # Check for high OPM volatility as proxy for management instability
    opm_stdev = fundamentals_data.get('opm_stdev_12q', np.nan)
    if not pd.isna(opm_stdev) and opm_stdev > 0.10:  # High OPM volatility
        gov_penalty += gov_params.get("board_resignation", 1.0)
    
    # Cap at reasonable maximum (use auditor qualification penalty × 2 as max)
    max_penalty = gov_params.get("auditor_qualification", 2.0) * 2
    return min(gov_penalty, max_penalty)


def get_risk_penalty_summary(
    breakdown: Dict[str, float]
) -> str:
    """Generate human-readable summary of risk penalty components."""
    components = []
    
    if breakdown.get('liquidity', 0) > 0:
        components.append(f"Liquidity({breakdown['liquidity']:.0f})")
    
    if breakdown.get('pledge', 0) > 0:
        components.append(f"Pledge({breakdown['pledge']:.0f})")
    
    if breakdown.get('volatility', 0) > 0:
        components.append(f"Volatility({breakdown['volatility']:.0f})")
    
    if breakdown.get('event', 0) > 0:
        components.append(f"Event({breakdown['event']:.0f})")
    
    if breakdown.get('governance', 0) > 0:
        components.append(f"Governance({breakdown['governance']:.0f})")
    
    if components:
        return " + ".join(components) + f" = {breakdown.get('total_after_cap', 0):.0f}"
    else:
        return "No penalties applied"