#!/usr/bin/env python3
"""
Automated Test Script for LangChain Agent System
Tests 20+ questions and verifies answers against ground truth data.
"""

import requests
import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
import time

# Configuration
API_BASE_URL = "http://localhost:8000/api"
TEST_QUESTIONS = [
    # Category 1: Basic Data Retrieval
    {
        "question": "What is the total production quantity?",
        "expected_value": 237525,
        "tolerance": 0.01,  # 1% tolerance
        "category": "Basic Retrieval"
    },
    {
        "question": "What is the total inspected quantity?",
        "expected_value": 49107,
        "tolerance": 0.01,
        "category": "Basic Retrieval"
    },
    {
        "question": "How many units failed inspection?",
        "expected_value": 1687,
        "tolerance": 0.01,
        "category": "Basic Retrieval"
    },
    {
        "question": "What is the total maintenance cost?",
        "expected_value": 1030300,
        "tolerance": 0.01,
        "category": "Basic Retrieval"
    },
    {
        "question": "What is the total material consumption?",
        "expected_value": 136428,
        "tolerance": 0.01,
        "category": "Basic Retrieval"
    },
    # Category 2: Aggregations
    {
        "question": "What is the average production quantity per day?",
        "expected_value": 272.39,  # 237525 / 872
        "tolerance": 0.05,  # 5% tolerance for averages
        "category": "Aggregations"
    },
    {
        "question": "What is the pass rate percentage?",
        "expected_value": 96.57,  # (47420 / 49107) * 100
        "tolerance": 0.1,  # 0.1% tolerance for percentages
        "category": "Aggregations"
    },
    {
        "question": "What is the total downtime in hours?",
        "expected_value": 187.93,  # 11276 / 60
        "tolerance": 0.05,
        "category": "Aggregations"
    },
    {
        "question": "What is the average maintenance cost per maintenance event?",
        "expected_value": 7805.30,  # 1030300 / 132
        "tolerance": 0.05,
        "category": "Aggregations"
    },
    {
        "question": "What is the total material wastage?",
        "expected_value": 3704,
        "tolerance": 0.01,
        "category": "Aggregations"
    },
    # Category 3: Grouped Analysis
    {
        "question": "What is the total production quantity by product?",
        "expected_type": "grouped",
        "category": "Grouped Analysis"
    },
    {
        "question": "What is the total failed quantity by production line?",
        "expected_type": "grouped",
        "category": "Grouped Analysis"
    },
    {
        "question": "What is the total maintenance cost by machine?",
        "expected_type": "grouped",
        "category": "Grouped Analysis"
    },
    {
        "question": "What is the total consumption by material?",
        "expected_type": "grouped",
        "category": "Grouped Analysis"
    },
    {
        "question": "What is the total failed quantity by defect type?",
        "expected_type": "grouped",
        "category": "Grouped Analysis"
    },
    # Category 4: Trend Analysis
    {
        "question": "What is the production trend over time?",
        "expected_type": "trend",
        "category": "Trend Analysis"
    },
    {
        "question": "What is the quality trend (pass rate) over time?",
        "expected_type": "trend",
        "category": "Trend Analysis"
    },
    {
        "question": "What is the maintenance cost trend over time?",
        "expected_type": "trend",
        "category": "Trend Analysis"
    },
    # Category 5: Comparative Analysis
    {
        "question": "What are the top 5 products by production quantity?",
        "expected_type": "comparative",
        "category": "Comparative Analysis"
    },
    {
        "question": "What are the top 3 production lines with highest failed quantity?",
        "expected_type": "comparative",
        "category": "Comparative Analysis"
    },
    {
        "question": "Which machines have the highest maintenance costs?",
        "expected_type": "comparative",
        "category": "Comparative Analysis"
    },
    # Category 6: KPI Calculations
    {
        "question": "What is the First Pass Yield?",
        "expected_value": 96.57,
        "tolerance": 0.1,
        "category": "KPI"
    },
    {
        "question": "What is the defect rate?",
        "expected_value": 3.43,
        "tolerance": 0.1,
        "category": "KPI"
    },
    {
        "question": "What is the production efficiency (Actual vs Target)?",
        "expected_value": 84.88,  # (237525 / 279820) * 100
        "tolerance": 0.1,
        "category": "KPI"
    },
]


def check_agent_status() -> bool:
    """Check if agent is available."""
    try:
        response = requests.get(f"{API_BASE_URL}/agent/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            return status.get("available", False)
        return False
    except Exception as e:
        print(f"❌ Error checking agent status: {e}")
        return False


def ask_agent(question: str) -> Dict[str, Any]:
    """Send question to agent and get response."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/agent/query",
            json={"query": question},
            timeout=60
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def extract_numeric_value(response_text: str) -> float:
    """Extract numeric value from agent response."""
    import re
    # Try to find numbers in the response
    numbers = re.findall(r'\d+[.,]?\d*', response_text.replace(',', ''))
    if numbers:
        try:
            return float(numbers[0])
        except:
            pass
    return None


def verify_answer(test: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    """Verify agent answer against expected value."""
    result = {
        "passed": False,
        "error": None,
        "actual_value": None,
        "expected_value": test.get("expected_value"),
        "difference": None,
        "percentage_diff": None
    }
    
    if not response.get("success"):
        result["error"] = response.get("error", "Unknown error")
        return result
    
    answer_text = response.get("answer", "")
    
    # For numeric values
    if "expected_value" in test:
        actual_value = extract_numeric_value(answer_text)
        if actual_value is None:
            result["error"] = "Could not extract numeric value from response"
            return result
        
        result["actual_value"] = actual_value
        expected = test["expected_value"]
        tolerance = test.get("tolerance", 0.01)
        
        difference = abs(actual_value - expected)
        percentage_diff = (difference / expected * 100) if expected != 0 else 0
        
        result["difference"] = difference
        result["percentage_diff"] = percentage_diff
        
        if percentage_diff <= (tolerance * 100):
            result["passed"] = True
        else:
            result["error"] = f"Value outside tolerance: {percentage_diff:.2f}% > {tolerance * 100}%"
    
    # For type-based checks
    elif "expected_type" in test:
        expected_type = test["expected_type"]
        if expected_type == "grouped" and ("group" in answer_text.lower() or "by" in answer_text.lower()):
            result["passed"] = True
        elif expected_type == "trend" and ("trend" in answer_text.lower() or "over time" in answer_text.lower()):
            result["passed"] = True
        elif expected_type == "comparative" and ("top" in answer_text.lower() or "highest" in answer_text.lower()):
            result["passed"] = True
        else:
            result["error"] = f"Response doesn't match expected type: {expected_type}"
    
    return result


def run_tests():
    """Run all test cases."""
    print("=" * 80)
    print("Agent Testing Suite")
    print("=" * 80)
    print()
    
    # Check agent status
    print("🔍 Checking agent status...")
    if not check_agent_status():
        print("❌ Agent is not available. Please start the backend server.")
        return
    print("✅ Agent is available")
    print()
    
    # Run tests
    results = {
        "total": len(TEST_QUESTIONS),
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "details": []
    }
    
    for i, test in enumerate(TEST_QUESTIONS, 1):
        print(f"[{i}/{results['total']}] Testing: {test['question']}")
        print(f"   Category: {test['category']}")
        
        start_time = time.time()
        response = ask_agent(test['question'])
        elapsed_time = time.time() - start_time
        
        if not response.get("success"):
            print(f"   ❌ Error: {response.get('error', 'Unknown error')}")
            results["errors"] += 1
            results["details"].append({
                "question": test['question'],
                "status": "error",
                "error": response.get("error"),
                "time": elapsed_time
            })
            print()
            continue
        
        # Verify answer
        verification = verify_answer(test, response)
        
        if verification["passed"]:
            print(f"   ✅ PASSED (Time: {elapsed_time:.2f}s)")
            if verification["actual_value"] is not None:
                print(f"      Expected: {verification['expected_value']}, Got: {verification['actual_value']}")
            results["passed"] += 1
        else:
            print(f"   ❌ FAILED (Time: {elapsed_time:.2f}s)")
            if verification["actual_value"] is not None:
                print(f"      Expected: {verification['expected_value']}, Got: {verification['actual_value']}")
                print(f"      Difference: {verification['difference']} ({verification['percentage_diff']:.2f}%)")
            if verification["error"]:
                print(f"      Error: {verification['error']}")
            results["failed"] += 1
        
        results["details"].append({
            "question": test['question'],
            "category": test['category'],
            "status": "passed" if verification["passed"] else "failed",
            "verification": verification,
            "time": elapsed_time,
            "response": response.get("answer", "")[:200]  # First 200 chars
        })
        
        print()
        time.sleep(1)  # Rate limiting
    
    # Print summary
    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Total Tests: {results['total']}")
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"⚠️  Errors: {results['errors']}")
    print(f"Success Rate: {(results['passed'] / results['total'] * 100):.1f}%")
    print()
    
    # Save detailed results
    results_file = Path("agent_test_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"📄 Detailed results saved to: {results_file}")
    
    # Print failed tests
    if results['failed'] > 0 or results['errors'] > 0:
        print()
        print("Failed/Error Tests:")
        print("-" * 80)
        for detail in results['details']:
            if detail['status'] != 'passed':
                print(f"❌ {detail['question']}")
                if 'error' in detail:
                    print(f"   Error: {detail['error']}")
                elif 'verification' in detail and detail['verification'].get('error'):
                    print(f"   Error: {detail['verification']['error']}")
        print()


if __name__ == "__main__":
    run_tests()



