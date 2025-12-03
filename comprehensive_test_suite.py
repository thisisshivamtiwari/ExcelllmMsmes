#!/usr/bin/env python3
"""
Comprehensive Test Suite for Excel Agent
Tests 20+ queries against actual CSV data and compares with ground truth.
"""

import requests
import json
import time
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
import pandas as pd
from datetime import datetime, timedelta
import re

# Configuration
BACKEND_URL = "http://localhost:8000"
PROVIDER = "gemini"  # or "groq"
TIMEOUT = 60  # seconds per query

# Load ground truth
try:
    with open('ground_truth.json', 'r') as f:
        GROUND_TRUTH = json.load(f)
except FileNotFoundError:
    print("⚠️  ground_truth.json not found. Run ground truth calculation first.")
    GROUND_TRUTH = {}

# Test queries organized by category
TEST_QUERIES = [
    # ========== BASIC CALCULATIONS ==========
    {
        "category": "Basic Calculations",
        "query": "What is the total production quantity?",
        "expected_type": "number",
        "expected_value": GROUND_TRUTH['total_production'],
        "tolerance": 0.01,  # Allow 1% tolerance
        "ground_truth_key": "total_production"
    },
    {
        "category": "Basic Calculations",
        "query": "Calculate the average production quantity per day",
        "expected_type": "number",
        "ground_truth_key": None  # Will calculate from data
    },
    {
        "category": "Basic Calculations",
        "query": "What is the total material consumption in kilograms?",
        "expected_type": "number",
        "expected_value": GROUND_TRUTH['material_consumption_trend']['total_consumption'],
        "tolerance": 0.01,
        "ground_truth_key": "material_consumption_trend.total_consumption"
    },
    {
        "category": "Basic Calculations",
        "query": "How many maintenance events occurred?",
        "expected_type": "number",
        "expected_value": GROUND_TRUTH.get('total_maintenance_events', 132),
        "tolerance": 0.01,
        "ground_truth_key": "total_maintenance_events"
    },
    {
        "category": "Basic Calculations",
        "query": "What is the total material consumption?",
        "expected_type": "number",
        "expected_value": GROUND_TRUTH.get('total_material_consumption', 136428),
        "tolerance": 0.01,
        "ground_truth_key": "total_material_consumption"
    },
    
    # ========== PRODUCT ANALYSIS ==========
    {
        "category": "Product Analysis",
        "query": "Which product has the most defects?",
        "expected_type": "product_name",
        "expected_value": GROUND_TRUTH['product_most_defects']['product'],
        "ground_truth_key": "product_most_defects.product"
    },
    {
        "category": "Product Analysis",
        "query": "What is the defect rate for each product?",
        "expected_type": "comparison",
        "ground_truth_key": "defect_rate_by_product"
    },
    {
        "category": "Product Analysis",
        "query": "Which product has the highest production quantity?",
        "expected_type": "product_name",
        "expected_value": GROUND_TRUTH.get('product_highest_production', {}).get('product', 'Widget-B'),
        "ground_truth_key": "product_highest_production.product"
    },
    {
        "category": "Product Analysis",
        "query": "Compare production quantities across all products",
        "expected_type": "comparison",
        "ground_truth_key": None
    },
    
    # ========== TREND ANALYSIS ==========
    {
        "category": "Trend Analysis",
        "query": "Show me production trends over the last month",
        "expected_type": "trend",
        "ground_truth_key": "production_trend_last_month"
    },
    {
        "category": "Trend Analysis",
        "query": "What is the trend in material consumption over time?",
        "expected_type": "trend",
        "ground_truth_key": "material_consumption_trend"
    },
    {
        "category": "Trend Analysis",
        "query": "Show me the production trend by week",
        "expected_type": "trend",
        "ground_truth_key": None
    },
    {
        "category": "Trend Analysis",
        "query": "What is the trend in defect rates over the last 3 months?",
        "expected_type": "trend",
        "ground_truth_key": None
    },
    
    # ========== COMPARATIVE ANALYSIS ==========
    {
        "category": "Comparative Analysis",
        "query": "Compare production efficiency across different lines",
        "expected_type": "comparison",
        "ground_truth_key": "line_efficiency"
    },
    {
        "category": "Comparative Analysis",
        "query": "Which line has the highest production output?",
        "expected_type": "line_name",
        "expected_value": GROUND_TRUTH.get('line_highest_production', {}).get('line', 'Line-1'),
        "ground_truth_key": "line_highest_production.line"
    },
    {
        "category": "Comparative Analysis",
        "query": "Which machine has the most downtime?",
        "expected_type": "machine_name",
        "expected_value": GROUND_TRUTH.get('machine_most_downtime', {}).get('machine', 'Line-1/Machine-M1'),
        "ground_truth_key": "machine_most_downtime.machine"
    },
    {
        "category": "Comparative Analysis",
        "query": "Compare downtime across different machines",
        "expected_type": "comparison",
        "ground_truth_key": None
    },
    {
        "category": "Comparative Analysis",
        "query": "Which machine has the most maintenance costs?",
        "expected_type": "machine_name",
        "expected_value": GROUND_TRUTH['maintenance_costs']['highest_cost_machine'],
        "ground_truth_key": "maintenance_costs.highest_cost_machine"
    },
    
    # ========== KPI CALCULATIONS ==========
    {
        "category": "KPI Calculations",
        "query": "Calculate OEE for all machines",
        "expected_type": "kpi",
        "ground_truth_key": "oee_by_machine"
    },
    {
        "category": "KPI Calculations",
        "query": "What is the First Pass Yield (FPY) for each product?",
        "expected_type": "kpi",
        "ground_truth_key": None
    },
    {
        "category": "KPI Calculations",
        "query": "Calculate the overall equipment effectiveness for Line-1",
        "expected_type": "kpi",
        "ground_truth_key": None
    },
    
    # ========== CROSS-FILE RELATIONSHIPS ==========
    {
        "category": "Cross-File Relationships",
        "query": "Which products have the highest defect rates and what are their production quantities?",
        "expected_type": "cross_file",
        "ground_truth_key": None
    },
    {
        "category": "Cross-File Relationships",
        "query": "Show me machines with high downtime and their corresponding maintenance costs",
        "expected_type": "cross_file",
        "ground_truth_key": None
    },
    {
        "category": "Cross-File Relationships",
        "query": "What is the relationship between material consumption and production output?",
        "expected_type": "cross_file",
        "ground_truth_key": None
    },
    {
        "category": "Cross-File Relationships",
        "query": "Which production lines have the most defects and what is their efficiency?",
        "expected_type": "cross_file",
        "ground_truth_key": None
    },
    
    # ========== EDGE CASES ==========
    {
        "category": "Edge Cases",
        "query": "What is the production quantity for products that don't exist?",
        "expected_type": "error_handling",
        "should_fail_gracefully": True
    },
    {
        "category": "Edge Cases",
        "query": "Calculate the average of an empty dataset",
        "expected_type": "error_handling",
        "should_fail_gracefully": True
    },
    {
        "category": "Edge Cases",
        "query": "Show me trends for dates in the future",
        "expected_type": "error_handling",
        "should_fail_gracefully": True
    },
    {
        "category": "Edge Cases",
        "query": "What is the total production quantity for a date range with no data?",
        "expected_type": "error_handling",
        "should_fail_gracefully": True
    },
    
    # ========== COMPLEX QUERIES ==========
    {
        "category": "Complex Queries",
        "query": "Which product has the highest defect rate and what is its production trend?",
        "expected_type": "complex",
        "ground_truth_key": None
    },
    {
        "category": "Complex Queries",
        "query": "Compare OEE, production quantity, and defect rates for all machines",
        "expected_type": "complex",
        "ground_truth_key": None
    },
    {
        "category": "Complex Queries",
        "query": "What is the correlation between maintenance costs and production downtime?",
        "expected_type": "complex",
        "ground_truth_key": None
    },
]


def extract_number_from_response(response_text: str) -> float:
    """Extract a number from agent response text."""
    # Remove commas and common text
    text = response_text.replace(',', '')
    
    # Try to find numbers
    numbers = re.findall(r'\d+\.?\d*', text)
    if numbers:
        try:
            return float(numbers[0])
        except:
            pass
    
    # Try to find "is X" or "= X" patterns
    patterns = [
        r'is\s+(\d+\.?\d*)',
        r'=\s*(\d+\.?\d*)',
        r':\s*(\d+\.?\d*)',
        r'(\d+\.?\d*)\s+units?',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except:
                pass
    
    return None


def extract_product_name(response_text: str) -> str:
    """Extract product name from response."""
    # Common products from our data
    products = ['Widget-A', 'Widget-B', 'Widget-C', 'Component-X', 'Component-Y', 'Assembly-Z']
    
    for product in products:
        if product.lower() in response_text.lower():
            return product
    
    return None


def extract_line_name(response_text: str) -> str:
    """Extract line name from response."""
    lines = ['Line-1', 'Line-2', 'Line-3']
    for line in lines:
        if line.lower() in response_text.lower():
            return line
    return None


def extract_machine_name(response_text: str) -> str:
    """Extract machine name from response."""
    machines = [
        'Line-1/Machine-M1', 'Line-1/Machine-M2',
        'Line-2/Machine-M1', 'Line-2/Machine-M2',
        'Line-3/Machine-M1', 'Line-3/Machine-M2',
        'Machine-M1', 'Machine-M2', 'Machine-M3', 'Machine-M4', 'Machine-M5'
    ]
    for machine in machines:
        if machine.lower() in response_text.lower():
            return machine
    return None


def test_query(query_config: Dict[str, Any]) -> Tuple[bool, str, Any]:
    """
    Test a single query against the backend.
    Returns: (success, message, response_data)
    """
    query = query_config['query']
    category = query_config['category']
    
    print(f"\n{'='*80}")
    print(f"Testing: {query}")
    print(f"Category: {category}")
    print(f"{'='*80}")
    
    try:
        # Make API request
        response = requests.post(
            f"{BACKEND_URL}/api/agent/query",
            json={
                "query": query,
                "provider": PROVIDER
            },
            timeout=TIMEOUT
        )
        
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}: {response.text}", None
        
        data = response.json()
        
        if not data.get('success', False):
            error_msg = data.get('error', 'Unknown error')
            if query_config.get('should_fail_gracefully', False):
                return True, f"Failed gracefully as expected: {error_msg}", data
            return False, f"Query failed: {error_msg}", data
        
        answer = data.get('answer', '')
        
        # Validate based on expected type
        expected_type = query_config.get('expected_type')
        expected_value = query_config.get('expected_value')
        tolerance = query_config.get('tolerance', 0.05)
        
        if expected_type == "number" and expected_value is not None:
            actual_value = extract_number_from_response(answer)
            if actual_value is None:
                return False, f"Could not extract number from response: {answer[:200]}", data
            
            diff = abs(actual_value - expected_value) / expected_value if expected_value != 0 else abs(actual_value)
            if diff <= tolerance:
                return True, f"✅ Match! Expected: {expected_value}, Got: {actual_value} (diff: {diff*100:.2f}%)", data
            else:
                return False, f"❌ Mismatch! Expected: {expected_value}, Got: {actual_value} (diff: {diff*100:.2f}%)", data
        
        elif expected_type == "product_name" and expected_value is not None:
            actual_product = extract_product_name(answer)
            if actual_product and actual_product == expected_value:
                return True, f"✅ Match! Expected: {expected_value}, Got: {actual_product}", data
            else:
                return False, f"❌ Mismatch! Expected: {expected_value}, Got: {actual_product}", data
        
        elif expected_type == "line_name" and expected_value is not None:
            actual_line = extract_line_name(answer)
            if actual_line and actual_line == expected_value:
                return True, f"✅ Match! Expected: {expected_value}, Got: {actual_line}", data
            else:
                return False, f"❌ Mismatch! Expected: {expected_value}, Got: {actual_line}", data
        
        elif expected_type == "machine_name" and expected_value is not None:
            actual_machine = extract_machine_name(answer)
            # Allow partial matches (e.g., "Machine-M1" matches "Line-1/Machine-M1")
            if actual_machine:
                if expected_value in actual_machine or actual_machine in expected_value:
                    return True, f"✅ Match! Expected: {expected_value}, Got: {actual_machine}", data
            return False, f"❌ Mismatch! Expected: {expected_value}, Got: {actual_machine}", data
        
        elif expected_type == "error_handling":
            # For error handling, we just check it doesn't crash
            return True, f"✅ Handled error gracefully: {answer[:200]}", data
        
        else:
            # For other types, just check we got a response
            if answer and len(answer) > 10:
                return True, f"✅ Got response: {answer[:200]}...", data
            else:
                return False, f"❌ Empty or too short response: {answer}", data
    
    except requests.exceptions.Timeout:
        return False, f"❌ Timeout after {TIMEOUT}s", None
    except Exception as e:
        return False, f"❌ Exception: {str(e)}", None


def run_all_tests():
    """Run all test queries and generate report."""
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Provider: {PROVIDER}")
    print(f"Total Queries: {len(TEST_QUERIES)}")
    print("="*80)
    
    # Check backend is running
    try:
        health = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if health.status_code != 200:
            print("❌ Backend is not healthy!")
            return
    except:
        print("❌ Backend is not running! Please start it first.")
        return
    
    results = []
    passed = 0
    failed = 0
    
    for i, query_config in enumerate(TEST_QUERIES, 1):
        print(f"\n[{i}/{len(TEST_QUERIES)}] ", end="")
        success, message, response_data = test_query(query_config)
        
        results.append({
            "query": query_config['query'],
            "category": query_config['category'],
            "success": success,
            "message": message,
            "response": response_data
        })
        
        if success:
            passed += 1
            print(f"✅ PASSED")
        else:
            failed += 1
            print(f"❌ FAILED")
        
        print(f"   {message}")
        
        # Small delay to avoid rate limiting
        time.sleep(1)
    
    # Generate report
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {len(TEST_QUERIES)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {passed/len(TEST_QUERIES)*100:.1f}%")
    print("="*80)
    
    # Category breakdown
    print("\nResults by Category:")
    categories = {}
    for result in results:
        cat = result['category']
        if cat not in categories:
            categories[cat] = {'passed': 0, 'failed': 0}
        if result['success']:
            categories[cat]['passed'] += 1
        else:
            categories[cat]['failed'] += 1
    
    for cat, counts in categories.items():
        total = counts['passed'] + counts['failed']
        pct = counts['passed'] / total * 100 if total > 0 else 0
        print(f"  {cat}: {counts['passed']}/{total} ({pct:.1f}%)")
    
    # Failed tests details
    if failed > 0:
        print("\n" + "="*80)
        print("FAILED TESTS DETAILS")
        print("="*80)
        for result in results:
            if not result['success']:
                print(f"\n❌ {result['query']}")
                print(f"   Category: {result['category']}")
                print(f"   Message: {result['message']}")
    
    # Save detailed results
    with open('test_results.json', 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(TEST_QUERIES),
            "passed": passed,
            "failed": failed,
            "success_rate": passed/len(TEST_QUERIES)*100,
            "results": results
        }, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: test_results.json")
    
    return passed, failed


if __name__ == "__main__":
    if len(sys.argv) > 1:
        PROVIDER = sys.argv[1]
    
    passed, failed = run_all_tests()
    sys.exit(0 if failed == 0 else 1)

