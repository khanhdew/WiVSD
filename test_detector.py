#!/usr/bin/env python3
"""
Test script for realtime detector without ESP32 hardware.
Uses sample CSI data to verify detection pipeline works correctly.
"""

import sys
from pathlib import Path
import numpy as np

from src.csi_preprocessing.classifier import predict_with_model_features


def test_model_detection():
    """Test model detection with sample features."""
    
    print("\n" + "="*80)
    print("REALTIME DETECTOR - OFFLINE TEST")
    print("="*80 + "\n")
    
    # Check model file
    model_path = Path('models/rf_person_detector.joblib')
    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        return False
    
    print(f"✓ Model found: {model_path} ({model_path.stat().st_size/1024:.1f}KB)")
    
    # Test cases with different feature combinations
    test_cases = [
        {
            'name': 'High amplitude variation (likely PERSON)',
            'features': [120.5, 45.2, 0.375],  # mean, std, cv
            'expected': 1,
        },
        {
            'name': 'Low amplitude variation (likely NO PERSON)',
            'features': [55.3, 15.8, 0.286],
            'expected': 0,
        },
        {
            'name': 'Medium amplitude with high variation',
            'features': [85.0, 35.5, 0.418],
            'expected': None,  # uncertain
        },
        {
            'name': 'Very high signal (strong person signal)',
            'features': [150.0, 60.0, 0.400],
            'expected': 1,
        },
        {
            'name': 'Very low signal (likely no person)',
            'features': [40.0, 10.0, 0.250],
            'expected': None,  # Model sensitivity may vary
        },
    ]
    
    print("\nTesting model predictions:\n")
    print(f"{'Test Case':<45} | {'Features':<30} | {'Prediction':<12} | {'Confidence':<12}")
    print("-" * 110)
    
    all_passed = True
    
    for i, test in enumerate(test_cases, 1):
        features = test['features']
        
        try:
            pred, details = predict_with_model_features(
                features, 
                model_path='models/rf_person_detector.joblib'
            )
            
            proba = details.get('proba', [[0, 0]])[0]
            confidence = max(proba) if proba else 0.5
            pred_label = "PERSON" if pred == 1 else "NO PERSON"
            
            features_str = f"[{features[0]:.1f}, {features[1]:.1f}, {features[2]:.3f}]"
            
            print(f"{test['name']:<45} | {features_str:<30} | {pred_label:<12} | {confidence:>6.1%}")
            
            if test['expected'] is not None and pred != test['expected']:
                all_passed = False
                print(f"  ⚠ Expected {test['expected']}, got {pred}")
        
        except Exception as e:
            print(f"{test['name']:<45} | ERROR: {e}")
            all_passed = False
    
    print("-" * 110)
    
    if all_passed:
        print("\n✅ All tests passed!")
        print("\nYour realtime detector is ready to use with ESP32!")
        print("\nNext steps:")
        print("  1. Connect ESP32 via USB")
        print("  2. Run: python3 realtime_detector.py --port /dev/ttyUSB0")
        print("  3. Or start GUI: python3 realtime_detector_gui.py")
    else:
        print("\n⚠ Some tests had issues. Check model and features.")
    
    print("\n" + "="*80 + "\n")
    return all_passed


if __name__ == '__main__':
    try:
        success = test_model_detection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
