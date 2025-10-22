#!/usr/bin/env python3
"""
Large-Scale Backtest
Run predictor-owned backtest on 200+ stocks from validation_data_large
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import json
from datetime import datetime

sys.path.insert(0, '/app/backend')

from predictor.rule_based import RuleBasedPredictor
from backtest_predictor_owned import backtest_one, load_csv, calculate_metrics


def run_large_scale_backtest(
    data_dir: Path,
    predictor,
    max_stocks: int = None,
    verbose: bool = False
):
    """
    Run backtest on all stocks in data directory
    
    Args:
        data_dir: Directory with CSV files
        predictor: Predictor instance
        max_stocks: Limit number of stocks (None = all)
        verbose: Print individual trades
    
    Returns:
        (all_trades, all_metrics, summary)
    """
    csv_files = sorted(list(data_dir.glob('*_price_data.csv')))
    
    if max_stocks:
        csv_files = csv_files[:max_stocks]
    
    print(f"\n🔍 Found {len(csv_files)} stocks to backtest")
    print(f"📊 Running backtest on {len(csv_files)} tickers...\n")
    
    all_trades = []
    all_metrics = []
    failed = []
    
    for i, csv_file in enumerate(csv_files, 1):
        ticker = csv_file.stem.replace('_price_data', '')
        
        try:
            # Load data
            df = load_csv(str(csv_file))
            
            if len(df) < 50:
                print(f"⚠️  {ticker}: Insufficient data ({len(df)} bars), skipping")
                continue
            
            # Run backtest
            trades = backtest_one(df, ticker, predictor, verbose=verbose)
            
            # Calculate metrics
            metrics = calculate_metrics(trades, ticker)
            
            all_trades.extend(trades)
            all_metrics.append(metrics)
            
            # Progress
            if i % 10 == 0 or i == len(csv_files):
                print(f"✓ Progress: {i}/{len(csv_files)} - {ticker}: {len(trades)} trades")
        
        except Exception as e:
            failed.append((ticker, str(e)))
            if verbose:
                print(f"❌ {ticker}: {e}")
    
    # Calculate summary
    successful = len(all_metrics)
    total_trades = sum(m['total_trades'] for m in all_metrics)
    
    # Filter metrics with trades
    with_trades = [m for m in all_metrics if m['total_trades'] > 0]
    
    if with_trades:
        avg_win_rate = np.mean([m['win_rate'] for m in with_trades])
        avg_return = np.mean([m['avg_return_pct'] for m in with_trades])
        avg_sharpe = np.mean([m['sharpe'] for m in with_trades])
        
        # Aggregate returns
        all_returns = []
        for trade in all_trades:
            all_returns.append(trade.ret_pct)
        
        overall_win_rate = len([r for r in all_returns if r > 0]) / len(all_returns) * 100 if all_returns else 0
    else:
        avg_win_rate = avg_return = avg_sharpe = overall_win_rate = 0
    
    summary = {
        'total_stocks': len(csv_files),
        'successful': successful,
        'failed': len(failed),
        'total_trades': total_trades,
        'stocks_with_trades': len(with_trades),
        'avg_win_rate': avg_win_rate,
        'overall_win_rate': overall_win_rate,
        'avg_return_pct': avg_return,
        'avg_sharpe': avg_sharpe,
        'failed_tickers': failed
    }
    
    return all_trades, all_metrics, summary


def print_summary(summary, all_metrics, all_trades):
    """Print detailed summary"""
    print("\n" + "="*70)
    print("LARGE-SCALE BACKTEST SUMMARY")
    print("="*70)
    
    print(f"\n📊 Coverage:")
    print(f"   Total Stocks: {summary['total_stocks']}")
    print(f"   Successful: {summary['successful']}")
    print(f"   Failed: {summary['failed']}")
    print(f"   Stocks with Trades: {summary['stocks_with_trades']}")
    
    print(f"\n🔢 Trading Activity:")
    print(f"   Total Trades: {summary['total_trades']}")
    print(f"   Avg Trades per Stock: {summary['total_trades'] / summary['stocks_with_trades']:.1f}")
    
    print(f"\n📈 Performance:")
    print(f"   Overall Win Rate: {summary['overall_win_rate']:.1f}%")
    print(f"   Avg Win Rate per Stock: {summary['avg_win_rate']:.1f}%")
    print(f"   Avg Return per Trade: {summary['avg_return_pct']:+.2f}%")
    print(f"   Avg Sharpe Ratio: {summary['avg_sharpe']:.2f}")
    
    # Top performers
    if all_metrics:
        sorted_by_return = sorted(
            [m for m in all_metrics if m['total_trades'] > 0],
            key=lambda x: x['avg_return_pct'],
            reverse=True
        )
        
        print(f"\n🏆 Top 10 Performers (by avg return):")
        for i, m in enumerate(sorted_by_return[:10], 1):
            print(f"   {i:2}. {m['ticker']:12} - {m['avg_return_pct']:+6.2f}% "
                  f"(WR: {m['win_rate']:5.1f}%, Trades: {m['total_trades']:2})")
        
        print(f"\n📉 Bottom 10 Performers:")
        for i, m in enumerate(sorted_by_return[-10:], 1):
            print(f"   {i:2}. {m['ticker']:12} - {m['avg_return_pct']:+6.2f}% "
                  f"(WR: {m['win_rate']:5.1f}%, Trades: {m['total_trades']:2})")
    
    # Exit distribution
    if all_trades:
        exit_counts = {}
        for trade in all_trades:
            reason = trade.exit_reason.split()[0]  # Get first word
            exit_counts[reason] = exit_counts.get(reason, 0) + 1
        
        print(f"\n🚪 Exit Distribution:")
        for reason, count in sorted(exit_counts.items(), key=lambda x: x[1], reverse=True):
            pct = count / len(all_trades) * 100
            print(f"   {reason:10} - {count:4} ({pct:5.1f}%)")
    
    # Failed tickers
    if summary['failed'] > 0:
        print(f"\n⚠️  Failed Tickers ({summary['failed']}):")
        for ticker, error in summary['failed_tickers'][:5]:
            print(f"   {ticker}: {error[:60]}...")


def save_results(all_metrics, all_trades, summary, output_dir: Path):
    """Save results to files"""
    output_dir.mkdir(exist_ok=True)
    
    # Save summary
    summary_file = output_dir / 'backtest_summary.json'
    with open(summary_file, 'w') as f:
        # Convert failed_tickers to serializable format
        summary_copy = summary.copy()
        summary_copy['failed_tickers'] = [list(t) for t in summary['failed_tickers']]
        json.dump(summary_copy, f, indent=2)
    
    # Save metrics CSV
    if all_metrics:
        metrics_df = pd.DataFrame(all_metrics)
        metrics_file = output_dir / 'stock_metrics.csv'
        metrics_df.to_csv(metrics_file, index=False)
        print(f"\n💾 Saved metrics to: {metrics_file}")
    
    # Save trades CSV
    if all_trades:
        trades_data = []
        for t in all_trades:
            trades_data.append({
                'ticker': t.ticker,
                'entry_date': t.entry_date.date(),
                'entry_px': t.entry_px,
                'exit_date': t.exit_date.date(),
                'exit_px': t.exit_px,
                'return': t.ret,
                'return_pct': t.ret_pct,
                'bars': t.bars,
                'exit_reason': t.exit_reason,
                'regime': t.regime
            })
        
        trades_df = pd.DataFrame(trades_data)
        trades_file = output_dir / 'all_trades.csv'
        trades_df.to_csv(trades_file, index=False)
        print(f"💾 Saved trades to: {trades_file}")
    
    print(f"💾 Saved summary to: {summary_file}")


def main():
    """Run large-scale backtest"""
    print("="*70)
    print("LARGE-SCALE BACKTEST - 200+ Stocks")
    print("="*70)
    print("\nPredictor: Rule-Based with Gates")
    print("Data: /app/backend/validation_data_large/")
    print("Period: 2020-2022 (3 years)")
    
    # Configuration
    data_dir = Path('/app/backend/validation_data_large')
    output_dir = Path('/app/backend/backtest_results')
    
    if not data_dir.exists():
        print(f"\n❌ Data directory not found: {data_dir}")
        print("Please run large_scale_data_downloader.py first")
        return
    
    # Initialize predictor
    predictor = RuleBasedPredictor()
    
    # Run backtest
    start_time = datetime.now()
    
    all_trades, all_metrics, summary = run_large_scale_backtest(
        data_dir=data_dir,
        predictor=predictor,
        max_stocks=None,  # Use all stocks
        verbose=False
    )
    
    elapsed = datetime.now() - start_time
    print(f"\n⏱️  Backtest completed in {elapsed.total_seconds():.1f} seconds")
    
    # Print summary
    print_summary(summary, all_metrics, all_trades)
    
    # Save results
    save_results(all_metrics, all_trades, summary, output_dir)
    
    print(f"\n✅ Large-scale backtest complete!")


if __name__ == "__main__":
    main()
