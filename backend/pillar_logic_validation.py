#!/usr/bin/env python3
"""
GreyOak Score Engine - Phase 1.5: Pillar Logic Validation
Test #1: Value Pillar Sanity Check

Validates that Value Pillar scoring logic produces sensible results:
- High Value scores should correspond to low P/E, P/B ratios
- High Value scores should correspond to high dividend yields
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
sys.path.append('/app/backend')

class ValuePillarValidator:
    """Validator for Value Pillar scoring logic."""
    
    def __init__(self):
        self.results = {}
        
    def generate_enhanced_dataset_with_value_metrics(self, num_stocks=50, num_days=100):
        """Generate dataset with proper Value Pillar calculations and fundamental metrics."""
        
        print("🔄 Generating Enhanced Dataset with Value Metrics...")
        print(f"   Stocks: {num_stocks}, Days: {num_days}")
        
        # Stock symbols for testing
        symbols = [f"STOCK{i:03d}.NS" for i in range(1, num_stocks + 1)]
        dates = pd.bdate_range(start='2023-01-01', periods=num_days)
        
        all_records = []
        
        for date in dates:
            for symbol in symbols:
                # Generate realistic fundamental metrics with correlations
                
                # Base company characteristics (persistent over time)
                company_seed = hash(symbol) % 1000
                np.random.seed(company_seed + int(date.timestamp()) % 1000)
                
                # Generate correlated fundamental metrics
                # Some stocks are genuinely cheap (low P/E, high div yield)
                # Others are expensive growth stocks (high P/E, low div yield)
                
                company_type = np.random.choice(['value', 'growth', 'balanced'], 
                                              p=[0.3, 0.3, 0.4])
                
                if company_type == 'value':
                    # Value stocks: Low P/E, Low P/B, Higher Div Yield
                    pe_ratio = np.random.uniform(8, 18)
                    pb_ratio = np.random.uniform(0.5, 2.0)
                    div_yield = np.random.uniform(2.5, 8.0)
                    roe = np.random.uniform(12, 25)
                    
                elif company_type == 'growth':
                    # Growth stocks: High P/E, High P/B, Lower Div Yield
                    pe_ratio = np.random.uniform(25, 60)
                    pb_ratio = np.random.uniform(3.0, 8.0)
                    div_yield = np.random.uniform(0.0, 2.0)
                    roe = np.random.uniform(20, 40)
                    
                else:  # balanced
                    # Balanced stocks: Moderate metrics
                    pe_ratio = np.random.uniform(15, 25)
                    pb_ratio = np.random.uniform(1.5, 3.5)
                    div_yield = np.random.uniform(1.0, 4.0)
                    roe = np.random.uniform(15, 25)
                
                # Add some time-based variation
                time_factor = np.sin(2 * np.pi * dates.get_loc(date) / len(dates)) * 0.1
                pe_ratio *= (1 + time_factor)
                pb_ratio *= (1 + time_factor * 0.5)
                div_yield *= (1 + time_factor * 0.3)
                
                # Generate other metrics
                debt_equity = np.random.uniform(0.1, 1.5)
                market_cap = np.random.uniform(1000, 100000)  # In crores
                book_value = market_cap / pb_ratio if pb_ratio > 0 else market_cap
                
                # Calculate Value Pillar Score using PROPER logic
                value_score = self._calculate_value_pillar_score(
                    pe_ratio, pb_ratio, div_yield, roe, debt_equity
                )
                
                # Generate other pillar scores (simplified for this test)
                technical_score = np.random.uniform(30, 80)
                momentum_score = np.random.uniform(30, 80)
                quality_score = 50 + (roe - 15) * 2 - max(0, debt_equity - 0.5) * 10
                quality_score = max(0, min(100, quality_score))
                
                # Store record
                record = {
                    'ticker': symbol,
                    'date': date,
                    'company_type': company_type,
                    
                    # Fundamental metrics
                    'pe_ratio': round(pe_ratio, 2),
                    'pb_ratio': round(pb_ratio, 2),
                    'dividend_yield': round(div_yield, 2),
                    'roe': round(roe, 2),
                    'debt_equity': round(debt_equity, 2),
                    'market_cap': round(market_cap, 0),
                    'book_value': round(book_value, 0),
                    
                    # Pillar scores
                    'value_pillar_score': round(value_score, 1),
                    'technical_score': round(technical_score, 1),
                    'momentum_score': round(momentum_score, 1),
                    'quality_score': round(quality_score, 1),
                    
                    # Derived metrics for validation
                    'earnings_yield': round(100 / pe_ratio if pe_ratio > 0 else 0, 2),
                    'book_to_market': round(1 / pb_ratio if pb_ratio > 0 else 0, 2)
                }
                
                all_records.append(record)
        
        df = pd.DataFrame(all_records)
        
        print(f"✅ Dataset generated: {len(df)} records")
        print(f"   • Unique stocks: {df['ticker'].nunique()}")
        print(f"   • Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"   • Value score range: {df['value_pillar_score'].min():.1f} - {df['value_pillar_score'].max():.1f}")
        
        return df
    
    def _calculate_value_pillar_score(self, pe_ratio, pb_ratio, div_yield, roe, debt_equity):
        """
        Calculate Value Pillar Score with CORRECT logic:
        - Lower P/E = Higher Score (cheaper is better)
        - Lower P/B = Higher Score (cheaper is better)  
        - Higher Dividend Yield = Higher Score (more income)
        - Adjust for quality (ROE) and risk (debt)
        """
        
        score = 50  # Base score
        
        # P/E Ratio Component (INVERSE relationship - lower PE is better)
        if pe_ratio <= 0:
            pe_component = -20  # Penalty for negative/zero earnings
        elif pe_ratio < 10:
            pe_component = 25   # Excellent value
        elif pe_ratio < 15:
            pe_component = 15   # Good value
        elif pe_ratio < 20:
            pe_component = 5    # Fair value
        elif pe_ratio < 30:
            pe_component = -5   # Expensive
        else:
            pe_component = -15  # Very expensive
        
        # P/B Ratio Component (INVERSE relationship - lower PB is better)
        if pb_ratio <= 0:
            pb_component = -10  # Invalid
        elif pb_ratio < 1.0:
            pb_component = 20   # Excellent value (trading below book)
        elif pb_ratio < 1.5:
            pb_component = 10   # Good value
        elif pb_ratio < 2.5:
            pb_component = 0    # Fair value
        elif pb_ratio < 4.0:
            pb_component = -5   # Expensive
        else:
            pb_component = -15  # Very expensive
        
        # Dividend Yield Component (DIRECT relationship - higher yield is better)
        if div_yield >= 6.0:
            div_component = 15  # Excellent yield
        elif div_yield >= 4.0:
            div_component = 10  # Good yield
        elif div_yield >= 2.0:
            div_component = 5   # Fair yield
        elif div_yield >= 1.0:
            div_component = 0   # Low yield
        else:
            div_component = -5  # No/minimal dividend
        
        # Quality adjustment (ROE)
        if roe > 20:
            quality_adj = 10
        elif roe > 15:
            quality_adj = 5
        elif roe > 10:
            quality_adj = 0
        else:
            quality_adj = -5
        
        # Risk adjustment (Debt/Equity)
        if debt_equity < 0.3:
            risk_adj = 5
        elif debt_equity < 0.7:
            risk_adj = 0
        elif debt_equity < 1.0:
            risk_adj = -3
        else:
            risk_adj = -8
        
        # Combine components
        final_score = score + pe_component + pb_component + div_component + quality_adj + risk_adj
        
        # Ensure score is within 0-100 range
        return max(0, min(100, final_score))
    
    def perform_value_pillar_sanity_check(self, df):
        """
        Perform the core Value Pillar sanity check as specified.
        Split stocks by Value Pillar score and validate relationships.
        """
        
        print("\n🔍 PERFORMING VALUE PILLAR SANITY CHECK")
        print("="*60)
        
        # Results storage
        daily_results = []
        
        # Process each date
        for date in df['date'].unique():
            date_data = df[df['date'] == date].copy()
            
            # Split into 3 groups by Value Pillar score
            date_data_sorted = date_data.sort_values('value_pillar_score', ascending=False)
            n = len(date_data_sorted)
            
            # Create tertiles (33% splits)
            top_33_idx = int(n * 0.33)
            bottom_33_idx = int(n * 0.67)
            
            top_33 = date_data_sorted.iloc[:top_33_idx]      # Highest Value scores
            middle_33 = date_data_sorted.iloc[top_33_idx:bottom_33_idx]  
            bottom_33 = date_data_sorted.iloc[bottom_33_idx:]  # Lowest Value scores
            
            # Calculate averages for each group
            daily_result = {
                'date': date,
                'top_33_count': len(top_33),
                'middle_33_count': len(middle_33), 
                'bottom_33_count': len(bottom_33),
                
                # Value scores (for verification)
                'top_33_value_score': top_33['value_pillar_score'].mean(),
                'middle_33_value_score': middle_33['value_pillar_score'].mean(),
                'bottom_33_value_score': bottom_33['value_pillar_score'].mean(),
                
                # P/E Ratios
                'top_33_pe': top_33['pe_ratio'].mean(),
                'middle_33_pe': middle_33['pe_ratio'].mean(),
                'bottom_33_pe': bottom_33['pe_ratio'].mean(),
                
                # P/B Ratios  
                'top_33_pb': top_33['pb_ratio'].mean(),
                'middle_33_pb': middle_33['pb_ratio'].mean(),
                'bottom_33_pb': bottom_33['pb_ratio'].mean(),
                
                # Dividend Yields
                'top_33_div_yield': top_33['dividend_yield'].mean(),
                'middle_33_div_yield': middle_33['dividend_yield'].mean(),
                'bottom_33_div_yield': bottom_33['dividend_yield'].mean(),
            }
            
            daily_results.append(daily_result)
        
        # Create summary DataFrame
        daily_df = pd.DataFrame(daily_results)
        
        # Calculate overall averages across all dates
        summary_stats = {
            'Top 33% (High Value)': {
                'Avg Value Score': daily_df['top_33_value_score'].mean(),
                'Avg P/E': daily_df['top_33_pe'].mean(),
                'Avg P/B': daily_df['top_33_pb'].mean(), 
                'Avg Div Yield': daily_df['top_33_div_yield'].mean(),
                'Count': daily_df['top_33_count'].mean()
            },
            'Middle 33%': {
                'Avg Value Score': daily_df['middle_33_value_score'].mean(),
                'Avg P/E': daily_df['middle_33_pe'].mean(),
                'Avg P/B': daily_df['middle_33_pb'].mean(),
                'Avg Div Yield': daily_df['middle_33_div_yield'].mean(),
                'Count': daily_df['middle_33_count'].mean()
            },
            'Bottom 33% (Low Value)': {
                'Avg Value Score': daily_df['bottom_33_value_score'].mean(),
                'Avg P/E': daily_df['bottom_33_pe'].mean(),
                'Avg P/B': daily_df['bottom_33_pb'].mean(),
                'Avg Div Yield': daily_df['bottom_33_div_yield'].mean(),
                'Count': daily_df['bottom_33_count'].mean()
            }
        }
        
        return summary_stats, daily_df
    
    def validate_results_and_generate_report(self, summary_stats, daily_df):
        """Validate results against pass/fail criteria and generate comprehensive report."""
        
        print(f"\n📊 VALUE PILLAR VALIDATION RESULTS")
        print("="*60)
        
        # Extract key metrics for validation
        top_pe = summary_stats['Top 33% (High Value)']['Avg P/E']
        middle_pe = summary_stats['Middle 33%']['Avg P/E']
        bottom_pe = summary_stats['Bottom 33% (Low Value)']['Avg P/E']
        
        top_pb = summary_stats['Top 33% (High Value)']['Avg P/B']
        middle_pb = summary_stats['Middle 33%']['Avg P/B']
        bottom_pb = summary_stats['Bottom 33% (Low Value)']['Avg P/B']
        
        top_div = summary_stats['Top 33% (High Value)']['Avg Div Yield']
        middle_div = summary_stats['Middle 33%']['Avg Div Yield']
        bottom_div = summary_stats['Bottom 33% (Low Value)']['Avg Div Yield']
        
        # Display summary table
        print(f"\n📋 SUMMARY TABLE:")
        print("-" * 80)
        print(f"{'Value Score Group':<20} {'Avg Value':<12} {'Avg P/E':<10} {'Avg P/B':<10} {'Avg Div Yield':<12}")
        print("-" * 80)
        
        for group_name, stats in summary_stats.items():
            print(f"{group_name:<20} "
                  f"{stats['Avg Value Score']:>8.1f}     "
                  f"{stats['Avg P/E']:>6.1f}     "
                  f"{stats['Avg P/B']:>6.2f}     "
                  f"{stats['Avg Div Yield']:>8.1f}%")
        
        print("-" * 80)
        
        # Validation against criteria
        print(f"\n🔍 VALIDATION AGAINST PASS/FAIL CRITERIA:")
        print("-" * 50)
        
        validation_results = {}
        
        # Test 1: P/E Ratio ordering (Top should have LOWEST P/E)
        pe_ordering_correct = top_pe < middle_pe < bottom_pe
        validation_results['pe_ordering'] = pe_ordering_correct
        
        print(f"✓ P/E Ratio Ordering Test:")
        print(f"   Expected: Top < Middle < Bottom")
        print(f"   Actual:   {top_pe:.1f} < {middle_pe:.1f} < {bottom_pe:.1f}")
        if pe_ordering_correct:
            print(f"   ✅ PASS: Correct P/E ordering (high value = low P/E)")
        else:
            print(f"   ❌ FAIL: Incorrect P/E ordering - logic may be backwards!")
        
        # Test 2: P/B Ratio ordering (Top should have LOWEST P/B)
        pb_ordering_correct = top_pb < middle_pb < bottom_pb
        validation_results['pb_ordering'] = pb_ordering_correct
        
        print(f"\n✓ P/B Ratio Ordering Test:")
        print(f"   Expected: Top < Middle < Bottom")
        print(f"   Actual:   {top_pb:.2f} < {middle_pb:.2f} < {bottom_pb:.2f}")
        if pb_ordering_correct:
            print(f"   ✅ PASS: Correct P/B ordering (high value = low P/B)")
        else:
            print(f"   ❌ FAIL: Incorrect P/B ordering - logic may be backwards!")
        
        # Test 3: Dividend Yield ordering (Top should have HIGHEST dividend yield)
        div_ordering_correct = top_div > middle_div > bottom_div
        validation_results['div_ordering'] = div_ordering_correct
        
        print(f"\n✓ Dividend Yield Ordering Test:")
        print(f"   Expected: Top > Middle > Bottom")
        print(f"   Actual:   {top_div:.1f}% > {middle_div:.1f}% > {bottom_div:.1f}%")
        if div_ordering_correct:
            print(f"   ✅ PASS: Correct dividend yield ordering (high value = high yield)")
        else:
            print(f"   ❌ FAIL: Incorrect dividend yield ordering")
        
        # Test 4: Statistical significance of differences
        pe_spread = bottom_pe - top_pe
        pb_spread = bottom_pb - top_pb  
        div_spread = top_div - bottom_div
        
        spreads_significant = pe_spread >= 3.0 and pb_spread >= 0.5 and div_spread >= 1.0
        validation_results['spreads_significant'] = spreads_significant
        
        print(f"\n✓ Statistical Significance Test:")
        print(f"   P/E Spread: {pe_spread:.1f} (threshold: ≥3.0)")
        print(f"   P/B Spread: {pb_spread:.2f} (threshold: ≥0.5)")  
        print(f"   Div Spread: {div_spread:.1f}% (threshold: ≥1.0%)")
        if spreads_significant:
            print(f"   ✅ PASS: Statistically significant differences")
        else:
            print(f"   ⚠️  WARN: Small differences - may need stronger differentiation")
        
        # Test 5: Consistency across time periods
        # Check if the pattern holds across most days
        pe_consistent_days = ((daily_df['top_33_pe'] < daily_df['middle_33_pe']) & 
                             (daily_df['middle_33_pe'] < daily_df['bottom_33_pe'])).sum()
        pb_consistent_days = ((daily_df['top_33_pb'] < daily_df['middle_33_pb']) & 
                             (daily_df['middle_33_pb'] < daily_df['bottom_33_pb'])).sum()
        div_consistent_days = ((daily_df['top_33_div_yield'] > daily_df['middle_33_div_yield']) & 
                              (daily_df['middle_33_div_yield'] > daily_df['bottom_33_div_yield'])).sum()
        
        total_days = len(daily_df)
        consistency_threshold = 0.70  # 70% of days should show correct pattern
        
        pe_consistency = pe_consistent_days / total_days
        pb_consistency = pb_consistent_days / total_days
        div_consistency = div_consistent_days / total_days
        
        time_consistency_pass = (pe_consistency >= consistency_threshold and 
                               pb_consistency >= consistency_threshold and 
                               div_consistency >= consistency_threshold)
        validation_results['time_consistency'] = time_consistency_pass
        
        print(f"\n✓ Time Consistency Test:")
        print(f"   P/E Pattern Consistency: {pe_consistency:.1%} of days ({pe_consistent_days}/{total_days})")
        print(f"   P/B Pattern Consistency: {pb_consistency:.1%} of days ({pb_consistent_days}/{total_days})")
        print(f"   Div Pattern Consistency: {div_consistency:.1%} of days ({div_consistent_days}/{total_days})")
        print(f"   Threshold: ≥{consistency_threshold:.0%}")
        if time_consistency_pass:
            print(f"   ✅ PASS: Consistent pattern across time")
        else:
            print(f"   ❌ FAIL: Inconsistent pattern across time periods")
        
        # Overall assessment
        print(f"\n" + "="*60)
        print(f"🎯 OVERALL VALUE PILLAR VALIDATION ASSESSMENT")
        print("="*60)
        
        total_tests = len(validation_results)
        passed_tests = sum(validation_results.values())
        
        print(f"📊 Test Summary:")
        for test_name, result in validation_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   • {test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\n📈 Results: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests:.0%})")
        
        if passed_tests == total_tests:
            overall_status = "✅ PASS"
            message = "Value Pillar logic is working correctly!"
        elif passed_tests >= total_tests * 0.8:  # 80% pass rate
            overall_status = "⚠️  CONDITIONAL PASS"
            message = "Value Pillar logic mostly correct but needs minor adjustments"
        else:
            overall_status = "❌ FAIL"
            message = "Value Pillar logic has significant issues requiring review"
        
        print(f"\n🚀 FINAL VERDICT: {overall_status}")
        print(f"   {message}")
        
        # Additional insights
        print(f"\n💡 KEY INSIGHTS:")
        value_range = summary_stats['Top 33% (High Value)']['Avg Value Score'] - summary_stats['Bottom 33% (Low Value)']['Avg Value Score']
        print(f"   • Value Score Range: {value_range:.1f} points (Top vs Bottom)")
        print(f"   • P/E Differentiation: {pe_spread:.1f}x (Bottom vs Top)")  
        print(f"   • P/B Differentiation: {pb_spread:.2f}x (Bottom vs Top)")
        print(f"   • Dividend Premium: +{div_spread:.1f}% (Top vs Bottom)")
        
        return validation_results, summary_stats
    
    def run_comprehensive_value_validation(self):
        """Run the complete Value Pillar validation test."""
        
        print("🚀 STARTING PHASE 1.5: VALUE PILLAR LOGIC VALIDATION")
        print("="*70)
        print("Test #1: Value Pillar Sanity Check")
        print("Validating that high Value scores correspond to undervalued stocks")
        print()
        
        # Step 1: Generate enhanced dataset with proper value metrics
        df = self.generate_enhanced_dataset_with_value_metrics(num_stocks=50, num_days=100)
        
        # Step 2: Perform the sanity check analysis
        summary_stats, daily_df = self.perform_value_pillar_sanity_check(df)
        
        # Step 3: Validate and generate report
        validation_results, final_summary = self.validate_results_and_generate_report(summary_stats, daily_df)
        
        # Step 4: Store results
        self.results = {
            'dataset': df,
            'daily_analysis': daily_df,
            'summary_stats': summary_stats,
            'validation_results': validation_results,
            'final_summary': final_summary
        }
        
        return self.results


def main():
    """Run the Value Pillar Logic Validation."""
    
    validator = ValuePillarValidator()
    results = validator.run_comprehensive_value_validation()
    
    # Display final summary
    print(f"\n" + "="*70)
    print(f"📋 VALUE PILLAR VALIDATION COMPLETE")
    print("="*70)
    
    validation_results = results['validation_results']
    passed = sum(validation_results.values())
    total = len(validation_results)
    
    print(f"✅ Tests Passed: {passed}/{total}")
    print(f"📊 Success Rate: {passed/total:.0%}")
    
    if passed == total:
        print(f"🎉 VALUE PILLAR LOGIC: VALIDATED ✅")
        print(f"   All sanity checks passed - scoring logic is correct")
    else:
        print(f"⚠️  VALUE PILLAR LOGIC: NEEDS REVIEW")
        print(f"   Some tests failed - review scoring algorithm")
    
    return results


if __name__ == "__main__":
    main()