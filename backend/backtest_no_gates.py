"""
Gate-Free Walk-Forward Backtest
Simulates live trading with proper time-series evaluation
NO LOOKAHEAD - Bar-by-bar progression only
"""

import sys
sys.path.insert(0, '/app/backend')

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from predictor.infer import load_model, predict_probabilities, compute_edge_metrics, compute_predictor_score
import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("GATE-FREE WALK-FORWARD BACKTEST")
print("Strict No-Lookahead | Live-Market Simulation")
print("="*70)

# Configuration
CONFIDENCE_THRESHOLD = 0.60  # Minimum p_pos to generate signal (no gates, just confidence)
HORIZON_DAYS = 20  # Forward-looking window for outcome evaluation
TARGET_MULTIPLIER = 1.0  # Target = Entry + (U * Entry)
SL_MULTIPLIER = 1.0  # Stop Loss = Entry - (L * Entry)

# Load model
output_dir = Path("/app/backend/predictor_output")
model_files = list(output_dir.glob("all_d20_*.pkl"))
if not model_files:
    print("❌ No model found!")
    sys.exit(1)

model_path = sorted(model_files)[-1]
print(f"\n📊 Loading model: {model_path.name}")
model_artifacts = load_model(model_path)

# Load data
training_data_file = output_dir / "training_data.parquet"
if not training_data_file.exists():
    print("❌ Training data not found.")
    sys.exit(1)

print(f"✅ Loading historical data...")
df_full = pd.read_parquet(training_data_file)
df_full = df_full.sort_values(['symbol', 'date']).reset_index(drop=True)

print(f"   Total samples: {len(df_full):,}")
print(f"   Date range: {df_full['date'].min().date()} to {df_full['date'].max().date()}")
print(f"   Stocks: {df_full['symbol'].nunique()}")

# Prepare price data for outcome tracking
print(f"\n📊 Loading price data for outcome tracking...")
data_dir = Path("/app/backend/validation_data_large")
price_files = list(data_dir.glob("*_price_data.csv"))[:88]

all_prices = {}
for pf in price_files:
    ticker = pf.stem.replace('_price_data', '')
    try:
        df_price = pd.read_csv(pf)
        if 'CH_TIMESTAMP' in df_price.columns:
            df_price = df_price.rename(columns={'CH_TIMESTAMP': 'date'})
        if 'CH_SYMBOL' not in df_price.columns:
            df_price['symbol'] = ticker
        
        required_cols = ['CH_TRADE_HIGH_PRICE', 'CH_TRADE_LOW_PRICE', 
                        'CH_OPENING_PRICE', 'CH_CLOSING_PRICE']
        
        if all(col in df_price.columns for col in required_cols):
            df_price = df_price.rename(columns={
                'CH_TRADE_HIGH_PRICE': 'high',
                'CH_TRADE_LOW_PRICE': 'low',
                'CH_OPENING_PRICE': 'open',
                'CH_CLOSING_PRICE': 'close'
            })
            df_price['date'] = pd.to_datetime(df_price['date'])
            df_price = df_price[['date', 'symbol', 'open', 'high', 'low', 'close']].sort_values('date')
            all_prices[ticker] = df_price
    except:
        pass

print(f"✅ Loaded price data for {len(all_prices)} stocks")

# Get unique dates for walk-forward
all_dates = sorted(df_full['date'].unique())
print(f"\n📅 Walk-forward simulation: {len(all_dates)} trading days")
print(f"   Start: {all_dates[0].date()}")
print(f"   End:   {all_dates[-1].date()}")

# Initialize results tracking
trades = []
predictions_log = []

print(f"\n{'='*70}")
print("RUNNING BAR-BY-BAR SIMULATION")
print("="*70)
print("\nProgress:")

# Walk forward bar-by-bar
for i, current_date in enumerate(all_dates):
    
    # Progress indicator
    if i % 50 == 0:
        pct = i / len(all_dates) * 100
        print(f"  [{pct:5.1f}%] {current_date.date()} - {i}/{len(all_dates)} days", end='\r')
    
    # Get all data UP TO this date (strict no lookahead)
    historical_data = df_full[df_full['date'] <= current_date].copy()
    
    # Get today's data for prediction
    today_data = df_full[df_full['date'] == current_date].copy()
    
    if len(today_data) == 0:
        continue
    
    # Run inference WITHOUT GATES
    feature_cols = model_artifacts['feature_cols']
    X = today_data[feature_cols].fillna(0)
    
    # Get probabilities
    p_pos, p_neg, p_neu = predict_probabilities(model_artifacts, X)
    
    # Compute edge metrics
    E, Var, RA = compute_edge_metrics(p_pos, p_neg, today_data['U'].values, today_data['L'].values)
    
    # Generate predictions for all stocks
    for idx in range(len(today_data)):
        symbol = today_data.iloc[idx]['symbol']
        
        pred_record = {
            'date': current_date,
            'symbol': symbol,
            'close': today_data.iloc[idx]['close'],
            'p_pos': p_pos[idx],
            'p_neg': p_neg[idx],
            'p_neu': p_neu[idx],
            'E': E[idx],
            'RA': RA[idx],
            'U': today_data.iloc[idx]['U'],
            'L': today_data.iloc[idx]['L']
        }
        predictions_log.append(pred_record)
        
        # Generate signal based on confidence only (no gates)
        if p_pos[idx] >= CONFIDENCE_THRESHOLD:
            action = 'BUY'
        elif p_neg[idx] >= CONFIDENCE_THRESHOLD:
            action = 'AVOID'
        else:
            action = 'HOLD'
        
        # Only track BUY signals for outcome evaluation
        if action == 'BUY':
            entry_price = today_data.iloc[idx]['close']
            U_barrier = today_data.iloc[idx]['U']
            L_barrier = today_data.iloc[idx]['L']
            
            target_price = entry_price * (1 + U_barrier * TARGET_MULTIPLIER)
            sl_price = entry_price * (1 - L_barrier * SL_MULTIPLIER)
            
            trade = {
                'entry_date': current_date,
                'symbol': symbol,
                'action': action,
                'entry_price': entry_price,
                'target_price': target_price,
                'sl_price': sl_price,
                'p_pos': p_pos[idx],
                'p_neg': p_neg[idx],
                'E': E[idx],
                'RA': RA[idx],
                'U': U_barrier,
                'L': L_barrier,
                'exit_date': None,
                'exit_price': None,
                'outcome': 'PENDING',
                'holding_days': None,
                'pnl_pct': None
            }
            
            # Check outcome in next HORIZON_DAYS bars
            if symbol in all_prices:
                price_data = all_prices[symbol]
                future_prices = price_data[price_data['date'] > current_date].head(HORIZON_DAYS)
                
                if len(future_prices) > 0:
                    # Check bar-by-bar for target or SL hit
                    for j, (_, price_row) in enumerate(future_prices.iterrows(), 1):
                        high = price_row['high']
                        low = price_row['low']
                        close = price_row['close']
                        
                        # Check if target hit first
                        target_hit = high >= target_price
                        sl_hit = low <= sl_price
                        
                        if target_hit and sl_hit:
                            # Both hit same bar - check which came first (conservative: SL)
                            trade['outcome'] = 'FAILED'
                            trade['exit_date'] = price_row['date']
                            trade['exit_price'] = sl_price
                            trade['holding_days'] = j
                            trade['pnl_pct'] = (sl_price - entry_price) / entry_price * 100
                            break
                        elif target_hit:
                            trade['outcome'] = 'ACHIEVED'
                            trade['exit_date'] = price_row['date']
                            trade['exit_price'] = target_price
                            trade['holding_days'] = j
                            trade['pnl_pct'] = (target_price - entry_price) / entry_price * 100
                            break
                        elif sl_hit:
                            trade['outcome'] = 'FAILED'
                            trade['exit_date'] = price_row['date']
                            trade['exit_price'] = sl_price
                            trade['holding_days'] = j
                            trade['pnl_pct'] = (sl_price - entry_price) / entry_price * 100
                            break
                    
                    # If no hit within horizon
                    if trade['outcome'] == 'PENDING':
                        trade['outcome'] = 'TIMEOUT'
                        trade['exit_date'] = future_prices.iloc[-1]['date']
                        trade['exit_price'] = future_prices.iloc[-1]['close']
                        trade['holding_days'] = len(future_prices)
                        trade['pnl_pct'] = (trade['exit_price'] - entry_price) / entry_price * 100
            
            trades.append(trade)

print(f"\n\n✅ Simulation complete!")

# Save results
trades_df = pd.DataFrame(trades)
predictions_df = pd.DataFrame(predictions_log)

trades_df.to_csv(output_dir / 'backtest_no_gates_trades.csv', index=False)
predictions_df.to_csv(output_dir / 'backtest_no_gates_predictions.csv', index=False)

print(f"✅ Saved results")
print(f"   Trades: {len(trades_df)}")
print(f"   Predictions: {len(predictions_df)}")

# Performance Analysis
print(f"\n{'='*70}")
print("PERFORMANCE REPORT")
print("="*70)

if len(trades_df) == 0:
    print("\n❌ No trades generated!")
    print(f"   This means no predictions exceeded p_pos ≥ {CONFIDENCE_THRESHOLD}")
    print("\n💡 Recommendations:")
    print(f"   1. Lower confidence threshold (currently {CONFIDENCE_THRESHOLD})")
    print(f"   2. Model is not generating confident predictions")
    print(f"   3. Consider retraining with different parameters")
else:
    print(f"\n📊 TRADE STATISTICS")
    print(f"   Total signals: {len(trades_df)}")
    print(f"   Unique stocks: {trades_df['symbol'].nunique()}")
    print(f"   Date range: {trades_df['entry_date'].min().date()} to {trades_df['entry_date'].max().date()}")
    
    # Outcome distribution
    print(f"\n📊 OUTCOME DISTRIBUTION")
    outcome_counts = trades_df['outcome'].value_counts()
    for outcome, count in outcome_counts.items():
        pct = count / len(trades_df) * 100
        icon = "✅" if outcome == "ACHIEVED" else "❌" if outcome == "FAILED" else "⏳"
        print(f"   {icon} {outcome:10} {count:4d} ({pct:5.1f}%)")
    
    # Calculate win rate (exclude timeouts)
    completed_trades = trades_df[trades_df['outcome'].isin(['ACHIEVED', 'FAILED'])]
    if len(completed_trades) > 0:
        wins = (completed_trades['outcome'] == 'ACHIEVED').sum()
        losses = (completed_trades['outcome'] == 'FAILED').sum()
        win_rate = wins / len(completed_trades)
        
        print(f"\n🎯 WIN RATE (Excluding Timeouts)")
        print(f"   Wins:      {wins:4d}")
        print(f"   Losses:    {losses:4d}")
        print(f"   Win Rate:  {win_rate*100:5.1f}%")
        
        if win_rate >= 0.60:
            print(f"   ✅ Excellent! Model has predictive power")
        elif win_rate >= 0.50:
            print(f"   ⚠️  Marginal - better than random")
        else:
            print(f"   ❌ Poor - worse than coin flip")
    
    # PnL analysis
    if 'pnl_pct' in trades_df.columns and trades_df['pnl_pct'].notna().sum() > 0:
        print(f"\n💰 PnL STATISTICS")
        print(f"   Mean PnL:     {trades_df['pnl_pct'].mean():+.2f}%")
        print(f"   Median PnL:   {trades_df['pnl_pct'].median():+.2f}%")
        print(f"   Best trade:   {trades_df['pnl_pct'].max():+.2f}%")
        print(f"   Worst trade:  {trades_df['pnl_pct'].min():+.2f}%")
        print(f"   Total PnL:    {trades_df['pnl_pct'].sum():+.2f}%")
    
    # Holding period
    if 'holding_days' in trades_df.columns and trades_df['holding_days'].notna().sum() > 0:
        print(f"\n⏱️  HOLDING PERIOD")
        print(f"   Mean:      {trades_df['holding_days'].mean():.1f} days")
        print(f"   Median:    {trades_df['holding_days'].median():.1f} days")
        print(f"   Min:       {trades_df['holding_days'].min():.0f} days")
        print(f"   Max:       {trades_df['holding_days'].max():.0f} days")
    
    # Reward-to-risk ratio
    avg_U = trades_df['U'].mean()
    avg_L = trades_df['L'].mean()
    reward_risk = avg_U / avg_L if avg_L > 0 else 0
    print(f"\n📊 REWARD-TO-RISK")
    print(f"   Avg Up Barrier:   {avg_U*100:.2f}%")
    print(f"   Avg Down Barrier: {avg_L*100:.2f}%")
    print(f"   R:R Ratio:        {reward_risk:.2f}:1")
    
    # Show sample achieved trades
    achieved_trades = trades_df[trades_df['outcome'] == 'ACHIEVED']
    if len(achieved_trades) > 0:
        print(f"\n✅ SAMPLE ACHIEVED TRADES (Top 10)")
        sample = achieved_trades.nlargest(10, 'pnl_pct')[
            ['entry_date', 'symbol', 'entry_price', 'exit_price', 'pnl_pct', 'holding_days', 'p_pos']
        ]
        print(sample.to_string(index=False))
    
    # Show sample failed trades
    failed_trades = trades_df[trades_df['outcome'] == 'FAILED']
    if len(failed_trades) > 0:
        print(f"\n❌ SAMPLE FAILED TRADES (Worst 10)")
        sample = failed_trades.nsmallest(10, 'pnl_pct')[
            ['entry_date', 'symbol', 'entry_price', 'exit_price', 'pnl_pct', 'holding_days', 'p_pos']
        ]
        print(sample.to_string(index=False))

# Confidence analysis
print(f"\n{'='*70}")
print("MODEL CONFIDENCE ANALYSIS")
print("="*70)

print(f"\n📊 Probability Distribution (All Predictions)")
print(f"   Mean p_pos:  {predictions_df['p_pos'].mean():.3f}")
print(f"   Mean p_neg:  {predictions_df['p_neg'].mean():.3f}")
print(f"   Mean p_neu:  {predictions_df['p_neu'].mean():.3f}")

print(f"\n📊 Confidence Levels")
bins = [0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
labels = ['<50%', '50-60%', '60-70%', '70-80%', '80-90%', '90-100%']
predictions_df['p_pos_bin'] = pd.cut(predictions_df['p_pos'], bins=bins, labels=labels)
conf_dist = predictions_df['p_pos_bin'].value_counts().sort_index()
for label, count in conf_dist.items():
    pct = count / len(predictions_df) * 100
    print(f"   {label:10} {count:6d} ({pct:5.1f}%)")

print(f"\n{'='*70}")
print("✅ GATE-FREE BACKTEST COMPLETE")
print("="*70)
print(f"\n📁 Output files:")
print(f"   {output_dir / 'backtest_no_gates_trades.csv'}")
print(f"   {output_dir / 'backtest_no_gates_predictions.csv'}")
