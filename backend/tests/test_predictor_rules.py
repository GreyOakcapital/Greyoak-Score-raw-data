"""
GreyOak Predictor - Unit Tests
Test critical logic from specification
"""

import numpy as np
import pandas as pd
import sys
sys.path.insert(0, '/app/backend')

from predictor.labels import triple_barrier
from predictor.infer import apply_gates, compute_predictor_score, adjust_cuts_for_coverage


def test_same_bar_double_touch_is_neutral():
    """Test that same-bar double touch results in neutral label"""
    print("Test: Same-bar double touch → neutral")
    
    close = np.array([100.0])
    high = np.array([110.0])   # Hits up barrier
    low = np.array([90.0])     # Hits down barrier
    U = np.array([0.08])       # 8% up
    L = np.array([0.08])       # 8% down
    T = 1
    
    labels, hit_up, hit_dn = triple_barrier(close, high, low, U, L, T)
    
    assert labels[0] == 0, f"Expected 0, got {labels[0]}"
    assert hit_up[0] == True, "Should mark up as hit"
    assert hit_dn[0] == True, "Should mark down as hit"
    print("  ✅ PASS\n")


def test_gate_fail_caps_score():
    """Test that gate failure caps score at 49"""
    print("Test: Gate fail → score capped at 49")
    
    base_score = np.array([72, 60, 85])
    E = np.array([0.010, 0.020, 0.018])
    RA = np.array([0.30, 0.50, 0.48])
    E_min = 0.015
    RA_min = 0.45
    flags = [[], [], []]
    
    gated_score, updated_flags = apply_gates(base_score, E, RA, E_min, RA_min, flags)
    
    # First should fail (E too low, RA too low)
    assert gated_score[0] <= 49, f"Score should be capped, got {gated_score[0]}"
    assert 'GateFail' in updated_flags[0], "Should have GateFail flag"
    
    # Second should pass
    assert gated_score[1] >= 60, f"Score should not be capped, got {gated_score[1]}"
    assert 'GateFail' not in updated_flags[1], "Should not have GateFail flag"
    
    print("  ✅ PASS\n")


def test_xsctn_fallback_when_small_n():
    """Test cross-sectional fallback for small sample sizes"""
    print("Test: Small N → XSctnFallback flag")
    
    # Small sample
    p_pos_small = np.array([0.6, 0.4, 0.5])
    RA_small = np.array([0.3, 0.1, 0.2])
    
    score_small, flags_small = compute_predictor_score(
        p_pos_small, RA_small, method='cross_sectional'
    )
    
    assert any('XSctnFallback' in f for f in flags_small), "Should use fallback for small N"
    
    # Large sample
    p_pos_large = np.random.rand(20) * 0.5 + 0.25
    RA_large = np.random.rand(20) * 0.5
    
    score_large, flags_large = compute_predictor_score(
        p_pos_large, RA_large, method='cross_sectional'
    )
    
    assert not any('XSctnFallback' in f for f in flags_large), "Should not use fallback for large N"
    
    print("  ✅ PASS\n")


def test_coverage_guard_raises_cuts():
    """Test that high coverage raises thresholds"""
    print("Test: High coverage → raised thresholds")
    
    # Create scenario with high SB coverage
    timing_bands = np.array(['TimingSB'] * 20 + ['TimingBuy'] * 80)
    
    thresholds = {
        'p_pos_min_sb': 0.90,
        'p_pos_min_buy': 0.75,
        'p_neg_min_avoid': 0.45
    }
    
    config = {
        'coverage_caps': {
            'strong_buy_max': 0.12,
            'buy_max': 0.35
        }
    }
    
    sb_cut, buy_cut = adjust_cuts_for_coverage(timing_bands, thresholds, config)
    
    # SB coverage is 20% (> 12%), should raise
    assert sb_cut >= 0.92, f"SB cut should be raised, got {sb_cut}"
    
    # Buy+SB coverage is 100% (> 35%), should raise
    assert buy_cut >= 0.77, f"Buy cut should be raised, got {buy_cut}"
    
    print("  ✅ PASS\n")


def test_timing_band_logic():
    """Test timing band assignment logic"""
    print("Test: Timing band assignment")
    
    from predictor.infer import determine_timing_band
    
    p_pos = np.array([0.95, 0.80, 0.70, 0.40, 0.30])
    p_neg = np.array([0.10, 0.15, 0.20, 0.50, 0.60])
    gate_pass = np.array([True, True, True, True, True])
    
    thresholds = {
        'p_pos_min_sb': 0.90,
        'p_pos_min_buy': 0.75,
        'p_neg_min_avoid': 0.45
    }
    
    bands = determine_timing_band(p_pos, p_neg, gate_pass, thresholds)
    
    assert bands[0] == 'TimingSB', f"Should be SB, got {bands[0]}"
    assert bands[1] == 'TimingBuy', f"Should be Buy, got {bands[1]}"
    assert bands[2] == 'TimingHold', f"Should be Hold, got {bands[2]}"
    assert bands[3] == 'TimingAvoid', f"Should be Avoid, got {bands[3]}"
    assert bands[4] == 'TimingAvoid', f"Should be Avoid, got {bands[4]}"
    
    print("  ✅ PASS\n")


def run_all_tests():
    """Run all test cases"""
    print("="*70)
    print("GREYOAK PREDICTOR - UNIT TESTS")
    print("="*70 + "\n")
    
    try:
        test_same_bar_double_touch_is_neutral()
        test_gate_fail_caps_score()
        test_xsctn_fallback_when_small_n()
        test_coverage_guard_raises_cuts()
        test_timing_band_logic()
        
        print("="*70)
        print("✅ ALL TESTS PASSED")
        print("="*70)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("="*70)
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("="*70)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
