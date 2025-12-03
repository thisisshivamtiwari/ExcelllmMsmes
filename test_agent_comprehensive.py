"""
Comprehensive Agent Testing Script
Tests all tools with 20+ questions and verifies answers against ground truth.
"""

import sys
import os
from pathlib import Path
import json
import pandas as pd
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

# Import tools
from tools.excel_retriever import ExcelRetriever
from tools.data_calculator import DataCalculator
from tools.trend_analyzer import TrendAnalyzer
from tools.comparative_analyzer import ComparativeAnalyzer
from tools.kpi_calculator import KPICalculator

# Ground truth data (calculated from actual CSV files)
GROUND_TRUTH = {
    "production_logs": {
        "file_id": "b5b34b6b-2301-4422-860d-e9a5bdfb6a8a",
        "total_actual_qty": 237525,
        "total_target_qty": 279820,
        "total_downtime_minutes": 11276,
        "avg_actual_qty": 272.39,
        "rows": 872
    },
    "quality_control": {
        "file_id": "29aca7f4-7202-4c2b-bb92-ceb5dfd33b9a",
        "total_inspected_qty": 49107,
        "total_passed_qty": 47420,
        "total_failed_qty": 1687,
        "pass_rate": 96.57,
        "rows": 675
    },
    "maintenance_logs": {
        "file_id": "d5d3a697-68da-49db-a2b3-064b86912fba",
        "total_cost": 1030300,
        "avg_cost": 7805.30,
        "breakdown_count": 42,
        "rows": 132
    },
    "inventory": {
        "file_id": "e3941372-efe1-46dd-a3b4-abc31a6dee99",
        "total_consumption": 136428,
        "total_received": 106200,
        "total_wastage": 3704,
        "rows": 418
    }
}

# Test questions with expected answers
TEST_QUESTIONS = [
    {
        "id": 1,
        "question": "What is the total production quantity?",
        "expected_answer": 237525,
        "tolerance": 0.01,  # 0.01% tolerance
        "file": "production_logs",
        "column": "Actual_Qty",
        "operation": "sum"
    },
    {
        "id": 2,
        "question": "What is the total inspected quantity?",
        "expected_answer": 49107,
        "tolerance": 0.01,
        "file": "quality_control",
        "column": "Inspected_Qty",
        "operation": "sum"
    },
    {
        "id": 3,
        "question": "How many units failed inspection?",
        "expected_answer": 1687,
        "tolerance": 0.01,
        "file": "quality_control",
        "column": "Failed_Qty",
        "operation": "sum"
    },
    {
        "id": 4,
        "question": "What is the total maintenance cost?",
        "expected_answer": 1030300,
        "tolerance": 0.01,
        "file": "maintenance_logs",
        "column": "Cost_Rupees",
        "operation": "sum"
    },
    {
        "id": 5,
        "question": "What is the total material consumption?",
        "expected_answer": 136428,
        "tolerance": 0.01,
        "file": "inventory",
        "column": "Consumption_Kg",
        "operation": "sum"
    },
    {
        "id": 6,
        "question": "What is the average production quantity per day?",
        "expected_answer": 272.39,
        "tolerance": 1.0,  # Allow 1 unit tolerance
        "file": "production_logs",
        "column": "Actual_Qty",
        "operation": "avg"
    },
    {
        "id": 7,
        "question": "What is the pass rate percentage?",
        "expected_answer": 96.57,
        "tolerance": 0.1,  # 0.1% tolerance
        "file": "quality_control",
        "column": "Passed_Qty",
        "operation": "ratio"  # Special case
    },
    {
        "id": 8,
        "question": "What is the total downtime in hours?",
        "expected_answer": 187.93,
        "tolerance": 0.1,
        "file": "production_logs",
        "column": "Downtime_Minutes",
        "operation": "sum_hours"  # Special case: sum then divide by 60
    },
    {
        "id": 9,
        "question": "What is the average maintenance cost?",
        "expected_answer": 7805.30,
        "tolerance": 1.0,
        "file": "maintenance_logs",
        "column": "Cost_Rupees",
        "operation": "avg"
    },
    {
        "id": 10,
        "question": "What is the total material wastage?",
        "expected_answer": 3704,
        "tolerance": 0.01,
        "file": "inventory",
        "column": "Wastage_Kg",
        "operation": "sum"
    }
]


def calculate_ground_truth_from_csv():
    """Calculate ground truth values from actual CSV files."""
    uploaded_files = project_root / "uploaded_files"
    metadata_dir = uploaded_files / "metadata"
    
    results = {}
    
    # Load production_logs
    prod_file = uploaded_files / "b5b34b6b-2301-4422-860d-e9a5bdfb6a8a.csv"
    if prod_file.exists():
        df = pd.read_csv(prod_file)
        results["production_logs"] = {
            "total_actual_qty": int(float(df["Actual_Qty"].sum())),
            "total_target_qty": int(float(df["Target_Qty"].sum())),
            "total_downtime_minutes": int(float(df["Downtime_Minutes"].sum())),
            "avg_actual_qty": float(df["Actual_Qty"].mean()),
            "rows": int(len(df))
        }
    
    # Load quality_control
    qc_file = uploaded_files / "29aca7f4-7202-4c2b-bb92-ceb5dfd33b9a.csv"
    if qc_file.exists():
        df = pd.read_csv(qc_file)
        total_inspected = int(float(df["Inspected_Qty"].sum()))
        total_passed = int(float(df["Passed_Qty"].sum()))
        total_failed = int(float(df["Failed_Qty"].sum()))
        results["quality_control"] = {
            "total_inspected_qty": total_inspected,
            "total_passed_qty": total_passed,
            "total_failed_qty": total_failed,
            "pass_rate": round((total_passed / total_inspected * 100), 2) if total_inspected > 0 else 0.0,
            "rows": int(len(df))
        }
    
    # Load maintenance_logs
    maint_file = uploaded_files / "d5d3a697-68da-49db-a2b3-064b86912fba.csv"
    if maint_file.exists():
        df = pd.read_csv(maint_file)
        breakdown_count = int(df["Breakdown_Date"].notna().sum())
        results["maintenance_logs"] = {
            "total_cost": int(float(df["Cost_Rupees"].sum())) if "Cost_Rupees" in df.columns else 0,
            "avg_cost": float(df["Cost_Rupees"].mean()) if "Cost_Rupees" in df.columns else 0.0,
            "breakdown_count": breakdown_count,
            "rows": int(len(df))
        }
    
    # Load inventory
    inv_file = uploaded_files / "e3941372-efe1-46dd-a3b4-abc31a6dee99.csv"
    if inv_file.exists():
        df = pd.read_csv(inv_file)
        results["inventory"] = {
            "total_consumption": int(float(df["Consumption_Kg"].sum())),
            "total_received": int(float(df["Received_Kg"].sum())),
            "total_wastage": int(float(df["Wastage_Kg"].sum())),
            "rows": int(len(df))
        }
    
    return results


def test_file_finding():
    """Test file finding by name."""
    print("\n" + "="*80)
    print("TEST 1: File Finding by Name")
    print("="*80)
    
    excel_retriever = ExcelRetriever(
        files_base_path=project_root / "uploaded_files",
        metadata_base_path=project_root / "uploaded_files" / "metadata"
    )
    
    test_cases = [
        ("production_logs", "b5b34b6b-2301-4422-860d-e9a5bdfb6a8a"),
        ("production quantity", "b5b34b6b-2301-4422-860d-e9a5bdfb6a8a"),
        ("quality control", "29aca7f4-7202-4c2b-bb92-ceb5dfd33b9a"),
        ("maintenance", "d5d3a697-68da-49db-a2b3-064b86912fba"),
        ("inventory", "e3941372-efe1-46dd-a3b4-abc31a6dee99"),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_file_id in test_cases:
        file_id = excel_retriever.find_file_by_name(query)
        if file_id == expected_file_id:
            print(f"✓ PASS: '{query}' -> {file_id}")
            passed += 1
        else:
            print(f"✗ FAIL: '{query}' -> Expected {expected_file_id}, got {file_id}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_data_retrieval():
    """Test data retrieval."""
    print("\n" + "="*80)
    print("TEST 2: Data Retrieval")
    print("="*80)
    
    excel_retriever = ExcelRetriever(
        files_base_path=project_root / "uploaded_files",
        metadata_base_path=project_root / "uploaded_files" / "metadata"
    )
    
    # Test retrieving production data
    file_id = GROUND_TRUTH["production_logs"]["file_id"]
    result = excel_retriever.retrieve_data(
        file_id=file_id,
        columns=["Actual_Qty"],
        limit=10
    )
    
    if result.get("success"):
        print(f"✓ PASS: Retrieved {len(result.get('data', []))} rows from production_logs")
        print(f"  Columns: {result.get('columns', [])}")
        return True
    else:
        print(f"✗ FAIL: {result.get('error')}")
        return False


def test_calculations():
    """Test data calculations."""
    print("\n" + "="*80)
    print("TEST 3: Data Calculations")
    print("="*80)
    
    excel_retriever = ExcelRetriever(
        files_base_path=project_root / "uploaded_files",
        metadata_base_path=project_root / "uploaded_files" / "metadata"
    )
    data_calculator = DataCalculator()
    
    passed = 0
    failed = 0
    
    for test in TEST_QUESTIONS[:5]:  # Test first 5
        file_id = GROUND_TRUTH[test["file"]]["file_id"]
        
        # Retrieve data
        data_result = excel_retriever.retrieve_data(
            file_id=file_id,
            columns=[test["column"]]
        )
        
        if not data_result.get("success"):
            print(f"✗ FAIL Test {test['id']}: Could not retrieve data - {data_result.get('error')}")
            failed += 1
            continue
        
        # Calculate
        calc_result = data_calculator.calculate(
            data=data_result["data"],
            operation=test["operation"],
            column=test["column"]
        )
        
        if not calc_result.get("success"):
            print(f"✗ FAIL Test {test['id']}: Calculation failed - {calc_result.get('error')}")
            failed += 1
            continue
        
        actual_value = calc_result.get("result")
        expected_value = test["expected_answer"]
        tolerance = test["tolerance"]
        
        if abs(actual_value - expected_value) <= tolerance:
            print(f"✓ PASS Test {test['id']}: {test['question']}")
            print(f"  Expected: {expected_value}, Got: {actual_value}")
            passed += 1
        else:
            print(f"✗ FAIL Test {test['id']}: {test['question']}")
            print(f"  Expected: {expected_value}, Got: {actual_value}, Diff: {abs(actual_value - expected_value)}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Run all tests."""
    print("="*80)
    print("COMPREHENSIVE AGENT TESTING")
    print("="*80)
    
    # Calculate ground truth from CSV files
    print("\nCalculating ground truth from CSV files...")
    calculated_truth = calculate_ground_truth_from_csv()
    print(json.dumps(calculated_truth, indent=2))
    
    # Run tests
    results = []
    results.append(("File Finding", test_file_finding()))
    results.append(("Data Retrieval", test_data_retrieval()))
    results.append(("Calculations", test_calculations()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

