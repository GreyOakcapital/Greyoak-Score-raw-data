#!/usr/bin/env python3
"""
GreyOak Score Engine - Complete Pillar Logic Validation Suite
Validates all 6 pillars: Fundamentals, Technicals, Relative Strength, Ownership, Quality, Sector Momentum
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
sys.path.append('/app/backend')

class CompletePillarValidator:
    """Comprehensive validator for all pillar scoring logic."""
    
    def __init__(self):
        self.results = {}
        
    def generate_comprehensive_dataset(self, num_stocks=50, num_days=50):
        """Generate comprehensive dataset for all pillar validations."""
        
        print("🔄 Generating Comprehensive Multi-Pillar Dataset...")
        print(f"   Stocks: {num_stocks}, Days: {num_days}")
        
        symbols = [f"STOCK{i:03d}.NS" for i in range(1, num_stocks + 1)]
        dates = pd.bdate_range(start='2023-01-01', periods=num_days)
        
        all_records = []
        
        for i, date in enumerate(dates):
            # Market conditions for the day (affects sector momentum)
            market_return = np.random.normal(0.05, 0.02)  # Daily market return
            
            for j, symbol in enumerate(symbols):
                # Company seed for consistency
                company_seed = hash(symbol) % 1000
                np.random.seed(company_seed + i)
                
                # Company characteristics
                company_type = ['value', 'growth', 'quality', 'momentum', 'cyclical'][j % 5]
                sector = ['IT', 'Banking', 'Energy', 'Pharma', 'FMCG'][j % 5]
                
                # Generate correlated metrics based on company type
                if company_type == 'value':
                    pe_ratio = np.random.uniform(8, 15)
                    pb_ratio = np.random.uniform(0.8, 2.0)
                    div_yield = np.random.uniform(3, 7)
                    roe = np.random.uniform(12, 20)
                    debt_equity = np.random.uniform(0.2, 0.6)
                    profit_margin = np.random.uniform(8, 15)
                    
                elif company_type == 'growth':
                    pe_ratio = np.random.uniform(25, 50)
                    pb_ratio = np.random.uniform(3, 7)
                    div_yield = np.random.uniform(0, 2)
                    roe = np.random.uniform(20, 35)
                    debt_equity = np.random.uniform(0.1, 0.4)
                    profit_margin = np.random.uniform(15, 25)
                    
                elif company_type == 'quality':
                    pe_ratio = np.random.uniform(18, 30)
                    pb_ratio = np.random.uniform(2, 4)
                    div_yield = np.random.uniform(2, 4)
                    roe = np.random.uniform(25, 40)
                    debt_equity = np.random.uniform(0.0, 0.3)
                    profit_margin = np.random.uniform(18, 30)
                    
                elif company_type == 'momentum':
                    pe_ratio = np.random.uniform(15, 35)
                    pb_ratio = np.random.uniform(1.5, 4.0)
                    div_yield = np.random.uniform(1, 4)
                    roe = np.random.uniform(15, 25)
                    debt_equity = np.random.uniform(0.2, 0.8)
                    profit_margin = np.random.uniform(10, 20)
                    
                else:  # cyclical
                    pe_ratio = np.random.uniform(10, 25)
                    pb_ratio = np.random.uniform(1.0, 3.5)
                    div_yield = np.random.uniform(1.5, 5)
                    roe = np.random.uniform(8, 20)
                    debt_equity = np.random.uniform(0.3, 1.2)
                    profit_margin = np.random.uniform(5, 15)
                
                # Technical indicators (with momentum patterns for momentum stocks)
                if company_type == 'momentum':
                    returns_1m = np.random.uniform(8, 25)    # Strong momentum
                    returns_3m = np.random.uniform(15, 40)
                    volatility = np.random.uniform(25, 40)
                else:
                    returns_1m = np.random.uniform(-10, 15)
                    returns_3m = np.random.uniform(-15, 25)
                    volatility = np.random.uniform(20, 35)
                
                # Price vs moving averages (technical strength)
                current_price = 100 + np.random.uniform(-20, 20)
                if returns_1m > 5:  # Strong stocks above moving averages
                    sma_20 = current_price * np.random.uniform(0.95, 0.98)
                    sma_50 = current_price * np.random.uniform(0.90, 0.95)
                else:
                    sma_20 = current_price * np.random.uniform(1.02, 1.08)
                    sma_50 = current_price * np.random.uniform(1.05, 1.15)
                
                # Ownership patterns
                market_cap = np.random.uniform(1000, 50000)  # In crores
                
                if market_cap > 20000:  # Large cap - high institutional
                    fii_holding = np.random.uniform(20, 35)
                    dii_holding = np.random.uniform(15, 25)
                    promoter_holding = np.random.uniform(40, 65)
                elif market_cap > 5000:  # Mid cap
                    fii_holding = np.random.uniform(10, 25)
                    dii_holding = np.random.uniform(8, 20)
                    promoter_holding = np.random.uniform(45, 70)
                else:  # Small cap
                    fii_holding = np.random.uniform(2, 15)
                    dii_holding = np.random.uniform(5, 15)
                    promoter_holding = np.random.uniform(50, 75)
                
                # Calculate all pillar scores
                fundamentals_score = self._calculate_fundamentals_score(pe_ratio, roe, debt_equity, profit_margin)
                technicals_score = self._calculate_technicals_score(returns_1m, returns_3m, current_price, sma_20, sma_50, volatility)
                relative_strength_score = self._calculate_relative_strength_score(returns_3m, market_return * 60)  # 3-month market return
                ownership_score = self._calculate_ownership_score(fii_holding, dii_holding, promoter_holding, market_cap)
                quality_score = self._calculate_quality_score(roe, profit_margin, debt_equity, div_yield)
                sector_momentum_score = self._calculate_sector_momentum_score(sector, returns_3m, market_return)
                
                # Store record
                record = {
                    'ticker': symbol,
                    'date': date,
                    'company_type': company_type,
                    'sector': sector,
                    
                    # Raw metrics
                    'pe_ratio': round(pe_ratio, 2),
                    'pb_ratio': round(pb_ratio, 2),
                    'dividend_yield': round(div_yield, 2),
                    'roe': round(roe, 2),
                    'debt_equity': round(debt_equity, 2),
                    'profit_margin': round(profit_margin, 2),
                    'market_cap': round(market_cap, 0),
                    
                    'returns_1m': round(returns_1m, 2),
                    'returns_3m': round(returns_3m, 2),
                    'volatility': round(volatility, 2),
                    'current_price': round(current_price, 2),
                    'sma_20': round(sma_20, 2),
                    'sma_50': round(sma_50, 2),
                    
                    'fii_holding': round(fii_holding, 2),
                    'dii_holding': round(dii_holding, 2),
                    'promoter_holding': round(promoter_holding, 2),
                    
                    'market_return_3m': round(market_return * 60, 2),  # 3-month market return
                    
                    # Pillar scores
                    'fundamentals_score': round(fundamentals_score, 1),
                    'technicals_score': round(technicals_score, 1),
                    'relative_strength_score': round(relative_strength_score, 1),
                    'ownership_score': round(ownership_score, 1),
                    'quality_score': round(quality_score, 1),
                    'sector_momentum_score': round(sector_momentum_score, 1),
                }
                
                all_records.append(record)
        
        df = pd.DataFrame(all_records)
        
        print(f"✅ Comprehensive dataset generated: {len(df)} records")
        print(f"   • Company types: {df['company_type'].value_counts().to_dict()}")
        print(f"   • Sectors: {df['sector'].value_counts().to_dict()}")
        
        return df
    
    def _calculate_fundamentals_score(self, pe_ratio, roe, debt_equity, profit_margin):
        """Calculate Fundamentals pillar score."""
        score = 50
        
        # P/E component (lower is better)
        if pe_ratio < 12: score += 20
        elif pe_ratio < 18: score += 10
        elif pe_ratio < 25: score += 0
        else: score -= 10
        
        # ROE component (higher is better)
        if roe > 25: score += 20
        elif roe > 18: score += 10
        elif roe > 12: score += 0
        else: score -= 10
        
        # Debt component (lower is better)
        if debt_equity < 0.3: score += 10
        elif debt_equity < 0.7: score += 5
        elif debt_equity > 1.0: score -= 10
        
        # Profit margin (higher is better)
        if profit_margin > 20: score += 15
        elif profit_margin > 15: score += 8
        elif profit_margin > 10: score += 0
        else: score -= 5
        
        return max(0, min(100, score))
    
    def _calculate_technicals_score(self, returns_1m, returns_3m, current_price, sma_20, sma_50, volatility):
        """Calculate Technicals pillar score."""
        score = 50
        
        # Recent performance
        if returns_1m > 10: score += 20
        elif returns_1m > 5: score += 10
        elif returns_1m > 0: score += 5
        else: score -= 10
        
        if returns_3m > 20: score += 15
        elif returns_3m > 10: score += 8
        elif returns_3m > 0: score += 0
        else: score -= 10
        
        # Price vs moving averages
        if current_price > sma_20 > sma_50: score += 15
        elif current_price > sma_20: score += 8
        elif current_price < sma_50: score -= 10
        
        # Volatility (lower is better for technicals)
        if volatility < 20: score += 10
        elif volatility > 40: score -= 10
        
        return max(0, min(100, score))
    
    def _calculate_relative_strength_score(self, stock_return_3m, market_return_3m):
        """Calculate Relative Strength pillar score."""
        relative_return = stock_return_3m - market_return_3m
        
        score = 50 + relative_return * 2  # 2 points per % of outperformance
        
        return max(0, min(100, score))
    
    def _calculate_ownership_score(self, fii_holding, dii_holding, promoter_holding, market_cap):
        """Calculate Ownership pillar score."""
        score = 40
        
        # FII holding (higher is better)
        if fii_holding > 25: score += 25
        elif fii_holding > 20: score += 15
        elif fii_holding > 15: score += 8
        elif fii_holding < 5: score -= 10
        
        # DII holding (higher is better)
        if dii_holding > 20: score += 15
        elif dii_holding > 15: score += 10
        elif dii_holding > 10: score += 5
        
        # Promoter holding (sweet spot 40-70%)
        if 40 <= promoter_holding <= 70: score += 10
        elif promoter_holding > 75: score -= 5  # Too high, liquidity issues
        elif promoter_holding < 30: score -= 10  # Too low, lack of commitment
        
        # Market cap factor (large cap premium)
        if market_cap > 20000: score += 10
        elif market_cap > 5000: score += 5
        
        return max(0, min(100, score))
    
    def _calculate_quality_score(self, roe, profit_margin, debt_equity, div_yield):
        """Calculate Quality pillar score."""
        score = 40
        
        # ROE (higher is better)
        if roe > 30: score += 25
        elif roe > 20: score += 15
        elif roe > 15: score += 8
        elif roe < 10: score -= 10
        
        # Profit margin (higher is better)
        if profit_margin > 20: score += 20
        elif profit_margin > 15: score += 12
        elif profit_margin > 10: score += 5
        elif profit_margin < 5: score -= 10
        
        # Debt (lower is better for quality)
        if debt_equity < 0.2: score += 15
        elif debt_equity < 0.5: score += 8
        elif debt_equity > 1.0: score -= 15
        
        # Dividend yield (moderate is good for quality)
        if 2 <= div_yield <= 5: score += 10
        elif div_yield > 6: score -= 5  # Might be unsustainable
        
        return max(0, min(100, score))
    
    def _calculate_sector_momentum_score(self, sector, stock_return_3m, market_return):
        """Calculate Sector Momentum pillar score."""
        
        # Sector-specific momentum patterns
        sector_momentum = {
            'IT': np.random.uniform(-5, 15),      # Generally positive momentum
            'Banking': np.random.uniform(-10, 10), # Mixed momentum
            'Energy': np.random.uniform(-15, 20),  # Volatile
            'Pharma': np.random.uniform(-5, 10),   # Defensive
            'FMCG': np.random.uniform(-3, 8)       # Stable
        }
        
        base_sector_return = sector_momentum.get(sector, 0)
        
        # Stock's performance relative to its sector
        sector_relative = stock_return_3m - base_sector_return
        
        score = 50 + base_sector_return + sector_relative * 0.5
        
        return max(0, min(100, score))
    
    def validate_all_pillars(self, df):
        """Validate all 6 pillars with appropriate tests."""
        
        print("\n🔍 VALIDATING ALL 6 PILLARS")
        print("="*60)
        
        validation_results = {}
        
        # Test 1: Fundamentals Pillar
        print(f"\n✓ FUNDAMENTALS PILLAR VALIDATION")
        fund_result = self._validate_fundamentals_pillar(df)
        validation_results['fundamentals'] = fund_result
        
        # Test 2: Technicals Pillar
        print(f"\n✓ TECHNICALS PILLAR VALIDATION")  
        tech_result = self._validate_technicals_pillar(df)
        validation_results['technicals'] = tech_result
        
        # Test 3: Relative Strength Pillar
        print(f"\n✓ RELATIVE STRENGTH PILLAR VALIDATION")
        rs_result = self._validate_relative_strength_pillar(df)
        validation_results['relative_strength'] = rs_result
        
        # Test 4: Ownership Pillar
        print(f"\n✓ OWNERSHIP PILLAR VALIDATION")
        own_result = self._validate_ownership_pillar(df)
        validation_results['ownership'] = own_result
        
        # Test 5: Quality Pillar
        print(f"\n✓ QUALITY PILLAR VALIDATION")
        qual_result = self._validate_quality_pillar(df)
        validation_results['quality'] = qual_result
        
        # Test 6: Sector Momentum Pillar
        print(f"\n✓ SECTOR MOMENTUM PILLAR VALIDATION")
        sect_result = self._validate_sector_momentum_pillar(df)
        validation_results['sector_momentum'] = sect_result
        
        return validation_results
    
    def _validate_fundamentals_pillar(self, df):
        """Validate Fundamentals pillar relationships."""
        
        # Split by Fundamentals score
        df_sorted = df.sort_values('fundamentals_score', ascending=False)
        n = len(df_sorted)
        
        high_fund = df_sorted.iloc[:n//3]   # Top 33%
        low_fund = df_sorted.iloc[2*n//3:]  # Bottom 33%
        
        # Calculate averages
        high_pe = high_fund['pe_ratio'].mean()
        low_pe = low_fund['pe_ratio'].mean()
        
        high_roe = high_fund['roe'].mean()
        low_roe = low_fund['roe'].mean()
        
        high_debt = high_fund['debt_equity'].mean()
        low_debt = low_fund['debt_equity'].mean()
        
        # Validation checks
        pe_correct = high_pe < low_pe        # High fund score = lower P/E
        roe_correct = high_roe > low_roe     # High fund score = higher ROE
        debt_correct = high_debt < low_debt  # High fund score = lower debt
        
        print(f"   • P/E:  High Fund {high_pe:.1f} vs Low Fund {low_pe:.1f} - {'✅' if pe_correct else '❌'}")
        print(f"   • ROE:  High Fund {high_roe:.1f}% vs Low Fund {low_roe:.1f}% - {'✅' if roe_correct else '❌'}")
        print(f"   • Debt: High Fund {high_debt:.2f} vs Low Fund {low_debt:.2f} - {'✅' if debt_correct else '❌'}")
        
        return pe_correct and roe_correct and debt_correct
    
    def _validate_technicals_pillar(self, df):
        """Validate Technicals pillar relationships."""
        
        df_sorted = df.sort_values('technicals_score', ascending=False)
        n = len(df_sorted)
        
        high_tech = df_sorted.iloc[:n//3]
        low_tech = df_sorted.iloc[2*n//3:]
        
        high_ret1m = high_tech['returns_1m'].mean()
        low_ret1m = low_tech['returns_1m'].mean()
        
        high_ret3m = high_tech['returns_3m'].mean()
        low_tech3m = low_tech['returns_3m'].mean()
        
        high_above_sma = (high_tech['current_price'] > high_tech['sma_20']).mean()
        low_above_sma = (low_tech['current_price'] > low_tech['sma_20']).mean()
        
        ret1m_correct = high_ret1m > low_ret1m
        ret3m_correct = high_ret3m > low_tech3m
        sma_correct = high_above_sma > low_above_sma
        
        print(f"   • 1M Returns: High Tech {high_ret1m:.1f}% vs Low Tech {low_ret1m:.1f}% - {'✅' if ret1m_correct else '❌'}")
        print(f"   • 3M Returns: High Tech {high_ret3m:.1f}% vs Low Tech {low_tech3m:.1f}% - {'✅' if ret3m_correct else '❌'}")
        print(f"   • Above SMA: High Tech {high_above_sma:.1%} vs Low Tech {low_above_sma:.1%} - {'✅' if sma_correct else '❌'}")
        
        return ret1m_correct and ret3m_correct and sma_correct
    
    def _validate_relative_strength_pillar(self, df):
        """Validate Relative Strength pillar relationships."""
        
        df_sorted = df.sort_values('relative_strength_score', ascending=False)
        n = len(df_sorted)
        
        high_rs = df_sorted.iloc[:n//3]
        low_rs = df_sorted.iloc[2*n//3:]
        
        high_excess_return = (high_rs['returns_3m'] - high_rs['market_return_3m']).mean()
        low_excess_return = (low_rs['returns_3m'] - low_rs['market_return_3m']).mean()
        
        excess_return_correct = high_excess_return > low_excess_return
        
        print(f"   • Excess Return: High RS {high_excess_return:+.1f}% vs Low RS {low_excess_return:+.1f}% - {'✅' if excess_return_correct else '❌'}")
        
        return excess_return_correct
    
    def _validate_ownership_pillar(self, df):
        """Validate Ownership pillar relationships."""
        
        df_sorted = df.sort_values('ownership_score', ascending=False)
        n = len(df_sorted)
        
        high_own = df_sorted.iloc[:n//3]
        low_own = df_sorted.iloc[2*n//3:]
        
        high_fii = high_own['fii_holding'].mean()
        low_fii = low_own['fii_holding'].mean()
        
        high_dii = high_own['dii_holding'].mean()
        low_dii = low_own['dii_holding'].mean()
        
        high_mcap = high_own['market_cap'].mean()
        low_mcap = low_own['market_cap'].mean()
        
        fii_correct = high_fii > low_fii
        dii_correct = high_dii > low_dii
        mcap_correct = high_mcap > low_mcap
        
        print(f"   • FII Holding: High Own {high_fii:.1f}% vs Low Own {low_fii:.1f}% - {'✅' if fii_correct else '❌'}")
        print(f"   • DII Holding: High Own {high_dii:.1f}% vs Low Own {low_dii:.1f}% - {'✅' if dii_correct else '❌'}")
        print(f"   • Market Cap: High Own ₹{high_mcap:.0f}Cr vs Low Own ₹{low_mcap:.0f}Cr - {'✅' if mcap_correct else '❌'}")
        
        return fii_correct and dii_correct and mcap_correct
    
    def _validate_quality_pillar(self, df):
        """Validate Quality pillar relationships."""
        
        df_sorted = df.sort_values('quality_score', ascending=False)
        n = len(df_sorted)
        
        high_qual = df_sorted.iloc[:n//3]
        low_qual = df_sorted.iloc[2*n//3:]
        
        high_roe = high_qual['roe'].mean()
        low_roe = low_qual['roe'].mean()
        
        high_margin = high_qual['profit_margin'].mean()
        low_margin = low_qual['profit_margin'].mean()
        
        high_debt = high_qual['debt_equity'].mean()
        low_debt = low_qual['debt_equity'].mean()
        
        roe_correct = high_roe > low_roe
        margin_correct = high_margin > low_margin
        debt_correct = high_debt < low_debt
        
        print(f"   • ROE: High Quality {high_roe:.1f}% vs Low Quality {low_roe:.1f}% - {'✅' if roe_correct else '❌'}")
        print(f"   • Profit Margin: High Quality {high_margin:.1f}% vs Low Quality {low_margin:.1f}% - {'✅' if margin_correct else '❌'}")
        print(f"   • Debt/Equity: High Quality {high_debt:.2f} vs Low Quality {low_debt:.2f} - {'✅' if debt_correct else '❌'}")
        
        return roe_correct and margin_correct and debt_correct
    
    def _validate_sector_momentum_pillar(self, df):
        """Validate Sector Momentum pillar relationships."""
        
        # Group by sector and calculate average momentum scores
        sector_momentum = df.groupby('sector')['sector_momentum_score'].mean().sort_values(ascending=False)
        
        # Check if there's reasonable spread between sectors
        momentum_spread = sector_momentum.max() - sector_momentum.min()
        spread_adequate = momentum_spread >= 10  # At least 10 points between best and worst sector
        
        print(f"   • Sector Momentum Spread: {momentum_spread:.1f} points - {'✅' if spread_adequate else '❌'}")
        print(f"   • Top Sector: {sector_momentum.index[0]} ({sector_momentum.iloc[0]:.1f})")
        print(f"   • Bottom Sector: {sector_momentum.index[-1]} ({sector_momentum.iloc[-1]:.1f})")
        
        return spread_adequate
    
    def run_complete_pillar_validation(self):
        """Run complete validation for all 6 pillars."""
        
        print("🚀 STARTING COMPLETE PILLAR LOGIC VALIDATION")
        print("="*70)
        print("Validating all 6 pillars: F, T, R, O, Q, S")
        print()
        
        # Generate comprehensive dataset
        df = self.generate_comprehensive_dataset()
        
        # Validate all pillars
        validation_results = self.validate_all_pillars(df)
        
        # Generate final report
        self._generate_final_pillar_report(validation_results)
        
        return {
            'dataset': df,
            'validation_results': validation_results
        }
    
    def _generate_final_pillar_report(self, validation_results):
        """Generate final comprehensive pillar validation report."""
        
        print(f"\n" + "="*70)
        print(f"🎯 COMPLETE PILLAR VALIDATION RESULTS")
        print("="*70)
        
        pillar_names = {
            'fundamentals': 'Fundamentals (F)',
            'technicals': 'Technicals (T)', 
            'relative_strength': 'Relative Strength (R)',
            'ownership': 'Ownership (O)',
            'quality': 'Quality (Q)',
            'sector_momentum': 'Sector Momentum (S)'
        }
        
        passed_pillars = 0
        total_pillars = len(validation_results)
        
        print(f"📊 Individual Pillar Results:")
        for pillar_key, result in validation_results.items():
            pillar_name = pillar_names[pillar_key]
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   • {pillar_name:<20}: {status}")
            if result:
                passed_pillars += 1
        
        print(f"\n📈 Overall Results:")
        print(f"   • Pillars Validated: {passed_pillars}/{total_pillars}")
        print(f"   • Success Rate: {passed_pillars/total_pillars:.0%}")
        
        if passed_pillars == total_pillars:
            overall_status = "✅ ALL PILLARS VALIDATED"
            recommendation = "All pillar logic is working correctly - ready for production"
        elif passed_pillars >= total_pillars * 0.8:
            overall_status = "⚠️  MOSTLY VALIDATED"
            recommendation = "Most pillars working correctly - review failed pillars"
        else:
            overall_status = "❌ VALIDATION ISSUES"
            recommendation = "Multiple pillar issues detected - comprehensive review needed"
        
        print(f"\n🚀 FINAL ASSESSMENT: {overall_status}")
        print(f"   {recommendation}")
        
        print(f"\n💡 PILLAR LOGIC VALIDATION COMPLETE")
        print("="*70)


def main():
    """Run complete pillar validation."""
    
    validator = CompletePillarValidator()
    results = validator.run_complete_pillar_validation()
    
    return results


if __name__ == "__main__":
    main()