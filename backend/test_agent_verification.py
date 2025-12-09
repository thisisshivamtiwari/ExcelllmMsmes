"""
Test script to verify agent responses with actual queries and expected results.

This script:
1. Makes actual API calls to the agent
2. Verifies the responses against expected values
3. Validates chart data
4. Checks column name accuracy
"""

import os
import sys
import json
import requests
from typing import Dict, List, Any
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from verify_agent_responses import AgentResponseVerifier
from database import get_mongodb_uri

# Configuration
API_BASE_URL = "http://localhost:8000/api"
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "admin@admin.com")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "CHANGE_ME_IN_ENV")

def get_auth_token() -> str:
    """Get authentication token."""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    raise Exception(f"Failed to get auth token: {response.text}")

def get_user_id(token: str) -> str:
    """Get user ID from token."""
    # Decode JWT to get user_id (simplified - in production use proper JWT decoding)
    # For now, we'll get it from the files endpoint
    response = requests.get(
        f"{API_BASE_URL}/files/list",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        # We'll need to get user_id from user profile or use a known test user ID
        # For now, return a placeholder
        return "test_user_id"
    raise Exception("Could not determine user ID")

def query_agent(token: str, query: str, provider: str = "gemini") -> Dict[str, Any]:
    """Query the agent and get response."""
    response = requests.post(
        f"{API_BASE_URL}/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": query, "provider": provider}
    )
    if response.status_code == 200:
        return response.json()
    raise Exception(f"Agent query failed: {response.text}")

def extract_chart_json(response_text: str) -> Dict[str, Any]:
    """Extract chart JSON from agent response."""
    import re
    # Look for JSON in the response
    json_match = re.search(r'\{[^{}]*"chart_type"[^{}]*\}', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except:
            pass
    return None

def extract_number(response_text: str) -> float:
    """Extract first number from response."""
    import re
    numbers = re.findall(r'\d+\.?\d*', response_text.replace(',', ''))
    if numbers:
        try:
            return float(numbers[0])
        except:
            pass
    return None

def main():
    """Run verification tests."""
    print(f"\n{'='*80}")
    print(f"AGENT RESPONSE VERIFICATION TEST")
    print(f"{'='*80}\n")
    
    # Get auth token
    print("🔐 Authenticating...")
    try:
        token = get_auth_token()
        print("✅ Authentication successful")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return
    
    # Get user ID (you'll need to implement this properly)
    user_id = "69366c8393481cfdf197af6a"  # Replace with actual user ID from your system
    
    # Initialize verifier
    mongodb_uri = get_mongodb_uri()
    verifier = AgentResponseVerifier(
        user_id=user_id,
        mongodb_uri=mongodb_uri,
        database_name="excelllm"
    )
    
    # Test cases with expected results
    test_cases = [
        {
            "query": "What is the total production quantity?",
            "type": "calculation",
            "file_id": "047222e5-7e82-4526-a715-52984b56f591",  # production_logs.csv
            "expected_value": 265662.0,  # From actual data summary
            "tolerance": 100.0  # Allow 100 unit difference
        },
        {
            "query": "What is the average downtime minutes?",
            "type": "calculation",
            "file_id": "047222e5-7e82-4526-a715-52984b56f591",
            "expected_value": 12.77,  # From actual data summary
            "tolerance": 0.1
        },
        {
            "query": "Show quality metrics by inspector as a radar chart",
            "type": "chart",
            "file_id": "b95be2eb-f67c-4089-b6ed-11288640287c",  # quality_control.csv
            "expected_columns": ["Inspector_Name", "Inspected_Qty", "Passed_Qty", "Failed_Qty", "Rework_Count"]
        },
        {
            "query": "Display downtime trends over time as a line chart",
            "type": "chart",
            "file_id": "047222e5-7e82-4526-a715-52984b56f591",
            "expected_columns": ["Date", "Downtime_Minutes"]
        },
        {
            "query": "What columns are available in the quality control file?",
            "type": "column_check",
            "file_id": "b95be2eb-f67c-4089-b6ed-11288640287c"
        }
    ]
    
    print(f"\n📋 Running {len(test_cases)} test cases...\n")
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        print(f"\n[{i}/{len(test_cases)}] Query: {query}")
        print(f"Type: {test_case['type']}")
        
        try:
            # Query agent
            print("  🤖 Querying agent...")
            agent_response_data = query_agent(token, query)
            agent_answer = agent_response_data.get("answer", "")
            
            # Prepare verification data
            verification_data = {
                "query": query,
                "type": test_case["type"],
                "file_id": test_case.get("file_id"),
                "expected_columns": test_case.get("expected_columns", []),
                "agent_response": agent_answer
            }
            
            # Extract chart JSON if it's a chart query
            if test_case["type"] == "chart":
                chart_json = extract_chart_json(agent_answer)
                if chart_json:
                    verification_data["chart_json"] = chart_json
                    print(f"  📊 Chart JSON extracted")
                else:
                    print(f"  ⚠️  Could not extract chart JSON")
            
            # Extract expected value for calculations
            if test_case["type"] == "calculation":
                extracted_value = extract_number(agent_answer)
                if extracted_value:
                    print(f"  🔢 Extracted value: {extracted_value}")
                    verification_data["extracted_value"] = extracted_value
            
            # Run verification
            print("  ✅ Verifying response...")
            if test_case["type"] == "calculation":
                result = verifier.verify_calculation(
                    query,
                    agent_answer,
                    test_case.get("expected_value"),
                    test_case.get("tolerance", 0.01)
                )
            elif test_case["type"] == "chart":
                if verification_data.get("chart_json"):
                    result = verifier.verify_chart_data(
                        query,
                        verification_data["chart_json"],
                        test_case["file_id"],
                        test_case.get("expected_columns", [])
                    )
                else:
                    result = {"query": query, "verified": False, "errors": ["No chart JSON found"]}
            elif test_case["type"] == "column_check":
                result = verifier.verify_column_names(query, agent_answer, test_case["file_id"])
            else:
                result = {"query": query, "verified": False, "warnings": ["Unknown test type"]}
            
            results.append(result)
            
            # Print result
            status = "✅ PASSED" if result.get("verified") else "❌ FAILED"
            print(f"  {status}")
            if result.get("errors"):
                for error in result["errors"]:
                    print(f"    ❌ {error}")
            if result.get("warnings"):
                for warning in result["warnings"]:
                    print(f"    ⚠️  {warning}")
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "query": query,
                "verified": False,
                "errors": [str(e)]
            })
    
    # Summary
    passed = sum(1 for r in results if r.get("verified"))
    failed = len(results) - passed
    
    print(f"\n{'='*80}")
    print(f"VERIFICATION SUMMARY")
    print(f"{'='*80}")
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed} ({passed/len(results)*100:.1f}%)")
    print(f"Failed: {failed}")
    print(f"{'='*80}\n")
    
    # Save results
    output_file = f"agent_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    summary = {
        "total_tests": len(results),
        "passed": passed,
        "failed": failed,
        "pass_rate": (passed / len(results) * 100) if results else 0,
        "results": results,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📄 Results saved to: {output_file}\n")
    
    return summary


if __name__ == "__main__":
    main()

