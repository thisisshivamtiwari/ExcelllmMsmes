"""
Test Suite for Agent System - 125 Questions
Tests all agent queries with verification against expected answers
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from decimal import Decimal

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.mongodb_agent import execute_agent_query
from database import connect_to_mongodb, get_database
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

# Test user ID (will be created or retrieved)
TEST_USER_ID = None


async def get_test_questions() -> List[Dict[str, Any]]:
    """
    Load test questions from MongoDB qa_bank collection.
    Returns list of questions with expected answers.
    """
    try:
        db = get_database()
        qa_collection = db["qa_bank"]
        
        # Try to get verified questions first
        questions = await qa_collection.find({
            "verified": True
        }).to_list(length=125)
        
        # If no verified questions, get any questions
        if not questions:
            questions = await qa_collection.find({}).to_list(length=125)
            print(f"⚠ No verified questions found, using {len(questions)} unverified questions")
        
        return questions
    except Exception as e:
        print(f"Error loading questions: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


async def test_agent_query(
    question: Dict[str, Any],
    user_id: str,
    provider: str = "gemini"
) -> Dict[str, Any]:
    """
    Test a single agent query and compare with expected answer.
    
    Returns:
        Test result with pass/fail status and details
    """
    # Handle different field names
    question_text = question.get("question_text") or question.get("question", "")
    question_id = question.get("question_id", "")
    expected_answer = question.get("answer_structured", {})
    expected_value = expected_answer.get("value") if expected_answer else None
    file_id = question.get("file_id")
    
    print(f"\n{'='*80}")
    print(f"Testing: {question_id}")
    print(f"Question: {question_text}")
    print(f"Expected: {expected_value}")
    
    try:
        # Execute agent query
        result = await execute_agent_query(
            question=question_text,
            user_id=user_id,
            file_id=file_id,
            provider=provider,
            max_iterations=10
        )
        
        if not result.get("success"):
            return {
                "question_id": question_id,
                "question": question_text,
                "status": "failed",
                "error": result.get("error", "Unknown error"),
                "answer": result.get("answer_short", ""),
                "expected": expected_value,
                "actual": None,
                "tools_called": result.get("tools_called", []),
                "latency_ms": result.get("latency_ms", 0)
            }
        
        # Extract actual value from answer
        actual_value = None
        answer_text = result.get("answer_short", "")
        values = result.get("values", {})
        
        # First, try to extract from values dict (most reliable)
        if values:
            # Look for numeric values in result - prioritize aggregation results
            for key, value in values.items():
                if isinstance(value, (int, float, Decimal)):
                    # Skip row_count and other metadata
                    if key not in ["row_count", "matched_row_count"]:
                        actual_value = float(value)
                        break
        
        # Try parsing from answer text (look for the main number mentioned)
        if actual_value is None:
            import re
            # Look for patterns like "is 308420" or "= 308420" or "308420 units"
            patterns = [
                r'(?:is|equals?|=\s*)(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',
                r'(\d{4,})',  # Large numbers (4+ digits) are likely the answer
            ]
            for pattern in patterns:
                matches = re.findall(pattern, answer_text, re.IGNORECASE)
                if matches:
                    try:
                        # Take the largest number found (likely the answer)
                        numbers = [float(m.replace(',', '')) for m in matches]
                        if numbers:
                            actual_value = max(numbers)
                            break
                    except:
                        pass
        
        # Compare with expected
        passed = False
        if expected_value is not None and actual_value is not None:
            # For numeric comparisons, allow small tolerance
            if isinstance(expected_value, (int, float)) and isinstance(actual_value, (int, float)):
                tolerance = abs(expected_value * 0.01)  # 1% tolerance
                passed = abs(expected_value - actual_value) <= tolerance
            else:
                # For string comparisons, exact match
                passed = str(expected_value).lower() == str(actual_value).lower()
        elif expected_value is None:
            # If no expected value, check if answer is non-empty
            passed = bool(answer_text)
        
        print(f"Actual: {actual_value}")
        print(f"Status: {'✓ PASSED' if passed else '✗ FAILED'}")
        print(f"Tools called: {', '.join(result.get('tools_called', []))}")
        print(f"Latency: {result.get('latency_ms', 0)}ms")
        
        return {
            "question_id": question_id,
            "question": question_text,
            "status": "passed" if passed else "failed",
            "error": None if passed else "Value mismatch",
            "answer": answer_text,
            "expected": expected_value,
            "actual": actual_value,
            "tools_called": result.get("tools_called", []),
            "latency_ms": result.get("latency_ms", 0),
            "provenance": result.get("provenance")
        }
    
    except Exception as e:
        import traceback
        print(f"✗ ERROR: {str(e)}")
        print(traceback.format_exc())
        
        return {
            "question_id": question_id,
            "question": question_text,
            "status": "error",
            "error": str(e),
            "answer": None,
            "expected": expected_value,
            "actual": None,
            "tools_called": [],
            "latency_ms": 0
        }


async def run_all_tests(provider: str = "gemini", limit: int = None):
    """
    Run all test questions and generate report.
    
    Args:
        provider: LLM provider ("gemini" or "groq")
        limit: Optional limit on number of questions to test
    """
    print("="*80)
    print("AGENT SYSTEM TEST SUITE - 125 QUESTIONS")
    print("="*80)
    
    # Connect to MongoDB
    try:
        await connect_to_mongodb()
        print("✓ Connected to MongoDB")
    except Exception as e:
        print(f"✗ Failed to connect to MongoDB: {str(e)}")
        return
    
    # Get test user (use first user or create test user)
    try:
        db = get_database()
        users_collection = db["users"]
        test_user = await users_collection.find_one({})
        
        if not test_user:
            print("✗ No users found. Please create a user first.")
            return
        
        user_id = str(test_user["_id"])
        print(f"✓ Using test user: {user_id}")
    except Exception as e:
        print(f"✗ Error getting test user: {str(e)}")
        return
    
    # Load questions
    print("\nLoading test questions...")
    questions = await get_test_questions()
    
    if not questions:
        print("✗ No verified questions found in qa_bank collection")
        return
    
    if limit:
        questions = questions[:limit]
    
    print(f"✓ Loaded {len(questions)} questions")
    
    # Run tests
    results = []
    passed = 0
    failed = 0
    errors = 0
    
    for i, question in enumerate(questions, 1):
        print(f"\n[{i}/{len(questions)}] Processing...")
        result = await test_agent_query(question, user_id, provider)
        results.append(result)
        
        if result["status"] == "passed":
            passed += 1
        elif result["status"] == "failed":
            failed += 1
        else:
            errors += 1
    
    # Generate report
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    print(f"Total Questions: {len(questions)}")
    print(f"✓ Passed: {passed}")
    print(f"✗ Failed: {failed}")
    print(f"⚠ Errors: {errors}")
    print(f"Success Rate: {(passed/len(questions)*100):.2f}%")
    
    # Calculate average latency
    avg_latency = sum(r.get("latency_ms", 0) for r in results) / len(results) if results else 0
    print(f"Average Latency: {avg_latency:.2f}ms")
    
    # Save detailed results
    results_file = Path(__file__).parent.parent / "agent_test_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "summary": {
                "total": len(questions),
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "success_rate": passed/len(questions)*100 if questions else 0,
                "avg_latency_ms": avg_latency
            },
            "results": results
        }, f, indent=2, default=str)
    
    print(f"\n✓ Detailed results saved to: {results_file}")
    
    # Show failed questions
    if failed > 0 or errors > 0:
        print("\n" + "="*80)
        print("FAILED QUESTIONS:")
        print("="*80)
        for r in results:
            if r["status"] != "passed":
                print(f"\n[{r['question_id']}] {r['question']}")
                print(f"  Expected: {r['expected']}")
                print(f"  Actual: {r['actual']}")
                print(f"  Error: {r['error']}")
                print(f"  Tools: {', '.join(r['tools_called'])}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test agent system with 125 questions")
    parser.add_argument("--provider", default="gemini", choices=["gemini", "groq"], help="LLM provider")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions to test")
    
    args = parser.parse_args()
    
    asyncio.run(run_all_tests(args.provider, args.limit))

