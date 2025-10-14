"""
GreyOak Predictor Engine - MVP Execution Script
Trains model and runs inference on real NSE data
"""

import sys
sys.path.insert(0, '/app/backend')

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from predictor.labels import generate_labels_for_stock, apply_eligibility_filters
from predictor.features import build_feature_frame, standardize_features, get_feature_columns
from predictor.train import train_predictor_model
from predictor.infer import run_inference, load_model


def load_price_data(data_dir: Path) -> pd.DataFrame:
    """Load price data from validation_data_large directory"""
    print("Loading price data...")
    
    price_files = list(data_dir.glob("*_price_data.csv"))
    print(f"Found {len(price_files)} stock files")
    
    all_data = []
    
    for pf in price_files[:85]:  # Limit to 85 stocks for MVP
        ticker = pf.stem.replace('_price_data', '')
        try:
            df = pd.read_csv(pf)
            
            # Rename columns to standard format
            if 'CH_TIMESTAMP' in df.columns:
                df = df.rename(columns={'CH_TIMESTAMP': 'date'})
            if 'CH_SYMBOL' in df.columns:
                df = df.rename(columns={'CH_SYMBOL': 'symbol'})
            else:
                df['symbol'] = ticker
            
            # Ensure required columns
            required_cols = ['CH_TRADE_HIGH_PRICE', 'CH_TRADE_LOW_PRICE', 
                            'CH_OPENING_PRICE', 'CH_CLOSING_PRICE', 'CH_TOT_TRADED_QTY']
            
            if all(col in df.columns for col in required_cols):
                df = df.rename(columns={
                    'CH_TRADE_HIGH_PRICE': 'high',
                    'CH_TRADE_LOW_PRICE': 'low',
                    'CH_OPENING_PRICE': 'open',
                    'CH_CLOSING_PRICE': 'close',
                    'CH_TOT_TRADED_QTY': 'volume'
                })
                
                df['date'] = pd.to_datetime(df['date'])
                df = df[['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
                all_data.append(df)
                
        except Exception as e:
            print(f"  Error loading {ticker}: {e}")
    
    combined = pd.concat(all_data, ignore_index=True)
    combined = combined.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    print(f"✅ Loaded {len(combined)} price records for {combined['symbol'].nunique()} stocks")
    return combined


def prepare_training_data(prices_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare labeled training dataset"""
    print("\nPreparing training data...")
    
    all_labeled = []
    
    for symbol in prices_df['symbol'].unique():
        stock_df = prices_df[prices_df['symbol'] == symbol].copy()
        
        # Generate labels
        try:
            labeled = generate_labels_for_stock(stock_df, horizon=20, k=1.8)
            
            # Build features
            labeled = build_feature_frame(labeled)
            
            # Apply eligibility filters
            labeled = apply_eligibility_filters(labeled)
            
            if len(labeled) > 50:  # Need minimum data
                all_labeled.append(labeled)
                
        except Exception as e:
            print(f"  Error processing {symbol}: {e}")
    
    combined = pd.concat(all_labeled, ignore_index=True)
    combined = combined.sort_values(['date', 'symbol']).reset_index(drop=True)
    
    print(f"✅ Generated {len(combined)} labeled samples")
    print(f"   Label distribution:")
    print(combined['label'].value_counts().sort_index())
    
    return combined


def main():
    """Main execution pipeline"""
    print("="*70)
    print(" "*15 + "GREYOAK PREDICTOR ENGINE - MVP")
    print("="*70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Paths
    data_dir = Path("/app/backend/validation_data_large")
    output_dir = Path("/app/backend/predictor_output")
    output_dir.mkdir(exist_ok=True)
    
    # Step 1: Load data
    print("\n" + "="*70)
    print("STEP 1: LOAD DATA")
    print("="*70)
    prices_df = load_price_data(data_dir)
    
    # Step 2: Prepare training data (labels + features)
    print("\n" + "="*70)
    print("STEP 2: PREPARE TRAINING DATA")
    print("="*70)
    training_df = prepare_training_data(prices_df)
    
    # Step 3: Standardize features
    print("\n" + "="*70)
    print("STEP 3: STANDARDIZE FEATURES")
    print("="*70)
    feature_cols = get_feature_columns()
    print(f"Features: {', '.join(feature_cols)}")
    
    training_df = standardize_features(
        training_df,
        feature_cols,
        method='cross_sectional',
        min_stocks=6
    )
    
    # Step 4: Train model
    print("\n" + "="*70)
    print("STEP 4: TRAIN MODEL")
    print("="*70)
    
    model_artifacts = train_predictor_model(
        training_df,
        feature_cols,
        save_dir=output_dir,
        model_id=None
    )
    
    # Step 5: Run inference on latest data
    print("\n" + "="*70)
    print("STEP 5: RUN INFERENCE")
    print("="*70)
    
    # Get latest date for each stock
    latest_df = training_df.sort_values('date').groupby('symbol').tail(1).copy()
    print(f"Running inference on {len(latest_df)} stocks (latest date per stock)")
    
    predictions = run_inference(latest_df, model_artifacts)
    
    # Step 6: Save results
    print("\n" + "="*70)
    print("STEP 6: SAVE RESULTS")
    print("="*70)
    
    # Save predictions
    predictions_file = output_dir / 'predictor_predictions.parquet'
    predictions.to_parquet(predictions_file, index=False)
    print(f"✅ Predictions saved: {predictions_file}")
    
    # Save CSV for easy viewing
    predictions_csv = output_dir / 'predictor_predictions.csv'
    predictions.to_csv(predictions_csv, index=False)
    print(f"✅ CSV saved: {predictions_csv}")
    
    # Step 7: Summary statistics
    print("\n" + "="*70)
    print("SUMMARY STATISTICS")
    print("="*70)
    
    print(f"\n📊 Timing Band Distribution:")
    band_counts = predictions['timing_band'].value_counts()
    for band, count in band_counts.items():
        pct = count / len(predictions) * 100
        print(f"   {band:15} {count:3d} ({pct:5.1f}%)")
    
    print(f"\n📊 Score Distribution:")
    print(f"   Mean:   {predictions['predictor_score'].mean():.1f}")
    print(f"   Median: {predictions['predictor_score'].median():.1f}")
    print(f"   Min:    {predictions['predictor_score'].min()}")
    print(f"   Max:    {predictions['predictor_score'].max()}")
    
    print(f"\n📊 Top 10 Strong Buys:")
    strong_buys = predictions[predictions['timing_band'] == 'TimingSB'].nlargest(10, 'predictor_score')
    if len(strong_buys) > 0:
        print(strong_buys[['symbol', 'predictor_score', 'p_pos', 'E', 'RA']].to_string(index=False))
    else:
        print("   No Strong Buy signals")
    
    print(f"\n📊 Flags Summary:")
    flag_counts = predictions['flags'].value_counts()
    for flag, count in flag_counts.items():
        if flag:
            print(f"   {flag}: {count}")
    
    print(f"\n{'='*70}")
    print("✅ PREDICTOR MVP COMPLETE")
    print("="*70)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n📁 Output directory: {output_dir}")
    print(f"   - Model: {output_dir / f'{model_artifacts[\"model_id\"]}.pkl'}")
    print(f"   - Predictions: {predictions_file}")
    print(f"   - CSV: {predictions_csv}")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
