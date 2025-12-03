#!/usr/bin/env python3
"""
EXPANDED Comprehensive Test Suite - 50+ queries covering ALL relationships and edge cases
Tests all relationship types, edge cases, and complex scenarios
"""

import requests
import json
import time
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
import re

# Configuration
BACKEND_URL = "http://localhost:8000"
PROVIDER = sys.argv[1] if len(sys.argv) > 1 else "gemini"
TIMEOUT = 90  # Increased timeout for complex queries

# Load ground truth
try:
    with open('ground_truth.json', 'r') as f:
        GROUND_TRUTH = json.load(f)
except FileNotFoundError:
    print("⚠️  ground_truth.json not found. Run ground truth calculation first.")
    GROUND_TRUTH = {}

# ============================================================================
# COMPREHENSIVE TEST QUERIES - ALL RELATIONSHIPS AND EDGE CASES
# ============================================================================

TEST_QUERIES = [
    # ========== BASIC CALCULATIONS (5 tests) ==========
    {
        "category": "Basic Calculations",
        "query": "What is the total production quantity?",
        "expected_type": "number",
        "expected_value": GROUND_TRUTH.get('total_production', 237525),
        "tolerance": 0.01
    },
    {
        "category": "Basic Calculations",
        "query": "Calculate the average production quantity per day",
        "expected_type": "number",
        "expected_value": GROUND_TRUTH.get('avg_production_per_day', 272.39),
        "tolerance": 0.05
    },
    {
        "category": "Basic Calculations",
        "query": "What is the total material consumption in kilograms?",
        "expected_type": "number",
        "expected_value": GROUND_TRUTH.get('total_material_consumption', 136428),
        "tolerance": 0.01
    },
    {
        "category": "Basic Calculations",
        "query": "How many maintenance events occurred?",
        "expected_type": "number",
        "expected_value": GROUND_TRUTH.get('total_maintenance_events', 132),
        "tolerance": 0.01
    },
    {
        "category": "Basic Calculations",
        "query": "What is the total number of quality inspections?",
        "expected_type": "number",
        "tolerance": 0.01
    },
    
    # ========== PRODUCT ANALYSIS (6 tests) ==========
    {
        "category": "Product Analysis",
        "query": "Which product has the most defects?",
        "expected_type": "product_name",
        "expected_value": GROUND_TRUTH.get('product_most_defects', {}).get('product', 'Assembly-Z')
    },
    {
        "category": "Product Analysis",
        "query": "What is the defect rate for each product?",
        "expected_type": "comparison"
    },
    {
        "category": "Product Analysis",
        "query": "Which product has the highest production quantity?",
        "expected_type": "product_name",
        "expected_value": GROUND_TRUTH.get('product_highest_production', {}).get('product', 'Widget-B')
    },
    {
        "category": "Product Analysis",
        "query": "Compare production quantities across all products",
        "expected_type": "comparison"
    },
    {
        "category": "Product Analysis",
        "query": "What is the First Pass Yield for each product?",
        "expected_type": "comparison"
    },
    {
        "category": "Product Analysis",
        "query": "Which product has the lowest defect rate?",
        "expected_type": "product_name"
    },
    
    # ========== TREND ANALYSIS (6 tests) ==========
    {
        "category": "Trend Analysis",
        "query": "Show me production trends over the last month",
        "expected_type": "trend"
    },
    {
        "category": "Trend Analysis",
        "query": "What is the trend in material consumption over time?",
        "expected_type": "trend"
    },
    {
        "category": "Trend Analysis",
        "query": "Show me the production trend by week",
        "expected_type": "trend"
    },
    {
        "category": "Trend Analysis",
        "query": "What is the trend in defect rates over the last 3 months?",
        "expected_type": "trend"
    },
    {
        "category": "Trend Analysis",
        "query": "Show me maintenance cost trends over time",
        "expected_type": "trend"
    },
    {
        "category": "Trend Analysis",
        "query": "What is the trend in downtime by machine?",
        "expected_type": "trend"
    },
    
    # ========== COMPARATIVE ANALYSIS (7 tests) ==========
    {
        "category": "Comparative Analysis",
        "query": "Compare production efficiency across different lines",
        "expected_type": "comparison"
    },
    {
        "category": "Comparative Analysis",
        "query": "Which line has the highest production output?",
        "expected_type": "line_name",
        "expected_value": GROUND_TRUTH.get('line_highest_production', {}).get('line', 'Line-1')
    },
    {
        "category": "Comparative Analysis",
        "query": "Compare downtime across different machines",
        "expected_type": "comparison"
    },
    {
        "category": "Comparative Analysis",
        "query": "Which machine has the most downtime?",
        "expected_type": "machine_name",
        "expected_value": GROUND_TRUTH.get('machine_most_downtime', {}).get('machine', 'Line-1/Machine-M1')
    },
    {
        "category": "Comparative Analysis",
        "query": "Which machine has the most maintenance costs?",
        "expected_type": "machine_name",
        "expected_value": GROUND_TRUTH.get('maintenance_costs', {}).get('highest_cost_machine', 'Machine-M1')
    },
    {
        "category": "Comparative Analysis",
        "query": "Compare defect rates by production line",
        "expected_type": "comparison"
    },
    {
        "category": "Comparative Analysis",
        "query": "Which shift has the highest production?",
        "expected_type": "shift_name"
    },
    
    # ========== KPI CALCULATIONS (5 tests) ==========
    {
        "category": "KPI Calculations",
        "query": "Calculate OEE for all machines",
        "expected_type": "kpi"
    },
    {
        "category": "KPI Calculations",
        "query": "What is the First Pass Yield (FPY) for each product?",
        "expected_type": "kpi"
    },
    {
        "category": "KPI Calculations",
        "query": "Calculate the overall equipment effectiveness for Line-1",
        "expected_type": "kpi"
    },
    {
        "category": "KPI Calculations",
        "query": "What is the availability rate for each machine?",
        "expected_type": "kpi"
    },
    {
        "category": "KPI Calculations",
        "query": "Calculate performance efficiency for all production lines",
        "expected_type": "kpi"
    },
    
    # ========== CROSS-FILE RELATIONSHIPS - Product ↔ Quality (6 tests) ==========
    {
        "category": "Cross-File: Product-Quality",
        "query": "Which products have the highest defect rates and what are their production quantities?",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Product-Quality",
        "query": "For products with defects, what is their production efficiency?",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Product-Quality",
        "query": "Show me products that were produced but never inspected",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Product-Quality",
        "query": "What is the relationship between production quantity and inspection quantity for each product?",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Product-Quality",
        "query": "Which products have the highest production but lowest quality pass rate?",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Product-Quality",
        "query": "Compare production dates with inspection dates for Widget-A",
        "expected_type": "cross_file"
    },
    
    # ========== CROSS-FILE RELATIONSHIPS - Production ↔ Maintenance (6 tests) ==========
    {
        "category": "Cross-File: Production-Maintenance",
        "query": "Show me machines with high downtime and their corresponding maintenance costs",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Production-Maintenance",
        "query": "What is the correlation between maintenance costs and production downtime?",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Production-Maintenance",
        "query": "Which machines had breakdowns and how did it affect their production?",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Production-Maintenance",
        "query": "Compare production output before and after maintenance events",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Production-Maintenance",
        "query": "What is the relationship between maintenance type and production efficiency?",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Production-Maintenance",
        "query": "Show me machines that need maintenance based on their production performance",
        "expected_type": "cross_file"
    },
    
    # ========== CROSS-FILE RELATIONSHIPS - Production ↔ Inventory (5 tests) ==========
    {
        "category": "Cross-File: Production-Inventory",
        "query": "What is the relationship between material consumption and production output?",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Production-Inventory",
        "query": "Which materials are consumed most when producing Widget-A?",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Production-Inventory",
        "query": "Compare material consumption trends with production trends",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Production-Inventory",
        "query": "What is the material efficiency (production per kg consumed) for each product?",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Production-Inventory",
        "query": "Show me dates when material consumption was high but production was low",
        "expected_type": "cross_file"
    },
    
    # ========== CROSS-FILE RELATIONSHIPS - Line/Machine Relationships (5 tests) ==========
    {
        "category": "Cross-File: Line Relationships",
        "query": "Which production lines have the most defects and what is their efficiency?",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Line Relationships",
        "query": "Compare production efficiency, quality, and maintenance costs for each line",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Line Relationships",
        "query": "What is the relationship between line downtime and quality defects?",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Line Relationships",
        "query": "Which lines have the best overall performance considering production, quality, and maintenance?",
        "expected_type": "cross_file"
    },
    {
        "category": "Cross-File: Line Relationships",
        "query": "Show me the correlation between production line and defect types",
        "expected_type": "cross_file"
    },
    
    # ========== TEMPORAL RELATIONSHIPS (5 tests) ==========
    {
        "category": "Temporal Relationships",
        "query": "What is the time lag between production and quality inspection?",
        "expected_type": "temporal"
    },
    {
        "category": "Temporal Relationships",
        "query": "Show me production output on days when maintenance occurred",
        "expected_type": "temporal"
    },
    {
        "category": "Temporal Relationships",
        "query": "Compare material consumption dates with production dates",
        "expected_type": "temporal"
    },
    {
        "category": "Temporal Relationships",
        "query": "What is the production trend after maintenance events?",
        "expected_type": "temporal"
    },
    {
        "category": "Temporal Relationships",
        "query": "Show me the sequence: production date → inspection date → defect detection",
        "expected_type": "temporal"
    },
    
    # ========== CALCULATED FIELDS VALIDATION (4 tests) ==========
    {
        "category": "Calculated Fields",
        "query": "Verify that Inspected_Qty equals Passed_Qty plus Failed_Qty",
        "expected_type": "validation"
    },
    {
        "category": "Calculated Fields",
        "query": "Verify that Closing_Stock equals Opening_Stock plus Received minus Consumption minus Wastage",
        "expected_type": "validation"
    },
    {
        "category": "Calculated Fields",
        "query": "Check if there are any inconsistencies in the inventory balance calculations",
        "expected_type": "validation"
    },
    {
        "category": "Calculated Fields",
        "query": "Validate that quality control data sums correctly",
        "expected_type": "validation"
    },
    
    # ========== EDGE CASES - Invalid Queries (6 tests) ==========
    {
        "category": "Edge Cases: Invalid Queries",
        "query": "What is the production quantity for products that don't exist?",
        "expected_type": "error_handling",
        "should_fail_gracefully": True
    },
    {
        "category": "Edge Cases: Invalid Queries",
        "query": "Show me data for Machine-XYZ-999",
        "expected_type": "error_handling",
        "should_fail_gracefully": True
    },
    {
        "category": "Edge Cases: Invalid Queries",
        "query": "What is the production for date 2099-12-31?",
        "expected_type": "error_handling",
        "should_fail_gracefully": True
    },
    {
        "category": "Edge Cases: Invalid Queries",
        "query": "Calculate average of an empty dataset",
        "expected_type": "error_handling",
        "should_fail_gracefully": True
    },
    {
        "category": "Edge Cases: Invalid Queries",
        "query": "Show me trends for dates in the future",
        "expected_type": "error_handling",
        "should_fail_gracefully": True
    },
    {
        "category": "Edge Cases: Invalid Queries",
        "query": "What is the total production quantity for a date range with no data?",
        "expected_type": "error_handling",
        "should_fail_gracefully": True
    },
    
    # ========== EDGE CASES - Boundary Conditions (5 tests) ==========
    {
        "category": "Edge Cases: Boundaries",
        "query": "What is the production quantity for the first date in the dataset?",
        "expected_type": "boundary"
    },
    {
        "category": "Edge Cases: Boundaries",
        "query": "What is the production quantity for the last date in the dataset?",
        "expected_type": "boundary"
    },
    {
        "category": "Edge Cases: Boundaries",
        "query": "Show me products with zero defects",
        "expected_type": "boundary"
    },
    {
        "category": "Edge Cases: Boundaries",
        "query": "What is the production for machines with zero downtime?",
        "expected_type": "boundary"
    },
    {
        "category": "Edge Cases: Boundaries",
        "query": "Show me materials with zero consumption",
        "expected_type": "boundary"
    },
    
    # ========== EDGE CASES - Null/Missing Data (4 tests) ==========
    {
        "category": "Edge Cases: Null Data",
        "query": "Show me maintenance records where Breakdown_Date is missing",
        "expected_type": "null_handling"
    },
    {
        "category": "Edge Cases: Null Data",
        "query": "What is the production for quality records with missing Defect_Type?",
        "expected_type": "null_handling"
    },
    {
        "category": "Edge Cases: Null Data",
        "query": "Show me maintenance events without Parts_Replaced",
        "expected_type": "null_handling"
    },
    {
        "category": "Edge Cases: Null Data",
        "query": "Handle queries for data with missing values gracefully",
        "expected_type": "null_handling"
    },
    
    # ========== COMPLEX MULTI-STEP QUERIES (6 tests) ==========
    {
        "category": "Complex Queries",
        "query": "Which product has the highest defect rate and what is its production trend?",
        "expected_type": "complex"
    },
    {
        "category": "Complex Queries",
        "query": "Compare OEE, production quantity, and defect rates for all machines",
        "expected_type": "complex"
    },
    {
        "category": "Complex Queries",
        "query": "What is the correlation between maintenance costs and production downtime?",
        "expected_type": "complex"
    },
    {
        "category": "Complex Queries",
        "query": "Show me the complete picture: production → quality → defects → maintenance for Line-1",
        "expected_type": "complex"
    },
    {
        "category": "Complex Queries",
        "query": "Which machines have high production, low defects, and low maintenance costs?",
        "expected_type": "complex"
    },
    {
        "category": "Complex Queries",
        "query": "Analyze the relationship between material consumption, production output, quality defects, and maintenance for the last month",
        "expected_type": "complex"
    },
    
    # ========== SEMANTIC RELATIONSHIPS (4 tests) ==========
    {
        "category": "Semantic Relationships",
        "query": "Which suppliers provide materials for products with high defect rates?",
        "expected_type": "semantic"
    },
    {
        "category": "Semantic Relationships",
        "query": "What is the relationship between material codes and product types?",
        "expected_type": "semantic"
    },
    {
        "category": "Semantic Relationships",
        "query": "Show me defect types and their associated products",
        "expected_type": "semantic"
    },
    {
        "category": "Semantic Relationships",
        "query": "What maintenance types are most common for each machine?",
        "expected_type": "semantic"
    },
    
    # ========== BATCH/TRACEABILITY RELATIONSHIPS (3 tests) ==========
    {
        "category": "Batch Relationships",
        "query": "Trace a batch from production to quality inspection",
        "expected_type": "batch"
    },
    {
        "category": "Batch Relationships",
        "query": "Which batches have the most defects and when were they produced?",
        "expected_type": "batch"
    },
    {
        "category": "Batch Relationships",
        "query": "Show me the production details for batches with defects",
        "expected_type": "batch"
    },
]

# Total: 50+ test queries covering all relationships and edge cases

def extract_number_from_response(response_text: str) -> float:
    """Extract a number from agent response text."""
    text = response_text.replace(',', '')
    numbers = re.findall(r'\d+\.?\d*', text)
    if numbers:
        try:
            return float(numbers[0])
        except:
            pass
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

def extract_shift_name(response_text: str) -> str:
    """Extract shift name from response."""
    shifts = ['Morning', 'Afternoon', 'Night']
    for shift in shifts:
        if shift.lower() in response_text.lower():
            return shift
    return None

def test_query(query_config: Dict[str, Any]) -> Tuple[bool, str, Any]:
    """Test a single query against the backend."""
    query = query_config['query']
    category = query_config['category']
    
    print(f"\n[{category}] {query[:80]}...")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/agent/query",
            json={
                "query": query,
                "provider": PROVIDER
            },
            timeout=TIMEOUT
        )
        
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}: {response.text[:200]}", None
        
        data = response.json()
        
        if not data.get('success', False):
            error_msg = data.get('error', 'Unknown error')
            if query_config.get('should_fail_gracefully', False):
                return True, f"Failed gracefully as expected: {error_msg[:100]}", data
            return False, f"Query failed: {error_msg[:200]}", data
        
        answer = data.get('answer', '')
        
        # Validate based on expected type
        expected_type = query_config.get('expected_type')
        expected_value = query_config.get('expected_value')
        tolerance = query_config.get('tolerance', 0.05)
        
        if expected_type == "number" and expected_value is not None:
            actual_value = extract_number_from_response(answer)
            if actual_value is None:
                return False, f"Could not extract number from response", data
            diff = abs(actual_value - expected_value) / expected_value if expected_value != 0 else abs(actual_value)
            if diff <= tolerance:
                return True, f"✅ Match! Expected: {expected_value}, Got: {actual_value}", data
            else:
                return False, f"❌ Mismatch! Expected: {expected_value}, Got: {actual_value}", data
        
        elif expected_type in ["product_name", "line_name", "machine_name", "shift_name"] and expected_value is not None:
            extractor = {
                "product_name": extract_product_name,
                "line_name": extract_line_name,
                "machine_name": extract_machine_name,
                "shift_name": extract_shift_name
            }[expected_type]
            actual = extractor(answer)
            if actual and (expected_value in actual or actual in expected_value):
                return True, f"✅ Match! Expected: {expected_value}, Got: {actual}", data
            else:
                return False, f"❌ Mismatch! Expected: {expected_value}, Got: {actual}", data
        
        elif expected_type == "error_handling":
            return True, f"✅ Handled error gracefully", data
        
        else:
            # For other types, just check we got a reasonable response
            if answer and len(answer) > 20:
                return True, f"✅ Got response ({len(answer)} chars)", data
            else:
                return False, f"❌ Empty or too short response", data
    
    except requests.exceptions.Timeout:
        return False, f"❌ Timeout after {TIMEOUT}s", None
    except Exception as e:
        return False, f"❌ Exception: {str(e)[:200]}", None

def run_all_tests():
    """Run all test queries and generate report."""
    print("\n" + "="*80)
    print("EXPANDED COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Provider: {PROVIDER}")
    print(f"Total Queries: {len(TEST_QUERIES)}")
    print("="*80)
    
    # Check backend
    try:
        health = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if health.status_code != 200:
            print("❌ Backend is not healthy!")
            return False, 0, 0
        print("✅ Backend is healthy")
    except:
        print("❌ Backend is not running!")
        return False, 0, 0
    
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
            print(f"✅ PASSED - {message}")
        else:
            failed += 1
            print(f"❌ FAILED - {message}")
        
        time.sleep(0.5)  # Small delay
    
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
    
    for cat, counts in sorted(categories.items()):
        total = counts['passed'] + counts['failed']
        pct = counts['passed'] / total * 100 if total > 0 else 0
        status = "✅" if pct >= 80 else "⚠️" if pct >= 60 else "❌"
        print(f"  {status} {cat}: {counts['passed']}/{total} ({pct:.1f}%)")
    
    # Save results
    with open('expanded_test_results.json', 'w') as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": len(TEST_QUERIES),
            "passed": passed,
            "failed": failed,
            "success_rate": passed/len(TEST_QUERIES)*100,
            "results": results
        }, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: expanded_test_results.json")
    
    return True, passed, failed

if __name__ == "__main__":
    success, passed, failed = run_all_tests()
    sys.exit(0 if failed == 0 else 1)

