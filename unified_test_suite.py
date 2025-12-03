#!/usr/bin/env python3
"""
Unified Test Suite for ExcelLLM MSME System
Consolidates all testing into one systematic framework
"""

import requests
import json
import time
import sys
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
import re

# Configuration
BACKEND_URL = "http://localhost:8000"
TIMEOUT = 90

# Load ground truth
try:
    with open('ground_truth.json', 'r') as f:
        GROUND_TRUTH = json.load(f)
except FileNotFoundError:
    GROUND_TRUTH = {}

class UnifiedTestSuite:
    """Unified test suite combining all test scenarios"""
    
    def __init__(self, backend_url=BACKEND_URL, provider="gemini"):
        self.backend_url = backend_url
        self.provider = provider
        self.results = []
        self.ground_truth = GROUND_TRUTH
        
    def check_backend(self) -> bool:
        """Check if backend is accessible"""
        try:
            response = requests.get(f"{self.backend_url}/api/files", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def extract_number(self, text: str) -> float:
        """Extract number from text"""
        numbers = re.findall(r'\d+\.?\d*', text.replace(',', ''))
        return float(numbers[0]) if numbers else None
    
    def extract_entity(self, text: str, entities: list) -> str:
        """Extract entity name from text"""
        for entity in entities:
            if entity.lower() in text.lower():
                return entity
        return None
    
    def test_query(self, query: str, category: str, expected_type: str = None, 
                   expected_value: Any = None, tolerance: float = 0.05) -> Dict:
        """Test a single query"""
        print(f"\n[{category}] Testing: {query[:80]}...")
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/agent/query",
                json={"question": query, "provider": self.provider},
                timeout=TIMEOUT
            )
            
            if response.status_code != 200:
                return {
                    "query": query,
                    "category": category,
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "timestamp": datetime.now().isoformat()
                }
            
            data = response.json()
            answer = data.get('answer', '')
            
            # Validation
            passed = False
            message = ""
            
            if expected_type == "number" and expected_value is not None:
                actual = self.extract_number(answer)
                if actual:
                    diff = abs(actual - expected_value) / expected_value if expected_value != 0 else abs(actual)
                    passed = diff <= tolerance
                    message = f"Expected: {expected_value}, Got: {actual}, Diff: {diff*100:.2f}%"
                else:
                    message = "Could not extract number"
            
            elif expected_type in ["product", "line", "machine"]:
                entities = {
                    "product": ['Widget-A', 'Widget-B', 'Widget-C', 'Component-X', 'Component-Y', 'Assembly-Z'],
                    "line": ['Line-1', 'Line-2', 'Line-3'],
                    "machine": ['Machine-M1', 'Machine-M2', 'Machine-M3', 'Machine-M4', 'Machine-M5']
                }
                actual = self.extract_entity(answer, entities.get(expected_type, []))
                passed = actual == expected_value if expected_value else bool(actual)
                message = f"Expected: {expected_value}, Got: {actual}"
            
            else:
                # For other types, check if we got a response
                passed = len(answer) > 20
                message = f"Got response ({len(answer)} chars)"
            
            return {
                "query": query,
                "category": category,
                "success": data.get('success', False) and passed,
                "passed": passed,
                "answer": answer[:200],
                "message": message,
                "provider": data.get('provider'),
                "model": data.get('model_name'),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "query": query,
                "category": category,
                "success": False,
                "error": str(e)[:200],
                "timestamp": datetime.now().isoformat()
            }
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("\n" + "="*80)
        print("UNIFIED TEST SUITE - ExcelLLM MSME System")
        print("="*80)
        print(f"Backend: {self.backend_url}")
        print(f"Provider: {self.provider}")
        print("="*80)
        
        if not self.check_backend():
            print("❌ Backend not accessible!")
            return {"error": "Backend not accessible"}
        
        print("✅ Backend accessible\n")
        
        # Define test suite
        test_cases = self._get_test_cases()
        
        total = len(test_cases)
        passed = 0
        failed = 0
        
        for i, test in enumerate(test_cases, 1):
            print(f"\n[{i}/{total}] ", end="")
            result = self.test_query(**test)
            self.results.append(result)
            
            if result.get('success') or result.get('passed'):
                passed += 1
                print("✅ PASSED")
            else:
                failed += 1
                print("❌ FAILED")
            
            time.sleep(0.5)
        
        # Generate report
        report = self._generate_report(passed, failed, total)
        
        # Save results
        with open('unified_test_results.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total: {total} | ✅ Passed: {passed} | ❌ Failed: {failed}")
        print(f"Success Rate: {passed/total*100:.1f}%")
        print("="*80)
        print("\n📄 Results saved to: unified_test_results.json")
        
        return report
    
    def _get_test_cases(self) -> List[Dict]:
        """Get all test cases"""
        return [
            # Basic Calculations
            {"query": "What is the total production quantity?", "category": "Basic", 
             "expected_type": "number", "expected_value": self.ground_truth.get('total_production', 237525)},
            {"query": "Calculate average production per day", "category": "Basic",
             "expected_type": "number", "expected_value": self.ground_truth.get('avg_production_per_day', 272.39), "tolerance": 0.1},
            {"query": "What is the total material consumption?", "category": "Basic",
             "expected_type": "number", "expected_value": self.ground_truth.get('total_material_consumption', 136428)},
            {"query": "How many maintenance events occurred?", "category": "Basic",
             "expected_type": "number", "expected_value": self.ground_truth.get('total_maintenance_events', 132)},
            
            # Product Analysis
            {"query": "Which product has the most defects?", "category": "Product",
             "expected_type": "product", "expected_value": self.ground_truth.get('product_most_defects', {}).get('product', 'Assembly-Z')},
            {"query": "Which product has highest production?", "category": "Product",
             "expected_type": "product", "expected_value": self.ground_truth.get('product_highest_production', {}).get('product', 'Widget-B')},
            {"query": "What is the defect rate for each product?", "category": "Product"},
            {"query": "Compare production quantities across products", "category": "Product"},
            
            # Trend Analysis
            {"query": "Show production trends over the last month", "category": "Trend"},
            {"query": "What is the material consumption trend?", "category": "Trend"},
            {"query": "Show weekly production trends", "category": "Trend"},
            
            # Comparative Analysis
            {"query": "Compare production efficiency across lines", "category": "Comparative"},
            {"query": "Which line has highest production?", "category": "Comparative",
             "expected_type": "line", "expected_value": self.ground_truth.get('line_highest_production', {}).get('line', 'Line-1')},
            {"query": "Compare downtime across machines", "category": "Comparative"},
            {"query": "Which machine has most maintenance costs?", "category": "Comparative",
             "expected_type": "machine", "expected_value": self.ground_truth.get('maintenance_costs', {}).get('highest_cost_machine', 'Machine-M1')},
            
            # KPI Calculations
            {"query": "Calculate OEE for all machines", "category": "KPI"},
            {"query": "What is First Pass Yield for each product?", "category": "KPI"},
            {"query": "Calculate defect rates by product", "category": "KPI"},
            
            # Cross-File Queries
            {"query": "Which products have high defects and high production?", "category": "Cross-File"},
            {"query": "Show machines with high downtime and maintenance costs", "category": "Cross-File"},
            {"query": "What is the relationship between material consumption and production?", "category": "Cross-File"},
            
            # Edge Cases
            {"query": "Show data for non-existent product XYZ", "category": "Edge Case"},
            {"query": "Calculate for date 2099-12-31", "category": "Edge Case"},
        ]
    
    def _generate_report(self, passed: int, failed: int, total: int) -> Dict:
        """Generate test report"""
        categories = {}
        for result in self.results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'passed': 0, 'failed': 0, 'total': 0}
            categories[cat]['total'] += 1
            if result.get('success') or result.get('passed'):
                categories[cat]['passed'] += 1
            else:
                categories[cat]['failed'] += 1
        
        return {
            "timestamp": datetime.now().isoformat(),
            "provider": self.provider,
            "backend_url": self.backend_url,
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "success_rate": round(passed/total*100, 2)
            },
            "by_category": categories,
            "results": self.results
        }

def main():
    provider = sys.argv[1] if len(sys.argv) > 1 else "gemini"
    suite = UnifiedTestSuite(provider=provider)
    report = suite.run_all_tests()
    
    success_rate = report['summary']['success_rate']
    sys.exit(0 if success_rate >= 90 else 1)

if __name__ == "__main__":
    main()

