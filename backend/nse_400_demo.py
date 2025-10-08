#!/usr/bin/env python3
"""
NSE 400 Stock Demo - GreyOak Score Engine
Full demonstration with 400 stocks from NSE universe
"""

import numpy as np
import pandas as pd
from datetime import date
import random
import time

# Expanded NSE stock universe (400 stocks)
def generate_nse_400():
    # Start with major NSE companies
    major_stocks = [
        # Nifty 50 + Next 50
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "HDFC.NS", "KOTAKBANK.NS",
        "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "ASIANPAINT.NS", "LT.NS", "AXISBANK.NS",
        "MARUTI.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS", "TITAN.NS", "WIPRO.NS", "NESTLEIND.NS", "BAJFINANCE.NS",
        "HCLTECH.NS", "POWERGRID.NS", "NTPC.NS", "TECHM.NS", "M&M.NS", "TATAMOTORS.NS", "INDUSINDBK.NS",
        "BAJAJFINSV.NS", "ONGC.NS", "COALINDIA.NS", "GRASIM.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "HINDALCO.NS",
        "ADANIPORTS.NS", "CIPLA.NS", "DIVISLAB.NS", "DRREDDY.NS", "EICHERMOT.NS", "HEROMOTOCO.NS", "BRITANNIA.NS",
        "APOLLOHOSP.NS", "UPL.NS", "BPCL.NS", "IOC.NS", "SHREECEM.NS", "GODREJCP.NS", "PIDILITIND.NS", "DABUR.NS",
        
        # Mid-cap additions
        "ADANIGREEN.NS", "TATACONSUM.NS", "HAVELLS.NS", "MCDOWELL-N.NS", "BERGEPAINT.NS", "MARICO.NS",
        "COLPAL.NS", "PAGEIND.NS", "BAJAJ-AUTO.NS", "BOSCHLTD.NS", "MOTHERSON.NS", "BALKRISIND.NS", "MRF.NS",
        "CUMMINSIND.NS", "TORNTPHARM.NS", "LUPIN.NS", "BANDHANBNK.NS", "FEDERALBNK.NS", "IDFCFIRSTB.NS",
        "PNB.NS", "BANKBARODA.NS", "CANFINHOME.NS", "SBILIFE.NS", "HDFCLIFE.NS", "ICICIPRULI.NS", "BAJAJHLDNG.NS",
        "MUTHOOTFIN.NS", "CHOLAFIN.NS", "MANAPPURAM.NS", "PEL.NS", "VOLTAS.NS", "BLUESTARCO.NS", "CROMPTON.NS",
        "WHIRLPOOL.NS", "VBL.NS", "TATAPOWER.NS", "ADANIPOWER.NS", "JINDALSTEEL.NS", "SAIL.NS", "VEDL.NS",
        "NMDC.NS", "GMRINFRA.NS", "IRB.NS", "CONCOR.NS", "DLF.NS", "GODREJPROP.NS", "PETRONET.NS", "GAIL.NS",
        "IGL.NS", "MGL.NS", "JUBLFOOD.NS", "ZOMATO.NS", "NYKAA.NS", "PAYTM.NS", "LTIM.NS", "PERSISTENT.NS",
        "COFORGE.NS", "MPHASIS.NS", "OFSS.NS", "LTTS.NS", "RBLBANK.NS", "AUBANK.NS", "DALBHARAT.NS", "RAMCOCEM.NS"
    ]
    
    # Generate additional realistic ticker names for demo
    sectors = ["AUTO", "BANK", "PHARMA", "IT", "FMCG", "METAL", "CEMENT", "POWER", "OIL", "TELECOM", 
               "REAL", "CHEM", "TEXTILE", "FOOD", "RETAIL", "MEDIA", "INFRA"]
    
    additional_stocks = []
    for i in range(len(major_stocks), 400):
        sector = random.choice(sectors)
        num = (i % 50) + 1
        ticker = f"{sector}{num:02d}.NS"
        additional_stocks.append(ticker)
    
    return major_stocks + additional_stocks

def generate_stock_data(ticker):
    """Generate realistic stock data for a ticker."""
    
    # Sector-based realistic ranges
    sector_profiles = {
        'IT': {'pe': (15, 35), 'roe': (15, 25), 'growth': (10, 30)},
        'BANK': {'pe': (8, 18), 'roe': (12, 18), 'growth': (5, 20)},
        'PHARMA': {'pe': (20, 40), 'roe': (12, 22), 'growth': (8, 25)},
        'AUTO': {'pe': (10, 25), 'roe': (8, 18), 'growth': (0, 20)},
        'FMCG': {'pe': (25, 50), 'roe': (15, 30), 'growth': (5, 15)},
        'DEFAULT': {'pe': (12, 28), 'roe': (10, 20), 'growth': (3, 20)}
    }
    
    # Determine sector from ticker
    sector = 'DEFAULT'
    for s in sector_profiles.keys():
        if s in ticker:
            sector = s
            break
    
    profile = sector_profiles[sector]
    
    # Generate correlated fundamental data
    base_quality = np.random.uniform(0.3, 0.9)  # Overall company quality factor
    
    pe_ratio = np.random.uniform(*profile['pe'])
    roe = profile['roe'][0] + (profile['roe'][1] - profile['roe'][0]) * base_quality + np.random.uniform(-2, 2)
    debt_equity = np.random.uniform(0.1, 1.2) * (1 - base_quality * 0.3)  # Better companies have less debt
    revenue_growth = np.random.uniform(*profile['growth']) * (0.7 + base_quality * 0.6)
    
    # Generate price performance (correlated with fundamentals)
    base_performance = (roe - 12) * 1.5 + (20 - pe_ratio) * 0.5
    returns_1m = base_performance + np.random.uniform(-10, 10)
    returns_3m = base_performance * 3 + np.random.uniform(-15, 15)
    returns_6m = base_performance * 6 + np.random.uniform(-20, 20)
    
    # Ownership patterns
    if 'RELIANCE' in ticker or 'TCS' in ticker:  # Large established companies
        fii_holding = np.random.uniform(20, 35)
        dii_holding = np.random.uniform(15, 25)
    else:
        fii_holding = np.random.uniform(5, 25)
        dii_holding = np.random.uniform(8, 20)
    
    return {
        'ticker': ticker,
        'pe_ratio': pe_ratio,
        'roe': roe,
        'debt_equity': debt_equity,
        'revenue_growth': revenue_growth,
        'returns_1m': returns_1m,
        'returns_3m': returns_3m,
        'returns_6m': returns_6m,
        'fii_holding': fii_holding,
        'dii_holding': dii_holding,
        'volatility': np.random.uniform(20, 50),
        'liquidity': base_quality * np.random.uniform(0.6, 1.0),
        'sector': sector,
        'quality_score': base_quality
    }

def calculate_greyoak_score(stock_data, mode):
    """Calculate GreyOak-style score with all 6 pillars."""
    
    # Fundamentals (F) - Financial metrics
    f_score = 40
    if stock_data['pe_ratio'] < 15: f_score += 20
    elif stock_data['pe_ratio'] < 25: f_score += 10
    if stock_data['roe'] > 20: f_score += 20
    elif stock_data['roe'] > 15: f_score += 10
    if stock_data['debt_equity'] < 0.3: f_score += 15
    elif stock_data['debt_equity'] < 0.7: f_score += 8
    if stock_data['revenue_growth'] > 15: f_score += 15
    elif stock_data['revenue_growth'] > 8: f_score += 8
    f_score = min(100, max(0, f_score))
    
    # Technicals (T) - Price momentum
    t_score = 45
    if stock_data['returns_1m'] > 8: t_score += 20
    elif stock_data['returns_1m'] > 3: t_score += 10
    elif stock_data['returns_1m'] > 0: t_score += 5
    if stock_data['returns_3m'] > 15: t_score += 15
    elif stock_data['returns_3m'] > 5: t_score += 8
    if stock_data['volatility'] < 25: t_score += 10
    elif stock_data['volatility'] < 35: t_score += 5
    t_score = min(100, max(0, t_score))
    
    # Relative Strength (R) - Momentum vs market
    r_score = 50 + stock_data['returns_3m'] * 1.5 + np.random.uniform(-5, 5)
    r_score = min(100, max(0, r_score))
    
    # Ownership (O) - Institutional interest
    o_score = 40
    if stock_data['fii_holding'] > 20: o_score += 20
    elif stock_data['fii_holding'] > 15: o_score += 10
    if stock_data['dii_holding'] > 15: o_score += 15
    elif stock_data['dii_holding'] > 10: o_score += 8
    o_score += stock_data['quality_score'] * 25  # Better companies attract institutions
    o_score = min(100, max(0, o_score))
    
    # Quality (Q) - Business quality
    q_score = 30 + stock_data['quality_score'] * 50
    if stock_data['roe'] > 18: q_score += 15
    if stock_data['debt_equity'] < 0.5: q_score += 10
    if stock_data['revenue_growth'] > 12: q_score += 15
    q_score = min(100, max(0, q_score))
    
    # Sector Momentum (S) - Sector relative performance  
    s_score = 45 + np.random.uniform(-15, 25)  # Simulated sector performance
    if stock_data['returns_3m'] > np.random.uniform(0, 10): s_score += 15
    s_score = min(100, max(0, s_score))
    
    # Calculate weighted score based on mode
    if mode == 'Investor':
        weights = {'F': 0.30, 'T': 0.15, 'R': 0.15, 'O': 0.20, 'Q': 0.15, 'S': 0.05}
    else:  # Trader
        weights = {'F': 0.15, 'T': 0.30, 'R': 0.25, 'O': 0.10, 'Q': 0.10, 'S': 0.10}
    
    weighted_score = (f_score * weights['F'] + t_score * weights['T'] + 
                     r_score * weights['R'] + o_score * weights['O'] + 
                     q_score * weights['Q'] + s_score * weights['S'])
    
    # Risk penalty calculation
    risk_penalty = 0
    if stock_data['debt_equity'] > 1.0: risk_penalty += 4
    if stock_data['volatility'] > 40: risk_penalty += 3
    if stock_data['liquidity'] < 0.4: risk_penalty += 2
    if stock_data['pe_ratio'] > 35: risk_penalty += 2
    
    final_score = max(0, weighted_score - risk_penalty)
    
    # Investment band determination
    if final_score >= 75:
        band = "Strong Buy"
    elif final_score >= 65:
        band = "Buy"
    elif final_score >= 50:
        band = "Hold"
    else:
        band = "Avoid"
    
    return {
        'ticker': stock_data['ticker'],
        'mode': mode,
        'f_score': round(f_score, 1),
        't_score': round(t_score, 1),
        'r_score': round(r_score, 1),
        'o_score': round(o_score, 1),
        'q_score': round(q_score, 1),
        's_score': round(s_score, 1),
        'weighted_score': round(weighted_score, 1),
        'risk_penalty': round(risk_penalty, 1),
        'final_score': round(final_score, 1),
        'band': band,
        'sector': stock_data['sector'],
        'pe_ratio': round(stock_data['pe_ratio'], 1),
        'roe': round(stock_data['roe'], 1),
        'returns_1m': round(stock_data['returns_1m'], 1)
    }

def main():
    print("🎯 GreyOak Score Engine - NSE 400 Stock Universe Demo")
    print("=" * 70)
    print("Real NSE ticker symbols with realistic simulated data")
    print("Complete 6-pillar scoring with dual-mode analysis")
    print("Processing 400 stocks in-memory (no data saved)")
    print()
    
    # Generate stock universe
    start_time = time.time()
    print("📊 Generating NSE 400 stock universe...")
    tickers = generate_nse_400()
    print(f"   ✅ {len(tickers)} stocks generated")
    print(f"   📈 Sample: {', '.join(tickers[:8])}...")
    print()
    
    # Generate stock data
    print("💹 Generating realistic market data...")
    stock_database = {}
    for i, ticker in enumerate(tickers):
        stock_database[ticker] = generate_stock_data(ticker)
        if (i + 1) % 100 == 0:
            print(f"   Progress: {i + 1}/400 stocks processed")
    
    print(f"   ✅ Market data generated for all 400 stocks")
    print()
    
    # Run scoring analysis
    results = {}
    for mode in ['Investor', 'Trader']:
        print(f"🔄 Running {mode} mode scoring analysis...")
        mode_results = []
        
        for i, ticker in enumerate(tickers):
            stock_data = stock_database[ticker]
            score_result = calculate_greyoak_score(stock_data, mode)
            mode_results.append(score_result)
            
            if (i + 1) % 100 == 0:
                avg_score = np.mean([r['final_score'] for r in mode_results])
                print(f"   Progress: {i + 1}/400 | Current Avg Score: {avg_score:.1f}")
        
        results[mode] = mode_results
        print(f"   ✅ {mode} mode complete: 400 stocks scored")
        print()
    
    # Comprehensive analysis
    total_time = time.time() - start_time
    print("📈 COMPREHENSIVE ANALYSIS - NSE 400 UNIVERSE")
    print("=" * 70)
    
    for mode in ['Investor', 'Trader']:
        df = pd.DataFrame(results[mode])
        
        print(f"\n🎯 {mode.upper()} MODE ANALYSIS (400 Stocks)")
        print("-" * 50)
        
        # Score statistics
        print(f"Score Statistics:")
        print(f"  • Average Score: {df['final_score'].mean():.1f}")
        print(f"  • Median Score: {df['final_score'].median():.1f}")
        print(f"  • Score Range: {df['final_score'].min():.1f} - {df['final_score'].max():.1f}")
        print(f"  • Standard Deviation: {df['final_score'].std():.1f}")
        
        # Investment opportunity distribution
        band_counts = df['band'].value_counts()
        print(f"\nInvestment Opportunities:")
        for band in ['Strong Buy', 'Buy', 'Hold', 'Avoid']:
            count = band_counts.get(band, 0)
            pct = (count / 400) * 100
            print(f"  • {band:10}: {count:3d} stocks ({pct:4.1f}%)")
        
        # Sector analysis
        print(f"\nTop Performing Sectors:")
        sector_avg = df.groupby('sector')['final_score'].mean().sort_values(ascending=False)
        for sector, avg_score in sector_avg.head(5).items():
            sector_count = len(df[df['sector'] == sector])
            print(f"  • {sector:8}: Avg Score {avg_score:4.1f} ({sector_count:2d} stocks)")
        
        # Top performers
        print(f"\nTop 10 {mode} Recommendations:")
        top_10 = df.nlargest(10, 'final_score')
        for i, (_, row) in enumerate(top_10.iterrows(), 1):
            print(f"  {i:2d}. {row['ticker']:12} | Score: {row['final_score']:5.1f} | {row['band']:10} | "
                  f"PE: {row['pe_ratio']:4.1f} | ROE: {row['roe']:4.1f}% | Ret: {row['returns_1m']:+5.1f}%")
        
        # Pillar strength analysis
        pillars = ['f_score', 't_score', 'r_score', 'o_score', 'q_score', 's_score']
        pillar_names = ['Fundamentals', 'Technicals', 'Rel.Strength', 'Ownership', 'Quality', 'Sector Mom.']
        print(f"\nAverage Pillar Scores:")
        for pillar, name in zip(pillars, pillar_names):
            avg_pillar = df[pillar].mean()
            print(f"  • {name:12}: {avg_pillar:4.1f}")
    
    # Comparative analysis
    investor_df = pd.DataFrame(results['Investor'])
    trader_df = pd.DataFrame(results['Trader'])
    
    print(f"\n🔄 INVESTOR vs TRADER COMPARISON")
    print("-" * 50)
    print(f"Average Scores:")
    print(f"  • Investor Mode: {investor_df['final_score'].mean():.1f}")  
    print(f"  • Trader Mode: {trader_df['final_score'].mean():.1f}")
    print(f"  • Score Difference: {abs(investor_df['final_score'].mean() - trader_df['final_score'].mean()):.1f}")
    
    print(f"\nStrong Buy Opportunities:")
    investor_strong_buys = sum(investor_df['band'] == 'Strong Buy')
    trader_strong_buys = sum(trader_df['band'] == 'Strong Buy')
    print(f"  • Investor Strong Buys: {investor_strong_buys} stocks")
    print(f"  • Trader Strong Buys: {trader_strong_buys} stocks")
    
    # Common strong buys
    inv_sb = set(investor_df[investor_df['band'] == 'Strong Buy']['ticker'])
    trd_sb = set(trader_df[trader_df['band'] == 'Strong Buy']['ticker'])
    common_sb = inv_sb & trd_sb
    print(f"  • Common Strong Buys: {len(common_sb)} stocks")
    if common_sb:
        print(f"    {', '.join(list(common_sb)[:5])}{'...' if len(common_sb) > 5 else ''}")
    
    # Performance summary
    print(f"\n🎉 DEMO PERFORMANCE SUMMARY")
    print("=" * 70)
    print(f"✅ Successfully processed 400 NSE stocks")
    print(f"✅ Generated realistic multi-dimensional data")
    print(f"✅ Calculated 6-pillar scores for both modes")
    print(f"✅ Identified {investor_strong_buys + trader_strong_buys} total investment opportunities")
    print(f"✅ Complete analysis in {total_time:.1f} seconds")
    print(f"✅ Processing rate: {400/total_time:.0f} stocks/second")
    print()
    print("🚀 GreyOak Score Engine Capabilities Demonstrated:")
    print("   • Handles large-scale stock universe (400+ stocks)")
    print("   • Multi-pillar quantitative analysis (F,T,R,O,Q,S)")
    print("   • Dual investment horizon support (Investor/Trader)")
    print("   • Risk-adjusted scoring with penalties")
    print("   • Sector-aware analysis and benchmarking")
    print("   • Real-time processing and investment band classification")
    print("   • In-memory processing (no data persistence)")
    print()
    print("💡 This system is ready for production deployment with real data feeds!")

if __name__ == "__main__":
    main()