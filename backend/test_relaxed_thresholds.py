"""
Test Predictor with Relaxed Thresholds
"""

import sys
sys.path.insert(0, '/app/backend')

import pandas as pd
import numpy as np
from pathlib import Path
from predictor.infer import load_model, run_inference, load_config

print("="*70)
print("TESTING RELAXED THRESHOLDS")
print("="*70)

# Load config
config = load_config()
print("\n📋 New Configuration:")
print(f"   E_min: {config['predictor_score']['thresholds']['DEFAULT']['d20']['E_min']}")
print(f"   RA_min: {config['predictor_score']['thresholds']['DEFAULT']['d20']['RA_min']}")
print(f"   p_pos_min_sb: {config['predictor_score']['thresholds']['DEFAULT']['d20']['p_pos_min_sb']}")
print(f"   p_pos_min_buy: {config['predictor_score']['thresholds']['DEFAULT']['d20']['p_pos_min_buy']}")
print(f"   k_static: {config['barriers']['k_static']}")

# Load model
output_dir = Path("/app/backend/predictor_output")
model_files = list(output_dir.glob("all_d20_*.pkl"))
if not model_files:
    print("❌ No model found!")
    sys.exit(1)

model_path = sorted(model_files)[-1]
print(f"\n📊 Loading model: {model_path.name}")
model_artifacts = load_model(model_path)

# Load the prepared data (we need the features)
# Since we already have trained data, let's reload it
training_data_file = output_dir / "training_data.parquet"

if training_data_file.exists():
    print(f"✅ Loading cached training data")
    df = pd.read_parquet(training_data_file)
else:
    print("⚠️  Training data not cached, loading from scratch...")
    from predictor.labels import generate_labels_for_stock, apply_eligibility_filters, calculate_barriers
    from predictor.features import build_feature_frame, standardize_features, get_feature_columns
    
    # Load price data
    data_dir = Path("/app/backend/validation_data_large")
    price_files = list(data_dir.glob("*_price_data.csv"))[:85]
    
    all_data = []
    for pf in price_files:
        ticker = pf.stem.replace('_price_data', '')
        try:
            df_temp = pd.read_csv(pf)
            if 'CH_TIMESTAMP' in df_temp.columns:
                df_temp = df_temp.rename(columns={'CH_TIMESTAMP': 'date'})
            if 'CH_SYMBOL' in df_temp.columns:
                df_temp = df_temp.rename(columns={'CH_SYMBOL': 'symbol'})
            else:
                df_temp['symbol'] = ticker
            
            required_cols = ['CH_TRADE_HIGH_PRICE', 'CH_TRADE_LOW_PRICE', 
                            'CH_OPENING_PRICE', 'CH_CLOSING_PRICE', 'CH_TOT_TRADED_QTY']
            
            if all(col in df_temp.columns for col in required_cols):
                df_temp = df_temp.rename(columns={
                    'CH_TRADE_HIGH_PRICE': 'high',
                    'CH_TRADE_LOW_PRICE': 'low',
                    'CH_OPENING_PRICE': 'open',
                    'CH_CLOSING_PRICE': 'close',
                    'CH_TOT_TRADED_QTY': 'volume'
                })
                
                df_temp['date'] = pd.to_datetime(df_temp['date'])
                df_temp = df_temp[['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
                
                # Generate labels with NEW k_static
                labeled = generate_labels_for_stock(df_temp, horizon=20, k=config['barriers']['k_static'])
                labeled = build_feature_frame(labeled)
                labeled = apply_eligibility_filters(labeled)
                
                if len(labeled) > 50:
                    all_data.append(labeled)
        except Exception as e:
            pass
    
    df = pd.concat(all_data, ignore_index=True)
    df = df.sort_values(['date', 'symbol']).reset_index(drop=True)
    
    # Standardize features
    feature_cols = get_feature_columns()
    df = standardize_features(df, feature_cols, method='cross_sectional', min_stocks=6)
    
    # Cache for next time
    df.to_parquet(training_data_file, index=False)
    print(f"✅ Cached training data")

print(f"\n✅ Loaded data: {len(df)} samples")

# Get latest data for each stock
latest_df = df.sort_values('date').groupby('symbol').tail(1).copy()
print(f"📊 Running inference on {len(latest_df)} stocks (latest per stock)")

# Re-calculate barriers with new k
from predictor.labels import calculate_barriers
latest_df = calculate_barriers(latest_df, k=config['barriers']['k_static'])

# Run inference with new config
predictions = run_inference(latest_df, model_artifacts, config)

# Save updated predictions
predictions.to_parquet(output_dir / 'predictor_predictions_relaxed.parquet', index=False)
predictions.to_csv(output_dir / 'predictor_predictions_relaxed.csv', index=False)

print(f"\n✅ Saved predictions with relaxed thresholds")

# Analyze results
print("\n" + "="*70)
print("RESULTS WITH RELAXED THRESHOLDS")
print("="*70)

print(f"\n📊 Timing Band Distribution:")
band_counts = predictions['timing_band'].value_counts()
for band, count in band_counts.items():
    pct = count / len(predictions) * 100
    print(f"   {band:15} {count:3d} ({pct:5.1f}%)")

print(f"\n📊 Score Statistics:")
print(f"   Mean:   {predictions['predictor_score'].mean():.1f}")
print(f"   Median: {predictions['predictor_score'].median():.1f}")
print(f"   Min:    {predictions['predictor_score'].min()}")
print(f"   Max:    {predictions['predictor_score'].max()}")
print(f"   Scores ≥60: {(predictions['predictor_score'] >= 60).sum()}")
print(f"   Scores ≥70: {(predictions['predictor_score'] >= 70).sum()}")

# Show Strong Buys if any
strong_buys = predictions[predictions['timing_band'] == 'TimingSB']
if len(strong_buys) > 0:
    print(f"\n🎯 STRONG BUY SIGNALS ({len(strong_buys)}):")
    print(strong_buys.nlargest(10, 'predictor_score')[
        ['symbol', 'predictor_score', 'p_pos', 'E', 'RA', 'flags']
    ].to_string(index=False))
else:
    print(f"\n⚠️  No Strong Buy signals")

# Show Buys if any
buys = predictions[predictions['timing_band'] == 'TimingBuy']
if len(buys) > 0:
    print(f"\n💰 BUY SIGNALS ({len(buys)}):")
    print(buys.nlargest(10, 'predictor_score')[
        ['symbol', 'predictor_score', 'p_pos', 'E', 'RA', 'flags']
    ].to_string(index=False))
else:
    print(f"\n⚠️  No Buy signals")

# Show top scorers regardless of band
print(f"\n📈 TOP 10 STOCKS BY SCORE:")
top10 = predictions.nlargest(10, 'predictor_score')[
    ['symbol', 'predictor_score', 'timing_band', 'p_pos', 'E', 'RA', 'flags']
]
print(top10.to_string(index=False))

# Flags summary
print(f"\n🚩 Flags Summary:")
flag_counts = predictions['flags'].value_counts()
for flag, count in flag_counts.items():
    if flag:
        pct = count / len(predictions) * 100
        print(f"   {flag}: {count} ({pct:.1f}%)")

print("\n" + "="*70)
print("COMPARISON: OLD vs NEW THRESHOLDS")
print("="*70)

print("\n📊 OLD (Strict):")
print("   E_min: 0.015, RA_min: 0.45, p_pos_sb: 0.90, p_pos_buy: 0.75, k: 1.8")
print("   Result: 100% TimingHold, 0 Buy signals")

print("\n📊 NEW (Relaxed):")
print(f"   E_min: {config['predictor_score']['thresholds']['DEFAULT']['d20']['E_min']}, " +
      f"RA_min: {config['predictor_score']['thresholds']['DEFAULT']['d20']['RA_min']}, " +
      f"p_pos_sb: {config['predictor_score']['thresholds']['DEFAULT']['d20']['p_pos_min_sb']}, " +
      f"p_pos_buy: {config['predictor_score']['thresholds']['DEFAULT']['d20']['p_pos_min_buy']}, " +
      f"k: {config['barriers']['k_static']}")

sb_count = (predictions['timing_band'] == 'TimingSB').sum()
buy_count = (predictions['timing_band'] == 'TimingBuy').sum()
hold_count = (predictions['timing_band'] == 'TimingHold').sum()
avoid_count = (predictions['timing_band'] == 'TimingAvoid').sum()

print(f"   Result: {sb_count} SB, {buy_count} Buy, {hold_count} Hold, {avoid_count} Avoid")

if sb_count > 0 or buy_count > 0:
    print("\n✅ SUCCESS! Relaxed thresholds generated actionable signals")
    print("   → These parameters work better for the current model")
else:
    print("\n⚠️  Still no Buy signals - model may need more training or different features")

print("\n" + "="*70)
print("✅ TEST COMPLETE")
print("="*70)
