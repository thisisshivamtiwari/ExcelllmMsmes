#!/usr/bin/env python3
"""
Comprehensive Test Suite for Excel Agent System
Tests 20+ queries against actual data and verifies accuracy
"""

import sys
import os
import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
import time
from datetime import datetime, timedelta

# Test via API endpoint only - no direct imports needed

# Load ground truth
with open('test_ground_truth.json', 'r') as f:
    GROUND_TRUTH = json.load(f)

# Test configuration
BACKEND_URL = "http://localhost:8000"
PROVIDER = "gemini"  # or "groq"

class TestResult:
    def __init__(self, query: str, expected: Any, actual: Any, passed: bool, error: Optional[str] = None):
        self.query = query
        self.expected = expected
        self.actual = actual
        self.passed = passed
        self.error = error
        self.timestamp = datetime.now().isoformat()

class ComprehensiveTestSuite:
    def __init__(self):
        self.results: List[TestResult] = []
    
    def test_via_api(self, query: str) -> Dict[str, Any]:
        """Test query via API endpoint"""
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/agent/query",
                json={"question": query, "provider": PROVIDER},
                timeout=120
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": str(e)}
    
    def extract_number(self, text: str) -> Optional[float]:
        """Extract numeric value from text response"""
        import re
        # Try to find numbers (including decimals)
        numbers = re.findall(r'-?\d+\.?\d*', text.replace(',', ''))
        if numbers:
            try:
                return float(numbers[0])
            except:
                pass
        return None
    
    def compare_values(self, expected: Any, actual: Any, tolerance: float = 0.01) -> bool:
        """Compare expected vs actual with tolerance"""
        if isinstance(expected, dict):
            if isinstance(actual, dict):
                # Compare dictionaries
                for key, exp_val in expected.items():
                    if key not in actual:
                        return False
                    if not self.compare_values(exp_val, actual[key], tolerance):
                        return False
                return True
            return False
        
        # Numeric comparison
        try:
            exp_num = float(expected)
            act_num = float(actual)
            diff = abs(exp_num - act_num)
            return diff <= (exp_num * tolerance) or diff <= tolerance
        except:
            # String comparison
            return str(expected).lower() in str(actual).lower()
    
    def run_test(self, query: str, expected: Any, category: str = "general"):
        """Run a single test"""
        print(f"\n{'='*80}")
        print(f"Test: {query}")
        print(f"Category: {category}")
        print(f"Expected: {expected}")
        
        start_time = time.time()
        result = self.test_via_api(query)
        elapsed = time.time() - start_time
        
        if "error" in result:
            print(f"❌ ERROR: {result['error']}")
            self.results.append(TestResult(
                query, expected, None, False, result['error']
            ))
            return False
        
        answer = result.get('answer', '')
        print(f"Actual: {answer}")
        print(f"Time: {elapsed:.2f}s")
        
        # Extract numeric value if expected is numeric
        if isinstance(expected, (int, float)):
            actual_num = self.extract_number(answer)
            if actual_num is not None:
                passed = self.compare_values(expected, actual_num, tolerance=0.05)
            else:
                passed = False
        elif isinstance(expected, dict):
            # For dict comparisons, check if key values are mentioned
            passed = all(
                str(val).lower() in answer.lower() or 
                self.extract_number(answer) == val
                for val in expected.values()
            )
        else:
            passed = str(expected).lower() in answer.lower()
        
        if passed:
            print(f"✅ PASSED")
        else:
            print(f"❌ FAILED")
            if isinstance(expected, (int, float)) and actual_num is not None:
                print(f"   Expected: {expected}, Got: {actual_num}, Diff: {abs(expected - actual_num)}")
        
        self.results.append(TestResult(
            query, expected, answer, passed
        ))
        return passed
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("\n" + "="*80)
        print("COMPREHENSIVE TEST SUITE - 20+ QUERIES")
        print("="*80)
        
        # Test 1-5: Basic Calculations
        print("\n📊 CATEGORY 1: Basic Calculations")
        self.run_test(
            "What is the total production quantity?",
            GROUND_TRUTH['total_production'],
            "calculation"
        )
        self.run_test(
            "Calculate the total maintenance cost",
            GROUND_TRUTH['total_maintenance_cost'],
            "calculation"
        )
        self.run_test(
            "What is the total inventory consumption?",
            GROUND_TRUTH['total_consumption'],
            "calculation"
        )
        self.run_test(
            "What is the average production per day?",
            GROUND_TRUTH['avg_production_per_day'],
            "calculation"
        )
        self.run_test(
            "Calculate total downtime in hours",
            GROUND_TRUTH['total_downtime_hours'],
            "calculation"
        )
        
        # Test 6-10: Comparative Analysis
        print("\n📈 CATEGORY 2: Comparative Analysis")
        self.run_test(
            "Which product has the most defects?",
            GROUND_TRUTH['product_most_defects'],
            "comparative"
        )
        self.run_test(
            "What is the most common defect type?",
            GROUND_TRUTH['most_common_defect'],
            "comparative"
        )
        self.run_test(
            "Which production line has the highest production?",
            GROUND_TRUTH['best_line'],
            "comparative"
        )
        self.run_test(
            "Compare production efficiency across different lines",
            None,  # Complex comparison
            "comparative"
        )
        self.run_test(
            "Which material has the highest wastage?",
            GROUND_TRUTH['highest_wastage'],
            "comparative"
        )
        
        # Test 11-15: Trend Analysis
        print("\n📉 CATEGORY 3: Trend Analysis")
        self.run_test(
            "Show me production trends over the last month",
            None,  # Trend data
            "trend"
        )
        self.run_test(
            "What is the production trend over time?",
            None,  # Trend data
            "trend"
        )
        self.run_test(
            "Show quality control trends",
            None,  # Trend data
            "trend"
        )
        self.run_test(
            "Analyze maintenance frequency trends",
            None,  # Trend data
            "trend"
        )
        self.run_test(
            "Show inventory consumption trends",
            None,  # Trend data
            "trend"
        )
        
        # Test 16-20: KPI Calculations
        print("\n🎯 CATEGORY 4: KPI Calculations")
        self.run_test(
            "Calculate OEE for all machines",
            None,  # KPI calculation
            "kpi"
        )
        self.run_test(
            "What is the quality pass rate?",
            GROUND_TRUTH['quality_pass_rate'],
            "kpi"
        )
        self.run_test(
            "Calculate FPY (First Pass Yield)",
            None,  # KPI calculation
            "kpi"
        )
        self.run_test(
            "What is the defect rate?",
            None,  # KPI calculation
            "kpi"
        )
        self.run_test(
            "Calculate production efficiency",
            GROUND_TRUTH['most_efficient_line'],
            "kpi"
        )
        
        # Test 21-25: Cross-File Relationships
        print("\n🔗 CATEGORY 5: Cross-File Relationships")
        self.run_test(
            "Which products have the highest defect rates?",
            None,  # Cross-file: production + quality
            "relationship"
        )
        self.run_test(
            "How does maintenance downtime affect production?",
            None,  # Cross-file: maintenance + production
            "relationship"
        )
        self.run_test(
            "Which machines have the most breakdowns?",
            None,  # Cross-file: maintenance + production
            "relationship"
        )
        self.run_test(
            "What is the relationship between material consumption and production?",
            None,  # Cross-file: inventory + production
            "relationship"
        )
        self.run_test(
            "Which supplier provides the most materials?",
            GROUND_TRUTH['supplier_most_materials'],
            "relationship"
        )
        
        # Test 26-30: Edge Cases
        print("\n🔍 CATEGORY 6: Edge Cases")
        self.run_test(
            "Find products with zero defects",
            None,  # Edge case: zero values
            "edge_case"
        )
        self.run_test(
            "Which machines have never had maintenance?",
            None,  # Edge case: missing relationships
            "edge_case"
        )
        self.run_test(
            "What is the production on weekends?",
            None,  # Edge case: date filtering
            "edge_case"
        )
        self.run_test(
            "Show me data for a specific date range",
            None,  # Edge case: custom date range
            "edge_case"
        )
        self.run_test(
            "What is the production by shift?",
            None,  # Edge case: categorical grouping
            "edge_case"
        )
        
        # Test 31-35: Advanced Relationships
        print("\n🔗 CATEGORY 7: Advanced Cross-File Relationships")
        self.run_test(
            "Which products have both high production and high defect rates?",
            None,  # Cross-file: production + quality analysis
            "relationship"
        )
        self.run_test(
            "What is the correlation between maintenance cost and production downtime?",
            None,  # Cross-file: maintenance + production
            "relationship"
        )
        self.run_test(
            "Which materials are consumed most for high-production products?",
            None,  # Cross-file: inventory + production
            "relationship"
        )
        self.run_test(
            "Show me machines with frequent breakdowns and their production impact",
            None,  # Cross-file: maintenance + production
            "relationship"
        )
        self.run_test(
            "What is the quality pass rate by production line?",
            None,  # Cross-file: production + quality
            "relationship"
        )
        
        # Test 36-40: Formula Verification
        print("\n🧮 CATEGORY 8: Formula Verification")
        self.run_test(
            "Verify that Closing_Stock = Opening_Stock + Received - Consumption - Wastage",
            None,  # Formula verification
            "formula"
        )
        self.run_test(
            "Verify that Inspected_Qty = Passed_Qty + Failed_Qty",
            None,  # Formula verification
            "formula"
        )
        self.run_test(
            "Calculate production efficiency as Actual_Qty / Target_Qty * 100",
            None,  # Formula verification
            "formula"
        )
        self.run_test(
            "What is the defect rate percentage?",
            None,  # Formula: Failed_Qty / Inspected_Qty * 100
            "formula"
        )
        self.run_test(
            "Calculate total inventory value",
            None,  # Formula: Closing_Stock * Unit_Cost
            "formula"
        )
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"❌ Failed: {failed} ({failed/total*100:.1f}%)")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.results:
                if not result.passed:
                    print(f"\n  Query: {result.query}")
                    print(f"  Expected: {result.expected}")
                    print(f"  Actual: {result.actual}")
                    if result.error:
                        print(f"  Error: {result.error}")
        
        # Save results
        results_file = Path("test_results.json")
        with open(results_file, 'w') as f:
            json.dump([
                {
                    "query": r.query,
                    "expected": r.expected,
                    "actual": r.actual,
                    "passed": r.passed,
                    "error": r.error,
                    "timestamp": r.timestamp
                }
                for r in self.results
            ], f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")

if __name__ == "__main__":
    # Check if backend is running
    try:
        response = requests.get(f"{BACKEND_URL}/api/agent/status", timeout=5)
        if response.status_code != 200:
            print("❌ Backend is not running or not responding correctly")
            print(f"   Status: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print("❌ Cannot connect to backend. Please start the backend first:")
        print("   cd backend && python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        sys.exit(1)
    
    suite = ComprehensiveTestSuite()
    suite.run_all_tests()

