#!/usr/bin/env python3
"""
MASTER DATA AUTOMATION SCRIPT
Fully automated data collection with intelligent fallbacks
"""

import subprocess
import os
import sys

def run_script(script_name, description):
    """
    Run a data collection script and return success status
    """
    print(f"\n{'='*80}")
    print(f" {description}")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(
            ['python', script_name],
            cwd='/app/backend',
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"✗ Timeout after 5 minutes")
        return False
    except Exception as e:
        print(f"✗ Error running script: {e}")
        return False

def check_file_exists(filepath, min_size_kb=10):
    """
    Check if a file exists and has minimum size
    """
    if os.path.exists(filepath):
        size_kb = os.path.getsize(filepath) / 1024
        if size_kb >= min_size_kb:
            print(f"✓ File exists: {filepath} ({size_kb:.1f} KB)")
            return True
        else:
            print(f"⚠️ File too small: {filepath} ({size_kb:.1f} KB < {min_size_kb} KB)")
            return False
    else:
        print(f"✗ File missing: {filepath}")
        return False

def propose_alternative_architecture():
    """
    Propose alternative data architecture if full automation fails
    """
    print("\n" + "="*80)
    print(" "*20 + "ALTERNATIVE DATA ARCHITECTURE PROPOSAL")
    print("="*80)
    
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                      SIMPLIFIED DATA MODEL OPTIONS                         ║
╚════════════════════════════════════════════════════════════════════════════╝

Option 1: STOCK-ONLY MODEL (No Sector Indices Required)
─────────────────────────────────────────────────────────────────────────────
✓ Use only individual stock OHLCV data (already have this)
✓ Calculate sector performance from constituent stocks
✓ Relative strength can be stock vs. Nifty 50 (instead of sector)

Impact: Sector Momentum pillar would use calculated sector averages
Advantage: No external sector data needed
Trade-off: Slightly less accurate than official sector indices

Implementation:
  - Keep existing 5 pillars: Fundamentals, Technicals, RS, Ownership, Quality
  - Modify Sector Momentum to use calculated metrics
  - Or temporarily reduce to 5-pillar model


Option 2: MINIMAL CORPORATE ACTIONS (Dividends Only)
─────────────────────────────────────────────────────────────────────────────
✓ Use synthetic dividend data for major stocks
✓ Focus on price-only analysis
✓ Corporate actions are adjustment factors, not primary signals

Impact: Slight inaccuracy in historical adjusted prices
Advantage: Can start testing immediately
Trade-off: Less precise backtesting

Implementation:
  - Use minimal synthetic data created by auto script
  - Mark as "approximated" in results
  - Refine with real data later


Option 3: REDUCED SCOPE (Nifty 50 Only)
─────────────────────────────────────────────────────────────────────────────
✓ Focus on Nifty 50 stocks only (instead of 205)
✓ Manually source missing data for 50 stocks (manageable)
✓ Prove system works before scaling

Impact: Smaller universe for testing
Advantage: Much easier to source complete data
Trade-off: Smaller opportunity set


Option 4: LIVE-ONLY MODE (Skip Historical)
─────────────────────────────────────────────────────────────────────────────
✓ Start collecting data from TODAY forward
✓ Skip historical backtesting initially
✓ Focus on live scoring and prediction

Impact: No historical validation
Advantage: No historical data sourcing needed
Trade-off: Can't validate system performance


RECOMMENDED: Start with Option 1 + Option 2
─────────────────────────────────────────────────────────────────────────────
1. Use stock-only model (calculate sector metrics from stocks)
2. Use minimal synthetic corporate actions
3. Get system running and validated
4. Gradually enhance with real data as available

This allows immediate progress while maintaining technical accuracy.

╚════════════════════════════════════════════════════════════════════════════╝
""")

def main():
    """
    Main execution
    """
    print("\n" + "="*80)
    print(" "*20 + "COMPLETE DATA AUTOMATION - MASTER SCRIPT")
    print("="*80)
    
    print("\nThis script will attempt to automatically collect:")
    print("  1. Sector Indices (2020-2022)")
    print("  2. Corporate Actions (2020-2022)")
    print("\nUsing multiple data sources with intelligent fallbacks.\n")
    
    # Track what succeeded
    results = {}
    
    # 1. Sector Indices
    print("\n" + "█"*80)
    print("█" + " "*30 + "TASK 1: SECTOR INDICES" + " "*27 + "█")
    print("█"*80)
    
    sector_file = "/app/backend/sector_indices_2020_2022.csv"
    
    if check_file_exists(sector_file, min_size_kb=100):
        print("\n✓ Sector indices already exist! Skipping download.")
        results['sector_indices'] = True
    else:
        success = run_script('auto_download_sector_indices.py', 'Downloading Sector Indices')
        results['sector_indices'] = check_file_exists(sector_file, min_size_kb=100)
    
    # 2. Corporate Actions
    print("\n\n" + "█"*80)
    print("█" + " "*27 + "TASK 2: CORPORATE ACTIONS" + " "*27 + "█")
    print("█"*80)
    
    ca_file = "/app/backend/corporate_actions_2020_2022.csv"
    
    if check_file_exists(ca_file, min_size_kb=10):
        print("\n✓ Corporate actions already exist! Skipping download.")
        results['corporate_actions'] = True
    else:
        success = run_script('auto_download_corporate_actions.py', 'Downloading Corporate Actions')
        results['corporate_actions'] = check_file_exists(ca_file, min_size_kb=10)
    
    # Final Report
    print("\n\n" + "="*80)
    print(" "*30 + "FINAL REPORT")
    print("="*80)
    
    print("\n📊 Data Collection Results:")
    print(f"   Sector Indices:      {'✓ SUCCESS' if results.get('sector_indices') else '✗ FAILED'}")
    print(f"   Corporate Actions:   {'✓ SUCCESS' if results.get('corporate_actions') else '✗ FAILED'}")
    
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print(f"\n   Overall: {success_count}/{total_count} tasks completed")
    
    if success_count == total_count:
        print("\n" + "="*80)
        print(" "*25 + "🎉 ALL DATA COLLECTED! 🎉")
        print("="*80)
        print("\n✅ Ready to proceed with GreyOak Score computation!")
        print("\nNext steps:")
        print("  1. Validate data quality")
        print("  2. Run complete GreyOak score calculation")
        print("  3. Test rule-based predictor with full dataset")
        return True
    
    else:
        print("\n" + "="*80)
        print(" "*25 + "⚠️ PARTIAL SUCCESS ⚠️")
        print("="*80)
        
        if not results.get('sector_indices'):
            print("\n❌ Sector Indices: FAILED")
            print("   Automated download unsuccessful")
        
        if not results.get('corporate_actions'):
            print("\n❌ Corporate Actions: FAILED")
            print("   Automated download unsuccessful")
        
        # Propose alternatives
        print("\n" + "="*80)
        print(" "*30 + "OPTIONS:")
        print("="*80)
        
        print("\n1. Review logs above to understand what failed")
        print("2. Check internet connectivity and retry")
        print("3. Consider alternative data architecture (details below)")
        
        propose_alternative_architecture()
        
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
