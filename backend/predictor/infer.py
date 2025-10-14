"""
GreyOak Predictor - Inference Module
Compute probabilities, edge, score, and timing bands
"""

import numpy as np
import pandas as pd
import pickle
from pathlib import Path
from typing import Dict, Tuple
import yaml


def load_config():
    """Load predictor configuration"""
    config_path = Path('/app/backend/config/predictor.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_model(model_path: Path) -> Dict:
    """Load trained model artifacts"""
    with open(model_path, 'rb') as f:
        return pickle.load(f)


def predict_probabilities(
    model_artifacts: Dict,
    X: pd.DataFrame
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Predict calibrated probabilities
    
    Args:
        model_artifacts: Dictionary with model and calibrators
        X: Feature DataFrame
    
    Returns:
        Tuple of (p_pos, p_neg, p_neu)
    """
    model = model_artifacts['model']
    cal_pos = model_artifacts['calibrator_pos']
    cal_neg = model_artifacts['calibrator_neg']
    
    # Predict raw probabilities
    y_pred_proba = model.predict(X)
    
    # Calibrate
    p_pos_raw = y_pred_proba[:, 2]  # Class 2 = +1
    p_neg_raw = y_pred_proba[:, 0]  # Class 0 = -1
    
    p_pos = cal_pos.predict(p_pos_raw)
    p_neg = cal_neg.predict(p_neg_raw)
    
    # Ensure probabilities sum <= 1
    p_pos = np.clip(p_pos, 0, 1)
    p_neg = np.clip(p_neg, 0, 1)
    
    total = p_pos + p_neg
    excess = np.maximum(0, total - 1.0)
    p_pos = p_pos - excess / 2
    p_neg = p_neg - excess / 2
    
    p_neu = 1.0 - p_pos - p_neg
    p_neu = np.clip(p_neu, 0, 1)
    
    return p_pos, p_neg, p_neu


def compute_edge_metrics(
    p_pos: np.ndarray,
    p_neg: np.ndarray,
    U: np.ndarray,
    L: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute expected edge, variance, and risk-adjusted edge
    
    Args:
        p_pos: Probability of +1
        p_neg: Probability of -1
        U: Up barrier (return)
        L: Down barrier (return)
    
    Returns:
        Tuple of (E, Var, RA)
    """
    # Expected payoff
    E = p_pos * U - p_neg * L
    
    # Variance
    Var = p_pos * U**2 + p_neg * L**2 - E**2 + 1e-8
    
    # Risk-adjusted edge
    RA = E / (np.sqrt(Var) + 1e-9)
    
    return E, Var, RA


def compute_predictor_score(
    p_pos: np.ndarray,
    RA: np.ndarray,
    w_prob: float = 0.60,
    method: str = 'cross_sectional',
    ts_alpha: float = 0.06
) -> Tuple[np.ndarray, list]:
    """
    Compute PredictorScore (0-100) with z-score mapping
    
    Args:
        p_pos: Probability of +1
        RA: Risk-adjusted edge
        w_prob: Weight for p_pos component
        method: 'cross_sectional' or 'time_series'
        ts_alpha: EWMA alpha for time-series fallback
    
    Returns:
        Tuple of (scores, flags)
    """
    n = len(p_pos)
    
    # Check if cross-sectional z-score is viable
    if method == 'cross_sectional' and n >= 6 and np.std(p_pos) > 1e-6 and np.std(RA) > 1e-6:
        # Cross-sectional z-score
        z_p = (p_pos - np.mean(p_pos)) / (np.std(p_pos) + 1e-9)
        z_ra = (RA - np.mean(RA)) / (np.std(RA) + 1e-9)
        flags = [[] for _ in range(n)]
    else:
        # Time-series fallback (EWMA z-score)
        z_p = ts_ewma_z(pd.Series(p_pos), alpha=ts_alpha).values
        z_ra = ts_ewma_z(pd.Series(RA), alpha=ts_alpha).values
        flags = [['XSctnFallback'] for _ in range(n)]
    
    # Map to points
    P_p = np.clip(50 + 15 * z_p, 0, 100)
    P_ra = np.clip(50 + 15 * z_ra, 0, 100)
    
    # Blend
    base_score = np.round(w_prob * P_p + (1 - w_prob) * P_ra).astype(int)
    
    return base_score, flags


def ts_ewma_z(series: pd.Series, alpha: float = 0.06) -> pd.Series:
    """Time-series EWMA z-score"""
    ewm_mean = series.ewm(alpha=alpha, adjust=False).mean()
    ewm_std = series.ewm(alpha=alpha, adjust=False).std()
    return (series - ewm_mean) / (ewm_std + 1e-9)


def apply_gates(
    base_score: np.ndarray,
    E: np.ndarray,
    RA: np.ndarray,
    E_min: float,
    RA_min: float,
    flags: list
) -> Tuple[np.ndarray, list]:
    """
    Apply amplitude gates
    
    Args:
        base_score: Base predictor scores
        E: Expected edge
        RA: Risk-adjusted edge
        E_min: Minimum E threshold
        RA_min: Minimum RA threshold
        flags: Existing flags list
    
    Returns:
        Tuple of (gated_scores, updated_flags)
    """
    # Check gates
    gate_pass = (E >= E_min) & (RA >= RA_min)
    
    # Cap score if gates fail
    gated_score = np.where(gate_pass, base_score, np.minimum(base_score, 49)).astype(int)
    
    # Update flags
    for i in range(len(flags)):
        if not gate_pass[i]:
            flags[i].append('GateFail')
    
    return gated_score, flags


def determine_timing_band(
    p_pos: np.ndarray,
    p_neg: np.ndarray,
    gate_pass: np.ndarray,
    thresholds: Dict
) -> np.ndarray:
    """
    Determine timing bands
    
    Args:
        p_pos: Probability of +1
        p_neg: Probability of -1
        gate_pass: Boolean array of gate pass status
        thresholds: Dictionary with band thresholds
    
    Returns:
        Array of timing band strings
    """
    n = len(p_pos)
    bands = np.array(['TimingHold'] * n, dtype=object)
    
    # TimingSB (Strong Buy)
    sb_mask = (p_pos >= thresholds['p_pos_min_sb']) & gate_pass
    bands[sb_mask] = 'TimingSB'
    
    # TimingBuy
    buy_mask = (p_pos >= thresholds['p_pos_min_buy']) & gate_pass & ~sb_mask
    bands[buy_mask] = 'TimingBuy'
    
    # TimingAvoid
    avoid_mask = (p_neg >= thresholds['p_neg_min_avoid'])
    bands[avoid_mask] = 'TimingAvoid'
    
    return bands


def adjust_cuts_for_coverage(
    timing_bands: np.ndarray,
    thresholds: Dict,
    config: Dict
) -> Tuple[float, float]:
    """
    Adjust thresholds if coverage caps are breached
    
    Args:
        timing_bands: Array of timing bands
        thresholds: Current thresholds
        config: Configuration with coverage caps
    
    Returns:
        Tuple of (adjusted_sb_cut, adjusted_buy_cut)
    """
    n = len(timing_bands)
    
    sb_share = (timing_bands == 'TimingSB').sum() / n
    buy_share = ((timing_bands == 'TimingBuy') | (timing_bands == 'TimingSB')).sum() / n
    
    sb_cut = thresholds['p_pos_min_sb']
    buy_cut = thresholds['p_pos_min_buy']
    
    # Raise cuts if over coverage caps
    if sb_share > config['coverage_caps']['strong_buy_max']:
        sb_cut += 0.02
    
    if buy_share > config['coverage_caps']['buy_max']:
        buy_cut += 0.02
    
    return sb_cut, buy_cut


def run_inference(
    df: pd.DataFrame,
    model_artifacts: Dict,
    config: Dict = None
) -> pd.DataFrame:
    """
    Run full inference pipeline
    
    Args:
        df: DataFrame with features (must include U, L columns for barriers)
        model_artifacts: Trained model artifacts
        config: Configuration (optional, will load if not provided)
    
    Returns:
        DataFrame with predictions
    """
    if config is None:
        config = load_config()
    
    # Extract features
    feature_cols = model_artifacts['feature_cols']
    X = df[feature_cols].fillna(0)
    
    # Predict probabilities
    p_pos, p_neg, p_neu = predict_probabilities(model_artifacts, X)
    
    # Compute edge metrics
    E, Var, RA = compute_edge_metrics(p_pos, p_neg, df['U'].values, df['L'].values)
    
    # Compute PredictorScore
    w_prob = config['predictor_score']['w_prob']
    base_score, flags = compute_predictor_score(p_pos, RA, w_prob=w_prob)
    
    # Apply gates
    thresholds = config['predictor_score']['thresholds']['DEFAULT']['d20']
    gated_score, flags = apply_gates(
        base_score, E, RA,
        thresholds['E_min'],
        thresholds['RA_min'],
        flags
    )
    
    # Determine timing bands
    gate_pass = (E >= thresholds['E_min']) & (RA >= thresholds['RA_min'])
    timing_bands = determine_timing_band(p_pos, p_neg, gate_pass, thresholds)
    
    # Adjust for coverage (if needed)
    # Note: In production, this would re-classify based on adjusted cuts
    # For MVP, we just note it
    sb_cut, buy_cut = adjust_cuts_for_coverage(timing_bands, thresholds, config)
    
    # Build output DataFrame
    output = df[['date', 'symbol', 'close', 'U', 'L']].copy()
    output['p_pos'] = p_pos
    output['p_neg'] = p_neg
    output['p_neu'] = p_neu
    output['E'] = E
    output['RA'] = RA
    output['predictor_score'] = gated_score
    output['timing_band'] = timing_bands
    output['flags'] = [','.join(f) if f else '' for f in flags]
    output['model_id'] = model_artifacts['model_id']
    
    return output


if __name__ == "__main__":
    print("Inference module loaded successfully")
    print("\nTo run inference:")
    print("  from predictor.infer import run_inference, load_model")
    print("  artifacts = load_model('path/to/model.pkl')")
    print("  results = run_inference(df, artifacts)")
