"""
Historical Backtest: Test Predictor on 2020-2022 Data
Check if model generates signals and validate accuracy
"""

import sys
sys.path.insert(0, '/app/backend')

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from predictor.infer import load_model, run_inference, load_config

print("="*70)
print("HISTORICAL BACKTEST: 2020-2022")
print("="*70)

# Load config
config = load_config()
print("\n📋 Configuration:")
print(f"   E_min: {config['predictor_score']['thresholds']['DEFAULT']['d20']['E_min']}")
print(f"   RA_min: {config['predictor_score']['thresholds']['DEFAULT']['d20']['RA_min']}")
print(f"   p_pos_min_sb: {config['predictor_score']['thresholds']['DEFAULT']['d20']['p_pos_min_sb']}")
print(f"   p_pos_min_buy: {config['predictor_score']['thresholds']['DEFAULT']['d20']['p_pos_min_buy']}")

# Load model
output_dir = Path("/app/backend/predictor_output")
model_files = list(output_dir.glob("all_d20_*.pkl"))
if not model_files:
    print("❌ No model found!")
    sys.exit(1)

model_path = sorted(model_files)[-1]
print(f"\n📊 Loading model: {model_path.name}")
model_artifacts = load_model(model_path)

# Load full training data
training_data_file = output_dir / "training_data.parquet"
if not training_data_file.exists():
    print("❌ Training data not found. Run test_relaxed_thresholds.py first.")
    sys.exit(1)

print(f"✅ Loading full historical data...")
df = pd.read_parquet(training_data_file)
print(f"   Total samples: {len(df):,}")
print(f"   Date range: {df['date'].min().date()} to {df['date'].max().date()}")
print(f"   Stocks: {df['symbol'].nunique()}")

# Split data into periods for backtesting
# We'll test on multiple time periods to see signal generation
test_periods = [
    ('Bull 2020-21 Start', '2020-11-01', '2020-11-30'),
    ('Bull 2020-21 Mid', '2021-03-01', '2021-03-31'),
    ('Bull 2020-21 Peak', '2021-09-01', '2021-09-30'),
    ('Bear 2022 Start', '2022-01-01', '2022-01-31'),
    ('Bear 2022 Mid', '2022-05-01', '2022-05-31'),
    ('Bear 2022 End', '2022-10-01', '2022-10-31')
]

print("\n" + "="*70)
print("RUNNING BACKTEST ACROSS MULTIPLE PERIODS")
print("="*70)

all_period_results = []
all_predictions = []

for period_name, start_date, end_date in test_periods:
    print(f"\n{'─'*70}")
    print(f"Period: {period_name}")
    print(f"Dates: {start_date} to {end_date}")
    print("─"*70)
    
    # Get data for this period
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    period_df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)].copy()
    
    if len(period_df) == 0:
        print("⚠️  No data in this period")
        continue
    
    print(f"Samples: {len(period_df)}")
    
    # Run inference
    predictions = run_inference(period_df, model_artifacts, config)
    
    # Add period label
    predictions['period'] = period_name
    all_predictions.append(predictions)
    
    # Analyze results
    band_counts = predictions['timing_band'].value_counts()
    
    sb_count = band_counts.get('TimingSB', 0)
    buy_count = band_counts.get('TimingBuy', 0)
    hold_count = band_counts.get('TimingHold', 0)
    avoid_count = band_counts.get('TimingAvoid', 0)
    
    print(f"\n📊 Signals:")
    print(f"   TimingSB:    {sb_count:3d} ({sb_count/len(predictions)*100:5.1f}%)")
    print(f"   TimingBuy:   {buy_count:3d} ({buy_count/len(predictions)*100:5.1f}%)")
    print(f"   TimingHold:  {hold_count:3d} ({hold_count/len(predictions)*100:5.1f}%)")
    print(f"   TimingAvoid: {avoid_count:3d} ({avoid_count/len(predictions)*100:5.1f}%)")
    
    # Score stats
    print(f"\n📊 Scores:")
    print(f"   Mean:   {predictions['predictor_score'].mean():.1f}")
    print(f"   Median: {predictions['predictor_score'].median():.1f}")
    print(f"   Max:    {predictions['predictor_score'].max()}")
    print(f"   ≥60:    {(predictions['predictor_score'] >= 60).sum()}")
    
    # Gate pass rate
    gate_fail = predictions['flags'].str.contains('GateFail', na=False).sum()
    gate_pass = len(predictions) - gate_fail
    print(f"\n🚪 Gates:")
    print(f"   Pass: {gate_pass:3d} ({gate_pass/len(predictions)*100:5.1f}%)")
    print(f"   Fail: {gate_fail:3d} ({gate_fail/len(predictions)*100:5.1f}%)")
    
    # Show top signals if any
    if sb_count > 0:
        print(f"\n🎯 Top Strong Buys:")
        top_sb = predictions[predictions['timing_band'] == 'TimingSB'].nlargest(5, 'predictor_score')
        print(top_sb[['symbol', 'date', 'predictor_score', 'p_pos', 'E', 'RA']].to_string(index=False))
    
    if buy_count > 0:
        print(f"\n💰 Top Buys:")
        top_buy = predictions[predictions['timing_band'] == 'TimingBuy'].nlargest(5, 'predictor_score')
        print(top_buy[['symbol', 'date', 'predictor_score', 'p_pos', 'E', 'RA']].to_string(index=False))
    
    # Store summary
    all_period_results.append({
        'period': period_name,
        'start_date': start_date,
        'end_date': end_date,
        'total_predictions': len(predictions),
        'sb_count': sb_count,
        'buy_count': buy_count,
        'hold_count': hold_count,
        'avoid_count': avoid_count,
        'gate_pass_count': gate_pass,
        'avg_score': predictions['predictor_score'].mean(),
        'max_score': predictions['predictor_score'].max()
    })

# Combine all predictions
if all_predictions:
    combined_predictions = pd.concat(all_predictions, ignore_index=True)
    combined_predictions.to_parquet(output_dir / 'backtest_predictions.parquet', index=False)
    combined_predictions.to_csv(output_dir / 'backtest_predictions.csv', index=False)
    print(f"\n✅ Saved all backtest predictions")

# Overall summary
print("\n" + "="*70)
print("BACKTEST SUMMARY ACROSS ALL PERIODS")
print("="*70)

summary_df = pd.DataFrame(all_period_results)

if len(summary_df) > 0:
    print("\n📊 Signal Generation by Period:")
    print("┌─────────────────────┬───────┬─────┬──────┬──────┬───────┬──────────┐")
    print("│ Period              │ Total │ SB  │ Buy  │ Hold │ Avoid │ MaxScore │")
    print("├─────────────────────┼───────┼─────┼──────┼──────┼───────┼──────────┤")
    
    for _, row in summary_df.iterrows():
        name = row['period'][:19]
        print(f"│ {name:19} │ {row['total_predictions']:>5} │ {row['sb_count']:>3} │ {row['buy_count']:>4} │ {row['hold_count']:>4} │ {row['avoid_count']:>5} │ {row['max_score']:>8.0f} │")
    
    print("└─────────────────────┴───────┴─────┴──────┴──────┴───────┴──────────┘")
    
    # Totals
    total_sb = summary_df['sb_count'].sum()
    total_buy = summary_df['buy_count'].sum()
    total_predictions = summary_df['total_predictions'].sum()
    total_gate_pass = summary_df['gate_pass_count'].sum()
    
    print(f"\n📊 Overall Statistics:")
    print(f"   Total predictions: {total_predictions:,}")
    print(f"   Strong Buy signals: {total_sb} ({total_sb/total_predictions*100:.2f}%)")
    print(f"   Buy signals: {total_buy} ({total_buy/total_predictions*100:.2f}%)")
    print(f"   Gate pass rate: {total_gate_pass/total_predictions*100:.1f}%")
    print(f"   Average max score: {summary_df['max_score'].mean():.1f}")

# Validate predictions (check actual outcomes)
if len(combined_predictions) > 0 and (combined_predictions['timing_band'].isin(['TimingSB', 'TimingBuy']).any()):
    print("\n" + "="*70)
    print("VALIDATION: CHECK ACTUAL OUTCOMES")
    print("="*70)
    
    # Get Buy/SB signals
    signals = combined_predictions[combined_predictions['timing_band'].isin(['TimingSB', 'TimingBuy'])].copy()
    
    if len(signals) > 0:
        print(f"\n✅ Found {len(signals)} Buy/SB signals to validate")
        
        # For each signal, check if stock went up in next 20 days
        # We already have the labels (ground truth)
        signals_with_labels = signals.merge(
            df[['date', 'symbol', 'label']],
            on=['date', 'symbol'],
            how='left'
        )
        
        print(f"\n📊 Signal Accuracy:")
        print(f"   Signals with labels: {signals_with_labels['label'].notna().sum()}")
        
        if signals_with_labels['label'].notna().sum() > 0:
            # Check how many were correct
            correct_up = (signals_with_labels['label'] == 1).sum()
            went_down = (signals_with_labels['label'] == -1).sum()
            neutral = (signals_with_labels['label'] == 0).sum()
            
            print(f"\n   Actual outcomes:")
            print(f"   ✅ Went UP (+1):   {correct_up} ({correct_up/len(signals_with_labels)*100:.1f}%)")
            print(f"   ❌ Went DOWN (-1): {went_down} ({went_down/len(signals_with_labels)*100:.1f}%)")
            print(f"   ⚪ Neutral (0):    {neutral} ({neutral/len(signals_with_labels)*100:.1f}%)")
            
            precision = correct_up / len(signals_with_labels) if len(signals_with_labels) > 0 else 0
            print(f"\n   🎯 Precision: {precision*100:.1f}%")
            
            if precision >= 0.60:
                print("   ✅ Good precision! Model is generating useful signals")
            elif precision >= 0.50:
                print("   ⚠️  Marginal precision - better than random but needs improvement")
            else:
                print("   ❌ Poor precision - model needs significant tuning")

# Final diagnosis
print("\n" + "="*70)
print("DIAGNOSIS & RECOMMENDATIONS")
print("="*70)

if total_sb + total_buy > 0:
    print("\n✅ MODEL IS GENERATING SIGNALS!")
    print(f"   Found {total_sb + total_buy} actionable signals across {len(test_periods)} periods")
    print("\n💡 Next Steps:")
    print("   1. Validate signal accuracy is acceptable (check precision above)")
    print("   2. If precision ≥60%, these thresholds are good")
    print("   3. Deploy with these relaxed settings")
else:
    print("\n⚠️  MODEL STILL NOT GENERATING SIGNALS")
    print("\n💡 Possible causes:")
    print("   1. Model predictions are genuinely low confidence")
    print("   2. Training data insufficient for pattern detection")
    print("   3. Features not capturing predictive signals")
    print("\n💡 Recommended fixes:")
    print("   1. Increase training data (more stocks, longer history)")
    print("   2. Add more features (volume patterns, sector momentum, etc.)")
    print("   3. Try simpler barriers (wider k, or fixed % returns)")
    print("   4. Review feature importance to see what's working")

print("\n" + "="*70)
print("✅ BACKTEST COMPLETE")
print("="*70)
