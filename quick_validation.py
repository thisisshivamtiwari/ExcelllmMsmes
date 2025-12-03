#!/usr/bin/env python3
"""
Quick validation script - tests 5 key queries to verify system is working
"""

import requests
import json
import sys

BACKEND_URL = "http://localhost:8000"
PROVIDER = sys.argv[1] if len(sys.argv) > 1 else "gemini"

# Key test queries
KEY_QUERIES = [
    {
        "name": "Total Production",
        "query": "What is the total production quantity?",
        "expected": 237525
    },
    {
        "name": "Product with Most Defects",
        "query": "Which product has the most defects?",
        "expected": "Assembly-Z"
    },
    {
        "name": "Line Efficiency",
        "query": "Compare production efficiency across different lines",
        "expected": "comparison"  # Should return comparison data
    },
    {
        "name": "Production Trends",
        "query": "Show me production trends over the last month",
        "expected": "trend"  # Should return trend data
    },
    {
        "name": "OEE Calculation",
        "query": "Calculate OEE for all machines",
        "expected": "kpi"  # Should return OEE values
    }
]

def test_backend():
    """Quick validation of backend and key queries."""
    print("=" * 80)
    print("QUICK VALIDATION - Testing Key Queries")
    print("=" * 80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Provider: {PROVIDER}")
    print("=" * 80)
    
    # Check backend health
    try:
        health = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if health.status_code != 200:
            print("❌ Backend is not healthy!")
            return False
        print("✅ Backend is healthy")
    except:
        print("❌ Backend is not running!")
        print("\nPlease start the backend first:")
        print("  cd backend")
        print("  python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        return False
    
    # Test key queries
    print("\n" + "=" * 80)
    print("Testing Key Queries")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(KEY_QUERIES, 1):
        print(f"\n[{i}/{len(KEY_QUERIES)}] {test['name']}")
        print(f"Query: {test['query']}")
        
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/agent/query",
                json={
                    "query": test['query'],
                    "provider": PROVIDER
                },
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"❌ HTTP {response.status_code}")
                failed += 1
                continue
            
            data = response.json()
            
            if not data.get('success', False):
                print(f"❌ Query failed: {data.get('error', 'Unknown error')}")
                failed += 1
                continue
            
            answer = data.get('answer', '')
            
            # Simple validation
            if test['expected'] == "comparison" or test['expected'] == "trend" or test['expected'] == "kpi":
                if len(answer) > 50 and ("line" in answer.lower() or "trend" in answer.lower() or "oee" in answer.lower()):
                    print(f"✅ Got response (length: {len(answer)} chars)")
                    print(f"   Preview: {answer[:150]}...")
                    passed += 1
                else:
                    print(f"❌ Unexpected response format")
                    print(f"   Response: {answer[:200]}")
                    failed += 1
            elif isinstance(test['expected'], str):
                if test['expected'].lower() in answer.lower():
                    print(f"✅ Found expected value: {test['expected']}")
                    print(f"   Response: {answer[:150]}...")
                    passed += 1
                else:
                    print(f"❌ Expected '{test['expected']}' not found")
                    print(f"   Response: {answer[:200]}")
                    failed += 1
            elif isinstance(test['expected'], int):
                # Try to extract number
                import re
                numbers = re.findall(r'\d+', answer.replace(',', ''))
                if numbers:
                    found_num = int(numbers[0])
                    if abs(found_num - test['expected']) / test['expected'] < 0.05:  # 5% tolerance
                        print(f"✅ Found expected value: {test['expected']} (got: {found_num})")
                        passed += 1
                    else:
                        print(f"❌ Expected {test['expected']}, got {found_num}")
                        failed += 1
                else:
                    print(f"❌ Could not extract number from response")
                    print(f"   Response: {answer[:200]}")
                    failed += 1
        
        except requests.exceptions.Timeout:
            print(f"❌ Timeout after 60s")
            failed += 1
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("QUICK VALIDATION SUMMARY")
    print("=" * 80)
    print(f"✅ Passed: {passed}/{len(KEY_QUERIES)}")
    print(f"❌ Failed: {failed}/{len(KEY_QUERIES)}")
    print(f"Success Rate: {passed/len(KEY_QUERIES)*100:.1f}%")
    print("=" * 80)
    
    if passed == len(KEY_QUERIES):
        print("\n🎉 All key queries passed! System is working correctly.")
        print("   Ready to run comprehensive test suite:")
        print("   ./run_comprehensive_tests.sh")
        return True
    else:
        print("\n⚠️  Some queries failed. Please check:")
        print("   1. Backend logs for errors")
        print("   2. API keys are set correctly")
        print("   3. CSV files are uploaded and indexed")
        return False

if __name__ == "__main__":
    success = test_backend()
    sys.exit(0 if success else 1)

