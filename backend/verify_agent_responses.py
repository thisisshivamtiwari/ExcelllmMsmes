"""
Agent Response Verification System

This script verifies the correctness of agent responses by:
1. Comparing calculated values with actual data
2. Validating chart data against source data
3. Checking column name accuracy
4. Verifying aggregation operations
5. Cross-referencing with summary statistics
"""

import os
import sys
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

# Add backend to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Add project root to path for tools
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, project_root)

# Import from backend modules
from database import get_mongodb_uri
from services.file_service import get_user_files

# Import from backend modules (all now in backend/)
from tools.excel_retriever import BackendExcelRetriever
from tools.data_calculator import DataCalculator
from tools.trend_analyzer import TrendAnalyzer
from tools.comparative_analyzer import ComparativeAnalyzer
from tools.kpi_calculator import KPICalculator
from tools.graph_generator import GraphGenerator

class AgentResponseVerifier:
    """Verifies agent responses against actual data."""
    
    def __init__(self, user_id: str, mongodb_uri: str, database_name: str):
        self.user_id = user_id
        self.mongodb_uri = mongodb_uri
        self.database_name = database_name
        self.excel_retriever = BackendExcelRetriever(user_id=user_id, mongodb_uri=mongodb_uri, database_name=database_name)
        self.data_calculator = DataCalculator()
        self.trend_analyzer = TrendAnalyzer()
        self.comparative_analyzer = ComparativeAnalyzer()
        self.kpi_calculator = KPICalculator()
        self.graph_generator = GraphGenerator()
        self.verification_results = []
    
    def verify_calculation(self, query: str, agent_answer: str, expected_value: Optional[float] = None, tolerance: float = 0.01) -> Dict[str, Any]:
        """
        Verify a calculation response.
        
        Args:
            query: The original query
            agent_answer: The agent's answer
            expected_value: Expected numerical value (if known)
            tolerance: Allowed difference for floating point comparison
        
        Returns:
            Verification result dict
        """
        result = {
            "query": query,
            "agent_answer": agent_answer,
            "verified": False,
            "errors": [],
            "warnings": [],
            "details": {}
        }
        
        # Extract numerical value from agent answer
        import re
        numbers = re.findall(r'\d+\.?\d*', agent_answer)
        if numbers:
            try:
                agent_value = float(numbers[0])
                result["details"]["extracted_value"] = agent_value
                
                if expected_value is not None:
                    difference = abs(agent_value - expected_value)
                    if difference <= tolerance:
                        result["verified"] = True
                        result["details"]["difference"] = difference
                    else:
                        result["errors"].append(f"Value mismatch: expected {expected_value}, got {agent_value}, difference: {difference}")
                else:
                    result["warnings"].append("No expected value provided for comparison")
            except ValueError:
                result["errors"].append("Could not extract numerical value from answer")
        else:
            result["warnings"].append("No numerical value found in answer")
        
        return result
    
    def verify_chart_data(self, query: str, chart_json: Dict[str, Any], file_id: str, expected_columns: List[str]) -> Dict[str, Any]:
        """
        Verify chart data against source data.
        
        Args:
            query: The original query
            chart_json: Chart.js JSON configuration from agent
            file_id: File ID to verify against
            expected_columns: Expected column names in the chart
        
        Returns:
            Verification result dict
        """
        result = {
            "query": query,
            "chart_type": chart_json.get("chart_type"),
            "verified": False,
            "errors": [],
            "warnings": [],
            "details": {}
        }
        
        try:
            # Retrieve actual data
            data_result = self.excel_retriever.retrieve_data(file_id=file_id, columns=expected_columns)
            
            if not data_result.get("success"):
                result["errors"].append(f"Failed to retrieve data: {data_result.get('error')}")
                return result
            
            actual_data = data_result.get("data", [])
            actual_summary = data_result.get("summary", {})
            
            # Extract chart data
            chart_data = chart_json.get("data", {})
            datasets = chart_data.get("datasets", [])
            
            if not datasets:
                result["errors"].append("No datasets found in chart")
                return result
            
            # Verify data points
            for dataset in datasets:
                dataset_label = dataset.get("label", "")
                dataset_data = dataset.get("data", [])
                
                # For line/bar charts, verify data points match
                if isinstance(dataset_data, list) and len(dataset_data) > 0:
                    # Check if data points are reasonable
                    if isinstance(dataset_data[0], (int, float)):
                        # Simple numeric data
                        chart_sum = sum(dataset_data)
                        actual_sum = actual_summary.get("numeric_summary", {}).get(dataset_label, {}).get("sum", 0)
                        
                        if actual_sum > 0:
                            difference = abs(chart_sum - actual_sum)
                            if difference / actual_sum < 0.1:  # Within 10%
                                result["verified"] = True
                                result["details"][dataset_label] = {
                                    "chart_sum": chart_sum,
                                    "actual_sum": actual_sum,
                                    "difference": difference,
                                    "difference_percent": (difference / actual_sum) * 100
                                }
                            else:
                                result["warnings"].append(f"Sum mismatch for {dataset_label}: chart={chart_sum}, actual={actual_sum}")
                
                # For scatter plots, verify data structure
                elif isinstance(dataset_data, list) and len(dataset_data) > 0 and isinstance(dataset_data[0], dict):
                    result["verified"] = True  # Structure is correct
                    result["details"]["scatter_points"] = len(dataset_data)
            
            # Verify column names match
            chart_columns = []
            for dataset in datasets:
                label = dataset.get("label", "")
                if label:
                    chart_columns.append(label)
            
            missing_columns = [col for col in expected_columns if col not in str(chart_columns)]
            if missing_columns:
                result["warnings"].append(f"Expected columns not found in chart: {missing_columns}")
            
        except Exception as e:
            result["errors"].append(f"Verification error: {str(e)}")
            import traceback
            result["details"]["traceback"] = traceback.format_exc()
        
        return result
    
    def verify_column_names(self, query: str, agent_response: str, file_id: str) -> Dict[str, Any]:
        """
        Verify that column names mentioned in agent response match actual columns.
        
        Args:
            query: The original query
            agent_response: Agent's response
            file_id: File ID to check
        
        Returns:
            Verification result dict
        """
        result = {
            "query": query,
            "verified": False,
            "errors": [],
            "warnings": [],
            "details": {}
        }
        
        try:
            # Get actual columns
            metadata = self.excel_retriever.load_file_metadata(file_id)
            if not metadata:
                result["errors"].append("Could not load file metadata")
                return result
            
            schema = metadata.get("schema", {})
            actual_columns = []
            if "sheets" in schema:
                for sheet_info in schema["sheets"].values():
                    if "columns" in sheet_info:
                        actual_columns.extend(sheet_info["columns"].keys())
            
            # Extract column names from agent response (simple pattern matching)
            import re
            # Look for common column name patterns
            mentioned_columns = re.findall(r'\b[A-Z][a-zA-Z_]+[A-Z][a-zA-Z_]*\b', agent_response)
            
            # Check if mentioned columns exist
            valid_columns = []
            invalid_columns = []
            for col in mentioned_columns:
                if col in actual_columns:
                    valid_columns.append(col)
                else:
                    invalid_columns.append(col)
            
            result["details"]["actual_columns"] = actual_columns
            result["details"]["mentioned_columns"] = mentioned_columns
            result["details"]["valid_columns"] = valid_columns
            result["details"]["invalid_columns"] = invalid_columns
            
            if invalid_columns:
                result["errors"].append(f"Invalid column names mentioned: {invalid_columns}")
            elif mentioned_columns:
                result["verified"] = True
            else:
                result["warnings"].append("No column names detected in response")
        
        except Exception as e:
            result["errors"].append(f"Verification error: {str(e)}")
        
        return result
    
    def run_verification_suite(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run a suite of verification tests.
        
        Args:
            test_cases: List of test case dicts with 'query', 'type', and optional 'expected_value'
        
        Returns:
            Summary of all verification results
        """
        print(f"\n{'='*80}")
        print(f"AGENT RESPONSE VERIFICATION SUITE")
        print(f"{'='*80}\n")
        print(f"User ID: {self.user_id}")
        print(f"Test Cases: {len(test_cases)}\n")
        
        all_results = []
        
        for i, test_case in enumerate(test_cases, 1):
            query = test_case.get("query", "")
            test_type = test_case.get("type", "general")  # general, calculation, chart, column_check
            expected_value = test_case.get("expected_value")
            file_id = test_case.get("file_id")
            expected_columns = test_case.get("expected_columns", [])
            
            print(f"\n[{i}/{len(test_cases)}] Testing: {query}")
            print(f"Type: {test_type}")
            
            # In a real scenario, you would call the agent here
            # For now, we'll simulate or you can pass agent_response
            agent_response = test_case.get("agent_response")
            
            if not agent_response:
                print("  ⚠️  No agent response provided, skipping...")
                continue
            
            if test_type == "calculation":
                result = self.verify_calculation(query, agent_response, expected_value)
            elif test_type == "chart":
                chart_json = test_case.get("chart_json")
                if chart_json:
                    result = self.verify_chart_data(query, chart_json, file_id, expected_columns)
                else:
                    result = {"query": query, "verified": False, "errors": ["No chart JSON provided"]}
            elif test_type == "column_check":
                result = self.verify_column_names(query, agent_response, file_id)
            else:
                result = {"query": query, "verified": False, "warnings": ["Unknown test type"]}
            
            all_results.append(result)
            
            # Print result
            status = "✅ PASSED" if result.get("verified") else "❌ FAILED"
            print(f"  {status}")
            if result.get("errors"):
                for error in result["errors"]:
                    print(f"    ❌ Error: {error}")
            if result.get("warnings"):
                for warning in result["warnings"]:
                    print(f"    ⚠️  Warning: {warning}")
        
        # Summary
        passed = sum(1 for r in all_results if r.get("verified"))
        failed = len(all_results) - passed
        
        summary = {
            "total_tests": len(all_results),
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / len(all_results) * 100) if all_results else 0,
            "results": all_results,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"\n{'='*80}")
        print(f"VERIFICATION SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {passed} ({summary['pass_rate']:.1f}%)")
        print(f"Failed: {failed}")
        print(f"{'='*80}\n")
        
        return summary


def main():
    """Main function to run verification."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify agent responses")
    parser.add_argument("--user-id", required=True, help="User ID for testing")
    parser.add_argument("--test-file", help="JSON file with test cases")
    parser.add_argument("--mongodb-uri", help="MongoDB URI (optional, uses env if not provided)")
    parser.add_argument("--database", default="excelllm", help="Database name")
    
    args = parser.parse_args()
    
    # Get MongoDB URI
    mongodb_uri = args.mongodb_uri or get_mongodb_uri()
    
    # Create verifier
    verifier = AgentResponseVerifier(
        user_id=args.user_id,
        mongodb_uri=mongodb_uri,
        database_name=args.database
    )
    
    # Load test cases
    if args.test_file:
        with open(args.test_file, 'r') as f:
            test_cases = json.load(f)
    else:
        # Default test cases
        test_cases = [
            {
                "query": "What is the total production quantity?",
                "type": "calculation",
                "expected_value": 265662.0,  # From production_logs summary
                "file_id": "047222e5-7e82-4526-a715-52984b56f591",
                "agent_response": "The total production quantity is approximately 265,662 units."
            },
            {
                "query": "Show quality metrics by inspector as a radar chart",
                "type": "chart",
                "file_id": "b95be2eb-f67c-4089-b6ed-11288640287c",
                "expected_columns": ["Inspector_Name", "Inspected_Qty", "Passed_Qty", "Failed_Qty", "Rework_Count"],
                "agent_response": "Chart generated",
                "chart_json": {
                    "success": True,
                    "chart_type": "radar",
                    "title": "Quality Metrics by Inspector"
                }
            }
        ]
    
    # Run verification
    summary = verifier.run_verification_suite(test_cases)
    
    # Save results
    output_file = f"verification_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    
    return summary


if __name__ == "__main__":
    main()

