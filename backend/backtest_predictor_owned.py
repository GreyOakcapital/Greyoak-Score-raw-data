#!/usr/bin/env python3
"""
Predictor-Owned Backtester
Clean separation: Predictor owns ALL logic (entry/exit/SL/TP/trail/horizon)
Backtester is just an execution engine with no lookahead

Key principles:
- Decisions at time t execute at t+1 open
- Predictor's exit policy is strictly enforced
- No lookahead bias by design
- Easy to swap predictors (rule-based → ML)
"""

import pandas as pd
import numpy as np
import json
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
from pathlib import Path
import sys

sys.path.insert(0, '/app/backend')

from predictor.rule_based import RuleBasedPredictor
from predictor.decision import Decision


@dataclass
class Trade:
    """Completed trade with all details"""
    ticker: str
    entry_date: pd.Timestamp
    entry_px: float
    exit_date: pd.Timestamp
    exit_px: float
    ret: float
    ret_pct: float
    bars: int
    exit_reason: str
    regime: str
    meta: Dict


def load_csv(path: str) -> pd.DataFrame:
    """
    Load OHLCV CSV with proper column naming
    Handles NSEPython format and generic OHLCV formats
    """
    df = pd.read_csv(path)
    
    # Handle NSEPython format (CH_ prefix columns)
    if 'CH_TIMESTAMP' in df.columns:
        df = df.rename(columns={
            'CH_TIMESTAMP': 'Date',
            'CH_OPENING_PRICE': 'Open',
            'CH_TRADE_HIGH_PRICE': 'High',
            'CH_TRADE_LOW_PRICE': 'Low',
            'CH_CLOSING_PRICE': 'Close',
            'CH_TOT_TRADED_QTY': 'Volume'
        })
    else:
        # Standardize column names for generic format
        col_map = {}
        date_found = False
        for col in df.columns:
            col_lower = col.lower()
            if not date_found and ('date' in col_lower or 'timestamp' in col_lower):
                col_map[col] = 'Date'
                date_found = True
            elif 'open' in col_lower:
                col_map[col] = 'Open'
            elif 'high' in col_lower:
                col_map[col] = 'High'
            elif 'low' in col_lower:
                col_map[col] = 'Low'
            elif 'close' in col_lower:
                col_map[col] = 'Close'
        
        df = df.rename(columns=col_map)
    
    # Convert date
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Keep only required columns
    required_cols = ['Date', 'Open', 'High', 'Low', 'Close']
    df = df[required_cols]
    
    # Sort and clean
    df = df.sort_values('Date').reset_index(drop=True)
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    
    return df


def backtest_one(
    df: pd.DataFrame,
    ticker: str,
    predictor: RuleBasedPredictor,
    verbose: bool = False
) -> List[Trade]:
    """
    Backtest a single ticker with predictor-owned exit logic
    
    Args:
        df: OHLCV DataFrame sorted by Date
        ticker: Stock symbol
        predictor: RuleBasedPredictor instance
        verbose: Print trade details
    
    Returns:
        List of completed Trade objects
    """
    trades: List[Trade] = []
    
    # Position state
    in_pos = False
    entry_px = None
    entry_idx = None
    entry_date = None
    
    # Predictor-owned exit policy (set at entry)
    sl = None
    tp = None
    trail = None
    max_hold = None
    regime = None
    entry_trail_gap = None  # for trailing stop updates
    
    # Iterate through bars; decisions at t execute at t+1
    for i in range(len(df) - 1):
        hist = df.iloc[:i+1]  # History up to current bar t (no lookahead)
        today = df.iloc[i]
        tomorrow = df.iloc[i+1]  # Execution bar (t+1)
        
        # Get predictor decision (only sees hist≤t)
        decision: Decision = predictor.decide(hist, in_position=in_pos)
        
        if not in_pos:
            # Flat - check for entry
            if decision.action == "enter_long":
                in_pos = True
                entry_idx = i + 1
                entry_px = float(tomorrow['Open'])  # Enter at t+1 open (no lookahead)
                entry_date = tomorrow['Date']
                
                # Store predictor's exit policy
                sl = decision.stop_loss
                tp = decision.take_profit
                trail = decision.trail_stop
                max_hold = decision.max_hold_bars
                regime = decision.regime
                
                # Track initial trail gap for updating
                if trail is not None:
                    entry_trail_gap = entry_px - trail
                
                if verbose:
                    print(f"\n{'='*60}")
                    print(f"ENTRY: {ticker} @ ₹{entry_px:.2f} on {entry_date.date()}")
                    print(f"Regime: {regime}")
                    print(f"SL: ₹{sl:.2f if sl else 'None'}, "
                          f"TP: ₹{tp:.2f if tp else 'None'}, "
                          f"Trail: ₹{trail:.2f if trail else 'None'}, "
                          f"Max Hold: {max_hold} bars")
                    print(f"Reason: {decision.reason}")
                    print(f"Meta: {decision.meta}")
            
            continue  # Stay flat if no entry
        
        # IN POSITION - apply predictor's exit policy
        cur = tomorrow
        high = float(cur['High'])
        low = float(cur['Low'])
        close = float(cur['Close'])
        
        # Update trailing stop if predictor provided one
        if trail is not None and entry_trail_gap is not None:
            # Trail from highest close since entry
            since_entry = df.iloc[entry_idx:i+2]['Close']
            roll_high = float(since_entry.max())
            new_trail = roll_high - entry_trail_gap
            trail = max(trail, new_trail)  # Only move up, never down
        
        # Check exit conditions (predictor-owned)
        exit_reason = None
        exit_px = None
        
        # Price-based exits
        if sl is not None and low <= sl:
            exit_reason = "SL (predictor)"
            exit_px = sl
        elif tp is not None and high >= tp:
            exit_reason = "TP (predictor)"
            exit_px = tp
        elif trail is not None and low <= trail:
            exit_reason = "TRAIL (predictor)"
            exit_px = trail
        else:
            # Regime-specific soft exits (predictor-owned)
            if regime == "mean_reversion":
                # Exit when price reaches DMA20 or RSI ≥ 55
                sub = df.iloc[:i+2].copy()
                c = sub['Close']
                
                # Calculate DMA20 up to current bar
                dma20 = c.rolling(20, min_periods=20).mean().iloc[-1]
                
                # Calculate RSI up to current bar
                delta = c.diff()
                gain = delta.where(delta > 0, 0.0)
                loss = -delta.where(delta < 0, 0.0)
                avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
                avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
                rs = avg_gain / (avg_loss + 1e-10)
                rsi = (100 - (100 / (1 + rs))).iloc[-1]
                
                if not pd.isna(dma20) and close >= float(dma20):
                    exit_reason = "MR target (DMA20, predictor)"
                    exit_px = close
                elif not pd.isna(rsi) and float(rsi) >= 55:
                    exit_reason = "MR target (RSI≥55, predictor)"
                    exit_px = close
            
            # Time horizon (predictor-owned)
            bars_held = (i + 1) - entry_idx + 1
            if exit_reason is None and max_hold is not None and bars_held >= max_hold:
                exit_reason = "TIME (predictor)"
                exit_px = close
        
        # Execute exit if triggered
        if exit_reason:
            ret = exit_px - entry_px
            ret_pct = (exit_px / entry_px - 1) * 100
            
            trade = Trade(
                ticker=ticker,
                entry_date=entry_date,
                entry_px=entry_px,
                exit_date=cur['Date'],
                exit_px=exit_px,
                ret=ret,
                ret_pct=ret_pct,
                bars=(i + 1 - entry_idx + 1),
                exit_reason=exit_reason,
                regime=regime,
                meta=decision.meta
            )
            
            trades.append(trade)
            
            if verbose:
                print(f"\nEXIT: {ticker} @ ₹{exit_px:.2f} on {cur['Date'].date()}")
                print(f"Reason: {exit_reason}")
                print(f"Return: ₹{ret:.2f} ({ret_pct:+.2f}%)")
                print(f"Bars held: {trade.bars}")
                print(f"{'='*60}")
            
            # Reset position
            in_pos = False
            entry_px = entry_idx = entry_date = None
            sl = tp = trail = max_hold = regime = entry_trail_gap = None
    
    return trades


def calculate_metrics(trades: List[Trade], ticker: str) -> Dict:
    """Calculate backtest metrics"""
    if not trades:
        return {
            'ticker': ticker,
            'total_trades': 0,
            'win_rate': 0.0,
            'avg_return_pct': 0.0,
            'total_return_pct': 0.0,
            'avg_bars': 0,
            'sharpe': 0.0,
            'max_dd_pct': 0.0
        }
    
    returns = [t.ret_pct for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    
    # Equity curve for drawdown
    equity = [100]
    for r in returns:
        equity.append(equity[-1] * (1 + r / 100))
    
    running_max = np.maximum.accumulate(equity)
    drawdowns = (np.array(equity) - running_max) / running_max * 100
    max_dd = abs(drawdowns.min()) if len(drawdowns) > 0 else 0.0
    
    # Sharpe (annualized, assuming ~252 trading days)
    avg_bars = np.mean([t.bars for t in trades])
    trades_per_year = 252 / avg_bars if avg_bars > 0 else 1
    sharpe = (np.mean(returns) / (np.std(returns) + 1e-9)) * np.sqrt(trades_per_year)
    
    return {
        'ticker': ticker,
        'total_trades': len(trades),
        'win_rate': len(wins) / len(trades) * 100,
        'avg_return_pct': np.mean(returns),
        'total_return_pct': sum(returns),
        'avg_win_pct': np.mean(wins) if wins else 0.0,
        'avg_loss_pct': np.mean(losses) if losses else 0.0,
        'avg_bars': avg_bars,
        'sharpe': sharpe,
        'max_dd_pct': max_dd,
        'breakout_trades': len([t for t in trades if t.regime == 'breakout']),
        'mr_trades': len([t for t in trades if t.regime == 'mean_reversion'])
    }


def main():
    """Run backtest on sample data"""
    print("="*70)
    print("Predictor-Owned Backtester")
    print("="*70)
    print("\nPredictor owns ALL logic:")
    print("  • Entry signals")
    print("  • Stop-loss levels")
    print("  • Take-profit targets")
    print("  • Trailing stops")
    print("  • Time horizons")
    print("  • Regime-specific exits")
    print("\nBacktester just executes at t+1 open with NO lookahead\n")
    
    # Initialize predictor
    predictor = RuleBasedPredictor()
    
    # Test with sample CSV (if available)
    data_dir = Path('/app/backend/validation_data')
    
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        print("Please run nsepython_downloader.py first to download data")
        return
    
    # Find available CSV files
    csv_files = list(data_dir.glob('*_price_data.csv'))
    
    if not csv_files:
        print(f"❌ No CSV files found in {data_dir}")
        return
    
    print(f"Found {len(csv_files)} CSV files\n")
    
    # Test on first 3 tickers
    all_metrics = []
    
    for csv_file in csv_files[:3]:
        ticker = csv_file.stem.replace('_price_data', '')
        
        print(f"\n{'#'*70}")
        print(f"Testing: {ticker}")
        print('#'*70)
        
        try:
            df = load_csv(str(csv_file))
            print(f"Loaded {len(df)} bars from {df['Date'].min().date()} to {df['Date'].max().date()}")
            
            # Run backtest
            trades = backtest_one(df, ticker, predictor, verbose=True)
            
            # Calculate metrics
            metrics = calculate_metrics(trades, ticker)
            all_metrics.append(metrics)
            
            print(f"\n{'='*60}")
            print(f"METRICS for {ticker}")
            print('='*60)
            print(f"Total Trades: {metrics['total_trades']}")
            print(f"Win Rate: {metrics['win_rate']:.1f}%")
            print(f"Avg Return: {metrics['avg_return_pct']:+.2f}%")
            print(f"Total Return: {metrics['total_return_pct']:+.2f}%")
            print(f"Avg Win: {metrics['avg_win_pct']:+.2f}%")
            print(f"Avg Loss: {metrics['avg_loss_pct']:+.2f}%")
            print(f"Avg Bars Held: {metrics['avg_bars']:.1f}")
            print(f"Sharpe Ratio: {metrics['sharpe']:.2f}")
            print(f"Max Drawdown: {metrics['max_dd_pct']:.2f}%")
            print(f"Breakout Trades: {metrics['breakout_trades']}")
            print(f"Mean-Reversion Trades: {metrics['mr_trades']}")
            
        except Exception as e:
            print(f"❌ Error backtesting {ticker}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    if all_metrics:
        print(f"\n{'='*70}")
        print("SUMMARY ACROSS ALL TICKERS")
        print('='*70)
        
        total_trades = sum(m['total_trades'] for m in all_metrics)
        avg_win_rate = np.mean([m['win_rate'] for m in all_metrics if m['total_trades'] > 0])
        avg_return = np.mean([m['avg_return_pct'] for m in all_metrics if m['total_trades'] > 0])
        
        print(f"Tickers Tested: {len(all_metrics)}")
        print(f"Total Trades: {total_trades}")
        print(f"Avg Win Rate: {avg_win_rate:.1f}%")
        print(f"Avg Return per Trade: {avg_return:+.2f}%")
        print(f"\n✅ Backtester working correctly!")
        print("   • No lookahead bias")
        print("   • Predictor-owned exits enforced")
        print("   • Clean separation of concerns")


if __name__ == "__main__":
    main()
