"""
GreyOak Predictor - Training Module
LightGBM multiclass with purged walk-forward CV and isotonic calibration
"""

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.calibration import CalibratedClassifierCV
from sklearn.isotonic import IsotonicRegression
import pickle
from pathlib import Path
from datetime import datetime
import yaml


def load_config():
    """Load predictor configuration"""
    config_path = Path('/app/backend/config/predictor.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def purged_walk_forward_cv(
    df: pd.DataFrame,
    n_splits: int = 5,
    embargo: int = 20
) -> list:
    """
    Purged walk-forward cross-validation
    
    Args:
        df: DataFrame with date column
        n_splits: Number of CV folds
        embargo: Number of bars to skip after each training set
    
    Returns:
        List of (train_idx, test_idx) tuples
    """
    df = df.sort_values('date').reset_index(drop=True)
    n = len(df)
    
    fold_size = n // (n_splits + 1)
    folds = []
    
    for i in range(n_splits):
        train_end = (i + 1) * fold_size
        test_start = train_end + embargo
        test_end = min(test_start + fold_size, n)
        
        if test_end <= test_start:
            break
        
        train_idx = df.index[:train_end].tolist()
        test_idx = df.index[test_start:test_end].tolist()
        
        folds.append((train_idx, test_idx))
    
    return folds


def train_lgbm_model(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
    config: dict
) -> lgb.Booster:
    """
    Train LightGBM multiclass model
    
    Args:
        X_train: Training features
        y_train: Training labels (-1, 0, +1)
        X_val: Validation features
        y_val: Validation labels
        config: Model configuration
    
    Returns:
        Trained LightGBM model
    """
    # Map labels to 0, 1, 2 for LightGBM
    label_map = {-1: 0, 0: 1, 1: 2}
    y_train_mapped = np.array([label_map[y] for y in y_train])
    y_val_mapped = np.array([label_map[y] for y in y_val])
    
    # Class weights
    weights = config['model']['class_weights']
    sample_weights = np.array([
        weights['neg'] if y == -1 else weights['neu'] if y == 0 else weights['pos']
        for y in y_train
    ])
    
    # Create datasets
    train_data = lgb.Dataset(
        X_train,
        label=y_train_mapped,
        weight=sample_weights
    )
    
    val_data = lgb.Dataset(
        X_val,
        label=y_val_mapped,
        reference=train_data
    )
    
    # Train model
    params = config['model']['lgbm_params'].copy()
    
    model = lgb.train(
        params,
        train_data,
        num_boost_round=300,
        valid_sets=[val_data],
        callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
    )
    
    return model


def isotonic_calibration(
    y_true: np.ndarray,
    y_pred_proba: np.ndarray
) -> tuple:
    """
    Isotonic regression calibration for probabilities
    
    Args:
        y_true: True labels (-1, 0, +1)
        y_pred_proba: Predicted probabilities (n_samples, 3)
    
    Returns:
        Tuple of (calibrator_pos, calibrator_neg)
    """
    # Calibrate P(+1)
    y_binary_pos = (y_true == 1).astype(int)
    cal_pos = IsotonicRegression(out_of_bounds='clip')
    cal_pos.fit(y_pred_proba[:, 2], y_binary_pos)  # class 2 = +1
    
    # Calibrate P(-1)
    y_binary_neg = (y_true == -1).astype(int)
    cal_neg = IsotonicRegression(out_of_bounds='clip')
    cal_neg.fit(y_pred_proba[:, 0], y_binary_neg)  # class 0 = -1
    
    return cal_pos, cal_neg


def train_predictor_model(
    df: pd.DataFrame,
    feature_cols: list,
    save_dir: Path,
    model_id: str = None
) -> dict:
    """
    Full training pipeline with CV and calibration
    
    Args:
        df: DataFrame with features and labels
        feature_cols: List of feature column names
        save_dir: Directory to save model artifacts
        model_id: Optional model identifier
    
    Returns:
        Dictionary with model, calibrators, and metadata
    """
    config = load_config()
    
    print("="*70)
    print("GREYOAK PREDICTOR - TRAINING")
    print("="*70)
    print(f"\nDataset: {len(df)} rows, {len(feature_cols)} features")
    print(f"Label distribution:")
    print(df['label'].value_counts().sort_index())
    
    # Prepare data
    X = df[feature_cols].fillna(0)  # Fill NaN with 0 after standardization
    y = df['label'].values
    
    # Purged walk-forward CV
    print(f"\nRunning {config['model']['cv']['n_splits']}-fold purged WF-CV...")
    folds = purged_walk_forward_cv(
        df,
        n_splits=config['model']['cv']['n_splits'],
        embargo=config['model']['cv']['embargo']
    )
    
    # Store OOF predictions
    oof_probs = np.zeros((len(df), 3))
    oof_probs[:] = np.nan
    
    models = []
    
    for fold_idx, (train_idx, test_idx) in enumerate(folds):
        print(f"\nFold {fold_idx + 1}/{len(folds)}:")
        print(f"  Train: {len(train_idx)} samples")
        print(f"  Test:  {len(test_idx)} samples")
        
        X_train, y_train = X.iloc[train_idx], y[train_idx]
        X_test, y_test = X.iloc[test_idx], y[test_idx]
        
        # Train model
        model = train_lgbm_model(X_train, y_train, X_test, y_test, config)
        models.append(model)
        
        # OOF predictions
        y_pred_proba = model.predict(X_test)
        oof_probs[test_idx] = y_pred_proba
        
        # Metrics
        y_pred = np.argmax(y_pred_proba, axis=1)
        label_map_inv = {0: -1, 1: 0, 2: 1}
        y_pred_labels = np.array([label_map_inv[p] for p in y_pred])
        acc = (y_pred_labels == y_test).mean()
        print(f"  Accuracy: {acc:.3f}")
    
    # Use last fold model as final model
    final_model = models[-1]
    
    # Isotonic calibration on OOF predictions
    print("\nCalibrating probabilities...")
    valid_idx = ~np.isnan(oof_probs[:, 0])
    cal_pos, cal_neg = isotonic_calibration(
        y[valid_idx],
        oof_probs[valid_idx]
    )
    
    # Save artifacts
    save_dir.mkdir(parents=True, exist_ok=True)
    
    if model_id is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_id = f"all_d20_{timestamp}"
    
    artifacts = {
        'model': final_model,
        'calibrator_pos': cal_pos,
        'calibrator_neg': cal_neg,
        'feature_cols': feature_cols,
        'model_id': model_id,
        'config': config,
        'oof_metrics': {
            'n_samples': len(df),
            'label_dist': df['label'].value_counts().to_dict()
        }
    }
    
    # Save
    model_path = save_dir / f"{model_id}.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump(artifacts, f)
    
    print(f"\n✅ Model saved: {model_path}")
    print(f"Model ID: {model_id}")
    
    return artifacts


if __name__ == "__main__":
    print("Training module loaded successfully")
    print("\nTo train a model:")
    print("  from predictor.train import train_predictor_model")
    print("  artifacts = train_predictor_model(df, feature_cols, save_dir)")
