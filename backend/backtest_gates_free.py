#!/usr/bin/env python3
"""
Gates-Free Backtest
Only uses GreyOak Score threshold for entries (no technical gates)

Test: Does GreyOak Score alone provide edge?
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, '/app/backend')

from predictor.decision import Decision
from backtest_predictor_owned import backtest_one, load_csv, calculate_metrics


class GatesFreePredictor:
    """
    Simplified predictor with only GreyOak Score threshold
    No technical gates (RSI, breakouts, DMA20)
    """
    
    def __init__(self, score_threshold: float = 60.0):
        """
        Args:
            score_threshold: Minimum GreyOak Score for entry (default 60)
        """
        self.score_threshold = score_threshold
        self.rsi_len = 14
    
    def _rsi(self, s: pd.Series, n=14):
        """Calculate RSI indicator"""
        d = s.diff()
        up = np.where(d > 0, d, 0.0)
        dn = np.where(d < 0, -d, 0.0)
        ru = pd.Series(up).ewm(alpha=1/n, adjust=False).mean()
        rd = pd.Series(dn).ewm(alpha=1/n, adjust=False).mean().replace(0, np.nan)
        rs = ru / rd
        return (100 - (100 / (1 + rs))).fillna(50.0)
    
    def decide(self, hist: pd.DataFrame, in_position: bool = False) -> Decision:
        """
        Gates-free decision: Only GreyOak Score threshold
        
        Entry: score >= threshold
        No technical gates applied
        """
        if len(hist) < 20:
            return Decision(
                action="do_nothing",
                reason="Insufficient history",
                meta={}
            )
        
        df = hist.copy()
        if 'date' in df.columns:
            df = df.rename(columns={'date': 'Date'})
        if 'open' in df.columns:
            df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'})
        
        close = df['Close']
        high = df['High']
        low = df['Low']
        
        # Calculate minimal indicators for ATR and score estimation
        df['rsi_14'] = self._rsi(close, period=14)
        df['dma20'] = close.rolling(window=20).mean()
        
        # ATR for stop-loss
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr_14'] = tr.rolling(window=14).mean()
        
        row = df.iloc[-1]
        current_close = float(row['Close'])
        rsi = float(row['rsi_14']) if not pd.isna(row['rsi_14']) else 50.0
        dma20 = float(row['dma20']) if not pd.isna(row['dma20']) else current_close
        atr = float(row['atr_14']) if not pd.isna(row['atr_14']) else current_close * 0.01
        
        # Calculate simplified GreyOak Score proxy
        # (In production, this would call actual score engine)
        score = 50.0  # baseline
        
        # Price momentum component
        if dma20:
            price_diff_pct = (current_close - dma20) / dma20
            score += 30 * np.tanh(price_diff_pct / 0.03)
        
        # RSI component (mean-reversion friendly)
        rsi_factor = (50 - rsi) / 50  # negative when overbought, positive when oversold
        score += 20 * rsi_factor
        
        score = max(0, min(100, score))
        
        meta = {
            "score": round(score, 1),
            "rsi": round(rsi, 1),
            "dma20": round(dma20, 2),
            "close": round(current_close, 2),
            "atr": round(atr, 2)
        }
        
        # If in position, hold
        if in_position:
            return Decision(
                action="hold_long",
                reason="Holding (gates-free)",
                meta=meta
            )
        
        # ENTRY LOGIC: Only GreyOak Score threshold
        if score >= self.score_threshold:
            # Simple unified exit policy
            return Decision(
                action="enter_long",
                stop_loss=current_close - 2.0 * atr,
                take_profit=None,
                trail_stop=current_close - 3.0 * atr,
                max_hold_bars=20,
                reason=f"Score {score:.1f} >= {self.score_threshold} (gates-free)",
                regime="gates_free",
                meta=meta
            )
        
        # No entry
        return Decision(
            action="do_nothing",
            reason=f"Score {score:.1f} < {self.score_threshold}",
            meta=meta
        )


def main():
    """Run gates-free backtest"""
    print("="*70)
    print("GATES-FREE BACKTEST")
    print("="*70)
    print("\n🎯 Test: Does GreyOak Score alone provide edge?")
    print("\nEntry rule: score >= 60")
    print("No technical gates: No RSI, no breakout, no DMA20 checks")
    print("Exit policy: 2*ATR SL, 3*ATR trail, 20-bar max hold\n")
    
    # Initialize gates-free predictor
    predictor = GatesFreePredictor(score_threshold=60.0)
    
    # Test with data
    data_dir = Path('/app/backend/validation_data')
    
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return
    
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
            
            # Run gates-free backtest
            trades = backtest_one(df, ticker, predictor, verbose=True)
            
            # Calculate metrics
            metrics = calculate_metrics(trades, ticker)
            all_metrics.append(metrics)
            
            print(f"\n{'='*60}")
            print(f"METRICS for {ticker} (GATES-FREE)")
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
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    if all_metrics:
        print(f"\n{'='*70}")
        print("GATES-FREE SUMMARY")
        print('='*70)
        
        total_trades = sum(m['total_trades'] for m in all_metrics)
        avg_win_rate = np.mean([m['win_rate'] for m in all_metrics if m['total_trades'] > 0])
        avg_return = np.mean([m['avg_return_pct'] for m in all_metrics if m['total_trades'] > 0])
        
        print(f"Tickers: {len(all_metrics)}")
        print(f"Total Trades: {total_trades}")
        print(f"Avg Win Rate: {avg_win_rate:.1f}%")
        print(f"Avg Return per Trade: {avg_return:+.2f}%")
        
        print(f"\n📊 Comparison vs With-Gates:")
        print("   With Gates: 23 trades, 48.1% win rate, +0.44% avg return")
        print(f"   Gates-Free: {total_trades} trades, {avg_win_rate:.1f}% win rate, {avg_return:+.2f}% avg return")
        
        if total_trades > 23:
            print(f"\n   ✅ More trades generated ({total_trades} vs 23)")
        else:
            print(f"\n   ⚠️ Fewer trades ({total_trades} vs 23)")
        
        if avg_return > 0.44:
            print(f"   ✅ Better avg return ({avg_return:+.2f}% vs +0.44%)")
        else:
            print(f"   ❌ Worse avg return ({avg_return:+.2f}% vs +0.44%)")
        
        print("\n💡 Conclusion:")
        if total_trades > 23 and avg_return > 0:
            print("   GreyOak Score alone provides more opportunities with positive returns")
        elif avg_return < 0.44:
            print("   Technical gates improve trade quality (higher avg return)")
        else:
            print("   Mixed results - may need tuning")


if __name__ == "__main__":
    main()
