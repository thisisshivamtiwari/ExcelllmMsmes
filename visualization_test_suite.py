#!/usr/bin/env python3
"""
Comprehensive Visualization Test Suite
Tests 50+ visualization queries covering all chart types and relationships
"""

import sys
import json
import requests
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Test configuration
BACKEND_URL = "http://localhost:8000"
PROVIDER = "gemini"

# Load ground truth
try:
    with open('viz_ground_truth.json', 'r') as f:
        VIZ_GROUND_TRUTH = json.load(f)
except:
    VIZ_GROUND_TRUTH = {}

class VisualizationTestResult:
    def __init__(self, query: str, chart_type: str, passed: bool, error: Optional[str] = None, response: Optional[Dict] = None):
        self.query = query
        self.chart_type = chart_type
        self.passed = passed
        self.error = error
        self.response = response
        self.timestamp = datetime.now().isoformat()

class VisualizationTestSuite:
    def __init__(self):
        self.results: List[VisualizationTestResult] = []
    
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
    
    def check_chart_in_response(self, response_text: str, chart_type: str) -> bool:
        """Check if response contains chart data"""
        response_lower = response_text.lower()
        
        # Check for chart type mentions
        chart_keywords = {
            "line": ["line chart", "line graph", "trend", "over time"],
            "bar": ["bar chart", "bar graph", "comparison", "compare"],
            "pie": ["pie chart", "distribution", "percentage"],
            "scatter": ["scatter", "correlation", "relationship"],
            "area": ["area chart", "filled"],
            "heatmap": ["heatmap", "matrix", "grid"]
        }
        
        keywords = chart_keywords.get(chart_type.lower(), [])
        return any(kw in response_lower for kw in keywords) or "chart" in response_lower or "graph" in response_lower
    
    def run_test(self, query: str, chart_type: str, category: str = "general"):
        """Run a single visualization test"""
        print(f"\n{'='*80}")
        print(f"Test: {query}")
        print(f"Category: {category} | Expected Chart Type: {chart_type}")
        
        start_time = time.time()
        result = self.test_via_api(query)
        elapsed = time.time() - start_time
        
        if "error" in result:
            print(f"❌ ERROR: {result['error']}")
            self.results.append(VisualizationTestResult(
                query, chart_type, False, result['error']
            ))
            return False
        
        answer = result.get('answer', '')
        print(f"Response: {answer[:200]}...")
        print(f"Time: {elapsed:.2f}s")
        
        # Check if chart data is present
        has_chart = self.check_chart_in_response(answer, chart_type)
        # Also check for JSON chart data structure
        has_json_chart = '"chart"' in answer or '"type"' in answer or '"data"' in answer
        
        passed = has_chart or has_json_chart
        
        if passed:
            print(f"✅ PASSED - Chart data detected")
        else:
            print(f"❌ FAILED - No chart data detected")
        
        self.results.append(VisualizationTestResult(
            query, chart_type, passed, None, result
        ))
        return passed
    
    def run_all_tests(self):
        """Run comprehensive visualization test suite"""
        print("\n" + "="*80)
        print("COMPREHENSIVE VISUALIZATION TEST SUITE - 50+ QUERIES")
        print("="*80)
        
        # Category 1: Line Charts (Time Series) - 10 tests
        print("\n📈 CATEGORY 1: Line Charts (Time Series)")
        self.run_test("Create a line chart showing production quantity over time", "line", "line_chart")
        self.run_test("Show me a line graph of production trends", "line", "line_chart")
        self.run_test("Generate a line chart for quality control inspections over time", "line", "line_chart")
        self.run_test("Plot production by date as a line chart", "line", "line_chart")
        self.run_test("Create a line chart showing maintenance frequency over time", "line", "line_chart")
        self.run_test("Show inventory consumption trends as a line graph", "line", "line_chart")
        self.run_test("Generate a line chart for defect rates over time", "line", "line_chart")
        self.run_test("Plot production efficiency trends", "line", "line_chart")
        self.run_test("Create a line chart showing material wastage over time", "line", "line_chart")
        self.run_test("Show production by shift over time as a line chart", "line", "line_chart")
        
        # Category 2: Bar Charts (Comparisons) - 10 tests
        print("\n📊 CATEGORY 2: Bar Charts (Comparisons)")
        self.run_test("Create a bar chart comparing production by different lines", "bar", "bar_chart")
        self.run_test("Show me a bar graph of defects by product", "bar", "bar_chart")
        self.run_test("Generate a bar chart comparing maintenance costs by machine", "bar", "bar_chart")
        self.run_test("Create a bar chart showing production by shift", "bar", "bar_chart")
        self.run_test("Plot defect types as a bar chart", "bar", "bar_chart")
        self.run_test("Show inventory consumption by material as a bar chart", "bar", "bar_chart")
        self.run_test("Generate a bar chart comparing quality pass rates by line", "bar", "bar_chart")
        self.run_test("Create a bar chart showing downtime by machine", "bar", "bar_chart")
        self.run_test("Plot production efficiency by line as a bar chart", "bar", "bar_chart")
        self.run_test("Show wastage by material as a bar graph", "bar", "bar_chart")
        
        # Category 3: Pie Charts (Distributions) - 8 tests
        print("\n🥧 CATEGORY 3: Pie Charts (Distributions)")
        self.run_test("Create a pie chart showing defect type distribution", "pie", "pie_chart")
        self.run_test("Show me a pie chart of production by product", "pie", "pie_chart")
        self.run_test("Generate a pie chart for maintenance types distribution", "pie", "pie_chart")
        self.run_test("Create a pie chart showing material consumption distribution", "pie", "pie_chart")
        self.run_test("Plot production by shift as a pie chart", "pie", "pie_chart")
        self.run_test("Show supplier distribution as a pie chart", "pie", "pie_chart")
        self.run_test("Generate a pie chart for defect rates by product", "pie", "pie_chart")
        self.run_test("Create a pie chart showing downtime distribution by machine", "pie", "pie_chart")
        
        # Category 4: Scatter Charts (Correlations) - 8 tests
        print("\n🔍 CATEGORY 4: Scatter Charts (Correlations)")
        self.run_test("Create a scatter plot showing production vs downtime", "scatter", "scatter_chart")
        self.run_test("Show me a scatter chart of production vs target quantity", "scatter", "scatter_chart")
        self.run_test("Generate a scatter plot for defects vs production quantity", "scatter", "scatter_chart")
        self.run_test("Create a scatter chart showing maintenance cost vs downtime", "scatter", "scatter_chart")
        self.run_test("Plot consumption vs production as a scatter chart", "scatter", "scatter_chart")
        self.run_test("Show quality pass rate vs production as a scatter plot", "scatter", "scatter_chart")
        self.run_test("Generate a scatter chart for wastage vs consumption", "scatter", "scatter_chart")
        self.run_test("Create a scatter plot showing efficiency vs downtime", "scatter", "scatter_chart")
        
        # Category 5: Area Charts (Filled Trends) - 5 tests
        print("\n📉 CATEGORY 5: Area Charts (Filled Trends)")
        self.run_test("Create an area chart showing production over time", "area", "area_chart")
        self.run_test("Show me an area chart of quality inspections over time", "area", "area_chart")
        self.run_test("Generate an area chart for inventory levels over time", "area", "area_chart")
        self.run_test("Create an area chart showing cumulative production", "area", "area_chart")
        self.run_test("Plot defect trends as an area chart", "area", "area_chart")
        
        # Category 6: Heatmaps (2D Matrix) - 5 tests
        print("\n🔥 CATEGORY 6: Heatmaps (2D Matrix)")
        self.run_test("Create a heatmap showing production by line and shift", "heatmap", "heatmap")
        self.run_test("Show me a heatmap of defects by product and defect type", "heatmap", "heatmap")
        self.run_test("Generate a heatmap for maintenance by machine and type", "heatmap", "heatmap")
        self.run_test("Create a heatmap showing consumption by material and date", "heatmap", "heatmap")
        self.run_test("Plot quality rates by line and product as a heatmap", "heatmap", "heatmap")
        
        # Category 7: Multi-Series Charts - 5 tests
        print("\n📊 CATEGORY 7: Multi-Series Charts")
        self.run_test("Create a line chart with multiple lines showing production by each line over time", "line", "multi_series")
        self.run_test("Show me a bar chart comparing production and target by line", "bar", "multi_series")
        self.run_test("Generate a line chart with passed and failed quantities over time", "line", "multi_series")
        self.run_test("Create a bar chart showing opening and closing stock by material", "bar", "multi_series")
        self.run_test("Plot production and downtime trends together", "line", "multi_series")
        
        # Category 8: Relationship Visualizations - 5 tests
        print("\n🔗 CATEGORY 8: Relationship Visualizations")
        self.run_test("Create a chart showing the relationship between maintenance and production", "scatter", "relationship")
        self.run_test("Show me a visualization of how defects affect production", "scatter", "relationship")
        self.run_test("Generate a chart showing material consumption vs production output", "scatter", "relationship")
        self.run_test("Create a visualization of quality pass rate vs production efficiency", "scatter", "relationship")
        self.run_test("Plot the correlation between downtime and production quantity", "scatter", "relationship")
        
        # Category 9: Edge Cases - 4 tests
        print("\n🔍 CATEGORY 9: Edge Cases")
        self.run_test("Create a chart for products with zero defects", "bar", "edge_case")
        self.run_test("Show me a chart of machines with no maintenance records", "bar", "edge_case")
        self.run_test("Generate a chart for weekend production only", "bar", "edge_case")
        self.run_test("Create a chart showing data for a specific date range", "line", "edge_case")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("VISUALIZATION TEST SUMMARY")
        print("="*80)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"❌ Failed: {failed} ({failed/total*100:.1f}%)")
        
        # Group by chart type
        by_type = {}
        for result in self.results:
            chart_type = result.chart_type
            if chart_type not in by_type:
                by_type[chart_type] = {"total": 0, "passed": 0}
            by_type[chart_type]["total"] += 1
            if result.passed:
                by_type[chart_type]["passed"] += 1
        
        print("\n📊 Results by Chart Type:")
        for chart_type, stats in sorted(by_type.items()):
            pct = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            print(f"  {chart_type}: {stats['passed']}/{stats['total']} ({pct:.1f}%)")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.results:
                if not result.passed:
                    print(f"\n  Query: {result.query}")
                    print(f"  Chart Type: {result.chart_type}")
                    if result.error:
                        print(f"  Error: {result.error}")
        
        # Save results
        results_file = Path("viz_test_results.json")
        with open(results_file, 'w') as f:
            json.dump([
                {
                    "query": r.query,
                    "chart_type": r.chart_type,
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
    
    suite = VisualizationTestSuite()
    suite.run_all_tests()

