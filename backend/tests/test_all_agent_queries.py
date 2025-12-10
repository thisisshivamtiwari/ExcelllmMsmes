"""
Comprehensive test suite for agent queries
Tests all example queries, question generator questions, and chart generation
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logging.info(f"Loaded environment variables from {env_path}")
except ImportError:
    pass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_database, connect_to_mongodb
from models.user import UserInDB
from agent.mongodb_agent import execute_agent_query
from bson import ObjectId

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentQueryTester:
    """Test agent queries comprehensively"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.db = get_database()
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "test_results": []
        }
    
    async def get_example_queries(self) -> List[Dict[str, str]]:
        """Get example queries from the API"""
        examples = [
            {
                "question": "What is the total production quantity?",
                "category": "aggregation",
                "expects_chart": False
            },
            {
                "question": "Show me the monthly production trend",
                "category": "timeseries",
                "expects_chart": True
            },
            {
                "question": "Show me daily production trend as a line chart",
                "category": "timeseries",
                "expects_chart": True
            },
            {
                "question": "Compare production between Line-1 and Line-2",
                "category": "comparison",
                "expects_chart": False
            },
            {
                "question": "What is the average quality score?",
                "category": "aggregation",
                "expects_chart": False
            },
            {
                "question": "Show me the top 5 products by sales",
                "category": "ranking",
                "expects_chart": True
            }
        ]
        return examples
    
    async def get_question_generator_questions(self) -> List[Dict[str, Any]]:
        """Get verified questions from question generator"""
        qa_collection = self.db["qa_bank"]
        
        # Get verified questions for this user
        cursor = qa_collection.find({
            "user_id": ObjectId(self.user_id),
            "verified": True
        }).limit(50)  # Test up to 50 questions
        
        questions = []
        async for doc in cursor:
            questions.append({
                "question": doc.get("question", ""),
                "type": doc.get("type", ""),
                "file_id": doc.get("file_id", ""),
                "table_name": doc.get("table_name", "Sheet1"),
                "expected_answer": doc.get("answer_structured", {}).get("value"),
                "expects_chart": doc.get("type") in ["trend", "comparative"] and "chart" in doc.get("question", "").lower()
            })
        
        return questions
    
    async def test_query(
        self,
        question: str,
        file_id: Optional[str] = None,
        expects_chart: bool = False,
        expected_value: Optional[Any] = None,
        category: str = "unknown"
    ) -> Dict[str, Any]:
        """Test a single query"""
        self.results["total_tests"] += 1
        
        test_result = {
            "question": question,
            "category": category,
            "file_id": file_id,
            "expects_chart": expects_chart,
            "expected_value": expected_value,
            "success": False,
            "error": None,
            "has_chart": False,
            "answer": None,
            "tools_called": [],
            "latency_ms": 0
        }
        
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"Testing: {question}")
            logger.info(f"Category: {category}, Expects Chart: {expects_chart}")
            
            start_time = datetime.now()
            
            # Execute query
            result = await execute_agent_query(
                question=question,
                user_id=self.user_id,
                file_id=file_id,
                provider="gemini",
                max_iterations=15
            )
            
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            test_result["latency_ms"] = latency_ms
            test_result["answer"] = result.get("answer_short", "")
            test_result["tools_called"] = result.get("tools_called", [])
            test_result["has_chart"] = result.get("chart_config") is not None
            
            # Check success
            if not result.get("success", False):
                test_result["error"] = result.get("error", "Unknown error")
                test_result["success"] = False
                logger.error(f"❌ Query failed: {test_result['error']}")
            else:
                # Check chart requirement
                if expects_chart and not test_result["has_chart"]:
                    test_result["error"] = "Expected chart but none was generated"
                    test_result["success"] = False
                    logger.warning(f"⚠️  Chart expected but not generated")
                elif not expects_chart and test_result["has_chart"]:
                    # Chart generated but not expected - this is OK
                    logger.info(f"✓ Chart generated (not required but OK)")
                    test_result["success"] = True
                else:
                    test_result["success"] = True
                    logger.info(f"✓ Query successful")
                
                # Check value accuracy if expected_value provided
                if expected_value is not None:
                    # Try to extract numeric value from answer
                    answer_text = test_result["answer"]
                    # Simple numeric extraction (can be improved)
                    import re
                    numbers = re.findall(r'\d+\.?\d*', answer_text)
                    if numbers:
                        answer_value = float(numbers[0])
                        # Allow 1% tolerance
                        tolerance = abs(expected_value * 0.01) if expected_value != 0 else 0.01
                        if abs(answer_value - expected_value) <= tolerance:
                            logger.info(f"✓ Value matches: {answer_value} ≈ {expected_value}")
                        else:
                            logger.warning(f"⚠️  Value mismatch: {answer_value} vs {expected_value}")
                            test_result["error"] = f"Value mismatch: {answer_value} vs {expected_value}"
                            test_result["success"] = False
            
            # Log chart config if present
            if test_result["has_chart"]:
                chart_config = result.get("chart_config", {})
                logger.info(f"✓ Chart generated: {chart_config.get('chart_type', 'unknown')} chart")
                logger.info(f"  Labels: {len(chart_config.get('data', {}).get('labels', []))} points")
            
        except Exception as e:
            test_result["error"] = str(e)
            test_result["success"] = False
            logger.error(f"❌ Exception: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Update results
        if test_result["success"]:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1
            self.results["errors"].append({
                "question": question,
                "error": test_result["error"]
            })
        
        self.results["test_results"].append(test_result)
        
        return test_result
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("="*80)
        logger.info("Starting Comprehensive Agent Query Tests")
        logger.info("="*80)
        
        # Test example queries
        logger.info("\n📋 Testing Example Queries...")
        examples = await self.get_example_queries()
        for example in examples:
            await self.test_query(
                question=example["question"],
                expects_chart=example["expects_chart"],
                category=example["category"]
            )
            await asyncio.sleep(1)  # Rate limiting
        
        # Test question generator questions
        logger.info("\n📋 Testing Question Generator Questions...")
        qa_questions = await self.get_question_generator_questions()
        logger.info(f"Found {len(qa_questions)} verified questions")
        
        for qa in qa_questions[:20]:  # Test first 20 to avoid timeout
            await self.test_query(
                question=qa["question"],
                file_id=qa.get("file_id"),
                expects_chart=qa.get("expects_chart", False),
                expected_value=qa.get("expected_answer"),
                category=qa.get("type", "unknown")
            )
            await asyncio.sleep(1)  # Rate limiting
        
        # Print summary
        self.print_summary()
        
        # Save results
        self.save_results()
    
    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Total Tests: {self.results['total_tests']}")
        logger.info(f"Passed: {self.results['passed']} ({self.results['passed']/self.results['total_tests']*100:.1f}%)")
        logger.info(f"Failed: {self.results['failed']} ({self.results['failed']/self.results['total_tests']*100:.1f}%)")
        
        if self.results["errors"]:
            logger.info("\n❌ Failed Tests:")
            for error in self.results["errors"][:10]:  # Show first 10
                logger.info(f"  - {error['question']}: {error['error']}")
    
    def save_results(self):
        """Save test results to JSON file"""
        output_file = Path(__file__).parent / "agent_test_results_comprehensive.json"
        
        # Clean results for JSON
        clean_results = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": self.results["total_tests"],
            "passed": self.results["passed"],
            "failed": self.results["failed"],
            "success_rate": self.results["passed"] / self.results["total_tests"] if self.results["total_tests"] > 0 else 0,
            "errors": self.results["errors"],
            "test_results": []
        }
        
        for tr in self.results["test_results"]:
            clean_tr = {
                "question": tr["question"],
                "category": tr["category"],
                "success": tr["success"],
                "has_chart": tr["has_chart"],
                "expects_chart": tr["expects_chart"],
                "tools_called": tr["tools_called"],
                "latency_ms": tr["latency_ms"],
                "error": tr.get("error")
            }
            clean_results["test_results"].append(clean_tr)
        
        with open(output_file, "w") as f:
            json.dump(clean_results, f, indent=2)
        
        logger.info(f"\n📄 Results saved to: {output_file}")


async def main():
    """Main test runner"""
    # Initialize database connection
    await connect_to_mongodb()
    
    # Get user_id from environment or use default test user
    user_id = os.getenv("TEST_USER_ID", "69366c8393481cfdf197af6a")
    
    if not user_id:
        logger.error("TEST_USER_ID environment variable not set")
        return
    
    tester = AgentQueryTester(user_id)
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

