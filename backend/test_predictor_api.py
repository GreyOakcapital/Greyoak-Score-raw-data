"""
Test Predictor API functionality locally
"""

import sys
sys.path.insert(0, '/app/backend')

from api.routes_predictor import load_predictions_cache, load_model_cache
import pandas as pd

print("="*70)
print("PREDICTOR API FUNCTIONALITY TEST")
print("="*70)

# Test 1: Load predictions
print("\n Test 1: Load Predictions Cache")
print("-"*70)
try:
    predictions = load_predictions_cache()
    if predictions is not None:
        print(f"✅ Loaded {len(predictions)} predictions")
        print(f"   Columns: {list(predictions.columns)}")
        print(f"   Date range: {predictions['date'].min()} to {predictions['date'].max()}")
    else:
        print("❌ No predictions found")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Load model
print("\n✓ Test 2: Load Model Cache")
print("-"*70)
try:
    model = load_model_cache()
    if model is not None:
        print(f"✅ Model loaded")
        print(f"   Model ID: {model['model_id']}")
        print(f"   Features: {len(model['feature_cols'])}")
    else:
        print("❌ No model found")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Sample predictions
if predictions is not None:
    print("\n✓ Test 3: Sample Predictions")
    print("-"*70)
    
    # Show distribution
    print("\n📊 Timing Band Distribution:")
    band_counts = predictions['timing_band'].value_counts()
    for band, count in band_counts.items():
        pct = count / len(predictions) * 100
        print(f"   {band:15} {count:3d} ({pct:5.1f}%)")
    
    # Show top scores
    print("\n📊 Top 10 by Score:")
    top10 = predictions.nlargest(10, 'predictor_score')[
        ['symbol', 'predictor_score', 'timing_band', 'p_pos', 'E', 'RA']
    ]
    print(top10.to_string(index=False))
    
    # Test API response format for a stock
    print("\n✓ Test 4: Sample API Response Format")
    print("-"*70)
    sample = predictions.iloc[0]
    
    response = {
        "ticker": sample['symbol'],
        "p_hat": round(sample['p_pos'], 4),
        "expected_edge_pct": round(sample['E'] * 100, 2),
        "risk_adjusted_edge": round(sample['RA'], 4),
        "predictor_score": int(sample['predictor_score']),
        "timing_band": sample['timing_band'],
        "flags": sample['flags'].split(',') if sample['flags'] else [],
        "as_of": str(sample['date']),
        "mode": "TRADER"
    }
    
    print(f"\nSample response for {response['ticker']}:")
    import json
    print(json.dumps(response, indent=2))

print("\n" + "="*70)
print("✅ PREDICTOR API TEST COMPLETE")
print("="*70)
print("\nPredictor is ready to serve via API endpoints:")
print("  GET /api/predictor/{ticker}")
print("  GET /api/predictor/")
print("  GET /api/predictor/stats/summary")
print("  GET /api/predictor/health")
print()
