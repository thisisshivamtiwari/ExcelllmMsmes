"""
Test Data Calculator with Gemini-powered column extraction
"""

import sys
import json
import logging
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

from tools.data_calculator import DataCalculator

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_composite_column_extraction():
    """Test extraction of Line from Line_Machine composite column"""
    
    print("\n" + "="*80)
    print("TEST 1: Composite Column Extraction (Line_Machine → Line)")
    print("="*80)
    
    # Sample data with Line_Machine composite column
    data = [
        {"Line_Machine": "Line-1/Machine-M1", "Product": "Widget-A", "Actual_Qty": 100},
        {"Line_Machine": "Line-2/Machine-M2", "Product": "Widget-B", "Actual_Qty": 150},
        {"Line_Machine": "Line-1/Machine-M1", "Product": "Widget-C", "Actual_Qty": 120},
        {"Line_Machine": "Line-3/Machine-M3", "Product": "Widget-A", "Actual_Qty": 130},
    ]
    
    calculator = DataCalculator()
    
    # Try to group by 'Line' even though only 'Line_Machine' exists
    result = calculator.calculate(
        data=data,
        operation='sum',
        column='Actual_Qty',
        group_by=['Line']  # This should be extracted from Line_Machine
    )
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
    
    if result.get('success'):
        print("✅ TEST PASSED: Successfully extracted Line from Line_Machine")
        return True
    else:
        print(f"❌ TEST FAILED: {result.get('error')}")
        return False


def test_different_composite_format():
    """Test with different composite column format"""
    
    print("\n" + "="*80)
    print("TEST 2: Different Composite Format (Station_Area → Station)")
    print("="*80)
    
    # Sample data with different composite format
    data = [
        {"Station_Area": "StationA-Area1", "Product": "Item-1", "Quantity": 50},
        {"Station_Area": "StationB-Area2", "Product": "Item-2", "Quantity": 75},
        {"Station_Area": "StationA-Area1", "Product": "Item-3", "Quantity": 60},
    ]
    
    calculator = DataCalculator()
    
    # Try to group by 'Station'
    result = calculator.calculate(
        data=data,
        operation='sum',
        column='Quantity',
        group_by=['Station']
    )
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
    
    if result.get('success'):
        print("✅ TEST PASSED: Successfully handled different format")
        return True
    else:
        print(f"❌ TEST FAILED: {result.get('error')}")
        return False


def test_no_extraction_needed():
    """Test when column exists directly (no extraction needed)"""
    
    print("\n" + "="*80)
    print("TEST 3: Direct Column Access (No Extraction Needed)")
    print("="*80)
    
    # Sample data with direct column
    data = [
        {"Line": "Line-1", "Product": "Widget-A", "Actual_Qty": 100},
        {"Line": "Line-2", "Product": "Widget-B", "Actual_Qty": 150},
        {"Line": "Line-1", "Product": "Widget-C", "Actual_Qty": 120},
    ]
    
    calculator = DataCalculator()
    
    result = calculator.calculate(
        data=data,
        operation='sum',
        column='Actual_Qty',
        group_by=['Line']
    )
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
    
    if result.get('success'):
        print("✅ TEST PASSED: Direct column access works")
        return True
    else:
        print(f"❌ TEST FAILED: {result.get('error')}")
        return False


def test_calculate_percentage():
    """Test percentage calculation with composite columns"""
    
    print("\n" + "="*80)
    print("TEST 4: Percentage Calculation with Composite Columns")
    print("="*80)
    
    # Sample data with Line_Machine
    data = [
        {"Line_Machine": "Line-1/Machine-M1", "Target_Qty": 100, "Actual_Qty": 95},
        {"Line_Machine": "Line-2/Machine-M2", "Target_Qty": 150, "Actual_Qty": 145},
        {"Line_Machine": "Line-1/Machine-M1", "Target_Qty": 120, "Actual_Qty": 110},
    ]
    
    calculator = DataCalculator()
    
    result = calculator.calculate_ratio(
        data=data,
        numerator_column='Actual_Qty',
        denominator_column='Target_Qty',
        group_by=['Line']  # Should extract from Line_Machine
    )
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
    
    if result.get('success'):
        print("✅ TEST PASSED: Percentage calculation with extraction works")
        return True
    else:
        print(f"❌ TEST FAILED: {result.get('error')}")
        return False


def test_invalid_extraction():
    """Test when column cannot be extracted"""
    
    print("\n" + "="*80)
    print("TEST 5: Invalid Extraction (Should Fail Gracefully)")
    print("="*80)
    
    # Sample data without any Line-related column
    data = [
        {"Machine": "M1", "Product": "Widget-A", "Quantity": 100},
        {"Machine": "M2", "Product": "Widget-B", "Quantity": 150},
    ]
    
    calculator = DataCalculator()
    
    result = calculator.calculate(
        data=data,
        operation='sum',
        column='Quantity',
        group_by=['Line']  # This should fail gracefully
    )
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
    
    if not result.get('success'):
        print("✅ TEST PASSED: Failed gracefully with clear error message")
        return True
    else:
        print("❌ TEST FAILED: Should have failed but didn't")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("🚀 DATA CALCULATOR GEMINI INTEGRATION TESTS")
    print("="*80)
    
    tests = [
        ("Composite Column Extraction", test_composite_column_extraction),
        ("Different Format Handling", test_different_composite_format),
        ("Direct Column Access", test_no_extraction_needed),
        ("Percentage with Extraction", test_calculate_percentage),
        ("Invalid Extraction (Graceful Fail)", test_invalid_extraction),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n❌ TEST ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for test_name, passed_status in results:
        status = "✅ PASSED" if passed_status else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*80)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

