#!/usr/bin/env python3
"""
Quick NSE Demo - GreyOak Score Engine
Simplified demonstration with 50 NSE stocks
"""

import numpy as np
import pandas as pd
from datetime import date
import random

# Sample NSE stocks
NSE_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HDFC.NS", "KOTAKBANK.NS", "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS",
    "ITC.NS", "ASIANPAINT.NS", "LT.NS", "AXISBANK.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "ULTRACEMCO.NS", "TITAN.NS", "WIPRO.NS", "NESTLEIND.NS",
    "BAJFINANCE.NS", "HCLTECH.NS", "POWERGRID.NS", "NTPC.NS", "TECHM.NS",
    "M&M.NS", "TATAMOTORS.NS", "INDUSINDBK.NS", "BAJAJFINSV.NS", "ONGC.NS",
    "COALINDIA.NS", "GRASIM.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "HINDALCO.NS",
    "ADANIPORTS.NS", "CIPLA.NS", "DIVISLAB.NS", "DRREDDY.NS", "EICHERMOT.NS",
    "HEROMOTOCO.NS", "BRITANNIA.NS", "APOLLOHOSP.NS", "UPL.NS", "BPCL.NS",
    "IOC.NS", "SHREECEM.NS", "GODREJCP.NS", "PIDILITIND.NS", "DABUR.NS"
]

def calculate_stock_score(ticker, pe_ratio, roe, returns_1m, debt_equity, mode='Investor'):
    """Calculate a simplified GreyOak-style score."""
    
    # Fundamentals score (30% weight for Investor, 15% for Trader)
    f_score = 50
    if pe_ratio < 20: f_score += 15
    if roe > 15: f_score += 20
    if debt_equity < 0.5: f_score += 15
    f_score = min(100, max(0, f_score))
    
    # Technical score (15% weight for Investor, 30% for Trader)  
    t_score = 50
    if returns_1m > 5: t_score += 25
    if returns_1m > 0: t_score += 15
    t_score = min(100, max(0, t_score))
    
    # Other pillars (simplified)
    r_score = 50 + returns_1m * 2 + np.random.uniform(-10, 10)
    o_score = np.random.uniform(40, 80)
    q_score = 40 + (roe - 10) * 2 + np.random.uniform(-10, 10)
    s_score = np.random.uniform(35, 75)
    
    # Ensure scores are within bounds
    for score in [r_score, o_score, q_score, s_score]:
        score = min(100, max(0, score))
    
    # Calculate weighted score based on mode
    if mode == 'Investor':
        weights = {'F': 0.35, 'T': 0.15, 'R': 0.15, 'O': 0.15, 'Q': 0.15, 'S': 0.05}
    else:  # Trader
        weights = {'F': 0.15, 'T': 0.30, 'R': 0.25, 'O': 0.10, 'Q': 0.10, 'S': 0.10}
    
    weighted_score = (f_score * weights['F'] + t_score * weights['T'] + 
                     r_score * weights['R'] + o_score * weights['O'] +
                     q_score * weights['Q'] + s_score * weights['S'])
    
    # Apply risk penalty
    risk_penalty = 0
    if debt_equity > 1.0: risk_penalty += 3
    if pe_ratio > 40: risk_penalty += 2
    
    final_score = max(0, weighted_score - risk_penalty)
    
    # Determine band
    if final_score >= 75:
        band = "Strong Buy"
    elif final_score >= 65:
        band = "Buy"
    elif final_score >= 50:
        band = "Hold"
    else:
        band = "Avoid"
    
    return {
        'ticker': ticker,
        'f_score': f_score,
        't_score': t_score,
        'r_score': r_score,
        'o_score': o_score,
        'q_score': q_score,
        's_score': s_score,
        'weighted_score': weighted_score,
        'risk_penalty': risk_penalty,
        'final_score': final_score,
        'band': band,
        'pe_ratio': pe_ratio,
        'roe': roe,
        'returns_1m': returns_1m,
        'debt_equity': debt_equity
    }

def main():
    print("🎯 GreyOak Score Engine - Quick NSE Demo")
    print("=" * 50)
    print(f"Testing with {len(NSE_STOCKS)} NSE stocks using realistic simulated data")
    print("All processing in-memory (no data saved)")
    print()
    
    # Generate random but realistic data
    np.random.seed(42)
    
    results = {'Investor': [], 'Trader': []}
    
    for mode in ['Investor', 'Trader']:
        print(f"🔄 Calculating scores for {mode} mode...")
        
        mode_results = []
        for ticker in NSE_STOCKS:
            # Generate realistic stock data
            pe_ratio = np.random.uniform(8, 45)
            roe = np.random.uniform(5, 30)
            returns_1m = np.random.uniform(-15, 25)
            debt_equity = np.random.uniform(0.1, 1.5)
            
            # Calculate score
            score_result = calculate_stock_score(ticker, pe_ratio, roe, returns_1m, debt_equity, mode)
            mode_results.append(score_result)
        
        results[mode] = mode_results
        print(f"✅ {len(mode_results)} stocks scored for {mode} mode")
    
    # Analyze results
    print("\n📊 RESULTS ANALYSIS")
    print("=" * 50)
    
    for mode in ['Investor', 'Trader']:
        df = pd.DataFrame(results[mode])
        
        print(f"\n🎯 {mode.upper()} MODE RESULTS:")
        print(f"Average Score: {df['final_score'].mean():.1f}")
        print(f"Score Range: {df['final_score'].min():.1f} - {df['final_score'].max():.1f}")
        
        # Band distribution
        band_counts = df['band'].value_counts()
        print("Investment Bands:")
        for band in ['Strong Buy', 'Buy', 'Hold', 'Avoid']:
            count = band_counts.get(band, 0)
            print(f"  • {band}: {count} stocks ({count/len(df)*100:.1f}%)")
        
        # Top 5 performers
        print(f"\nTop 5 {mode} Picks:")
        top_5 = df.nlargest(5, 'final_score')
        for _, row in top_5.iterrows():
            print(f"  {row['ticker']:12} | Score: {row['final_score']:5.1f} | {row['band']:10} | PE: {row['pe_ratio']:4.1f} | ROE: {row['roe']:4.1f}%")
    
    # Summary
    investor_df = pd.DataFrame(results['Investor'])
    trader_df = pd.DataFrame(results['Trader'])
    
    print(f"\n🎉 DEMO SUMMARY")
    print("=" * 50)
    print(f"✅ {len(NSE_STOCKS)} NSE stocks processed")
    print(f"✅ Both Investor and Trader modes calculated")
    print(f"✅ Investor Strong Buys: {sum(investor_df['band'] == 'Strong Buy')}")
    print(f"✅ Trader Strong Buys: {sum(trader_df['band'] == 'Strong Buy')}")
    print(f"✅ Average Investor Score: {investor_df['final_score'].mean():.1f}")
    print(f"✅ Average Trader Score: {trader_df['final_score'].mean():.1f}")
    print()
    print("🚀 This demonstrates the GreyOak scoring methodology!")
    print("   • Six-pillar analysis (F, T, R, O, Q, S)")
    print("   • Mode-specific weighting (Investor vs Trader)")
    print("   • Risk penalty application")
    print("   • Investment band classification")
    print("   • Real NSE ticker symbols used")
    print("   • No data persistence (all in-memory)")

if __name__ == "__main__":
    main()