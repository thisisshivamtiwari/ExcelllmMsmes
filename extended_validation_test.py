#!/usr/bin/env python3
"""
Extended Validation Test - 30+ Additional Queries
Tests complex scenarios, KPIs, and all relationships
"""

import requests
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import time
import re

BACKEND_URL = "http://localhost:8000/api"
PROVIDER = "gemini"
DATA_DIR = Path("uploaded_files")

class ExtendedValidator:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.load_data()
        
    def load_data(self):
        """Load all CSV files"""
        print("📊 Loading data files...")
        self.dfs = {}
        
        for csv_file in DATA_DIR.glob("*.csv"):
            try:
                df = pd.read_csv(csv_file)
                if 'Actual_Qty' in df.columns:
                    self.dfs['production'] = df
                elif 'Failed_Qty' in df.columns:
                    self.dfs['quality'] = df
                elif 'Downtime_Hours' in df.columns:
                    self.dfs['maintenance'] = df
                elif 'Consumption_Kg' in df.columns:
                    self.dfs['inventory'] = df
            except:
                pass
        
        print(f"✅ Loaded {len(self.dfs)} data files")
    
    def test_query(self, query, expected_type="text", validation_fn=None):
        """Test a single query"""
        print(f"\n{'='*80}")
        print(f"🔍 Query: {query}")
        
        try:
            response = requests.post(
                f"{BACKEND_URL}/agent/query",
                json={"question": query, "provider": PROVIDER},
                timeout=120
            )
            
            if response.status_code != 200:
                print(f"❌ FAILED - HTTP {response.status_code}")
                self.failed += 1
                return False
            
            data = response.json()
            answer = data.get('answer', '')
            
            print(f"💬 Response: {answer[:150]}...")
            
            # Validate based on type
            if expected_type == "graph":
                if 'chart_type' in answer and 'data' in answer:
                    print("✅ PASSED - Chart generated")
                    self.passed += 1
                    return True
                else:
                    print("❌ FAILED - No chart data")
                    self.failed += 1
                    return False
            
            elif validation_fn:
                if validation_fn(answer):
                    print("✅ PASSED - Validation successful")
                    self.passed += 1
                    return True
                else:
                    print("❌ FAILED - Validation failed")
                    self.failed += 1
                    return False
            
            else:
                if len(answer) > 20 and data.get('success'):
                    print("✅ PASSED - Got valid response")
                    self.passed += 1
                    return True
                else:
                    print("❌ FAILED - Invalid response")
                    self.failed += 1
                    return False
                    
        except Exception as e:
            print(f"❌ FAILED - Error: {str(e)[:100]}")
            self.failed += 1
            return False
    
    def run_extended_tests(self):
        """Run extended test suite"""
        print("\n" + "="*80)
        print("🚀 EXTENDED VALIDATION TEST SUITE - 30+ QUERIES")
        print("="*80)
        
        # KPI Calculations
        print("\n\n📁 CATEGORY: KPI CALCULATIONS")
        print("-" * 80)
        
        self.test_query("Calculate OEE for all machines")
        time.sleep(3)
        
        self.test_query("What is the First Pass Yield for each product?")
        time.sleep(3)
        
        self.test_query("Calculate defect rate by product")
        time.sleep(3)
        
        self.test_query("What is the overall equipment effectiveness?")
        time.sleep(3)
        
        # Trend Analysis
        print("\n\n📁 CATEGORY: TREND ANALYSIS")
        print("-" * 80)
        
        self.test_query("Show production trends over the last 30 days")
        time.sleep(3)
        
        self.test_query("What is the trend in material wastage?")
        time.sleep(3)
        
        self.test_query("Show defect trends by week")
        time.sleep(3)
        
        self.test_query("Analyze maintenance cost trends over time")
        time.sleep(3)
        
        # Comparative Analysis
        print("\n\n📁 CATEGORY: COMPARATIVE ANALYSIS")
        print("-" * 80)
        
        self.test_query("Compare production efficiency across all lines")
        time.sleep(3)
        
        self.test_query("Which line has the best quality performance?")
        time.sleep(3)
        
        self.test_query("Compare downtime across all machines")
        time.sleep(3)
        
        self.test_query("Which shift produces the most output?")
        time.sleep(3)
        
        # Graph Generation - All Types
        print("\n\n📁 CATEGORY: GRAPH GENERATION (ALL TYPES)")
        print("-" * 80)
        
        self.test_query("Show production actual vs target as grouped bar chart", expected_type="graph")
        time.sleep(3)
        
        self.test_query("Display production by shift as a pie chart", expected_type="graph")
        time.sleep(3)
        
        self.test_query("Create an area chart of weekly production trends", expected_type="graph")
        time.sleep(3)
        
        self.test_query("Show quality metrics by inspector as a radar chart", expected_type="graph")
        time.sleep(3)
        
        self.test_query("Display maintenance cost vs downtime as scatter plot", expected_type="graph")
        time.sleep(3)
        
        # Cross-File Complex Queries
        print("\n\n📁 CATEGORY: CROSS-FILE COMPLEX QUERIES")
        print("-" * 80)
        
        self.test_query("Which products consume the most materials relative to their production?")
        time.sleep(3)
        
        self.test_query("Show the correlation between machine downtime and production output")
        time.sleep(3)
        
        self.test_query("Which lines have both high production and high quality?")
        time.sleep(3)
        
        self.test_query("What is the impact of maintenance on production efficiency?")
        time.sleep(3)
        
        # Time-Based Queries
        print("\n\n📁 CATEGORY: TIME-BASED QUERIES")
        print("-" * 80)
        
        self.test_query("What was the production in November 2025?")
        time.sleep(3)
        
        self.test_query("Compare production between morning and afternoon shifts")
        time.sleep(3)
        
        self.test_query("Show monthly production totals")
        time.sleep(3)
        
        # Aggregation Queries
        print("\n\n📁 CATEGORY: AGGREGATION QUERIES")
        print("-" * 80)
        
        self.test_query("What is the total target quantity vs actual quantity?")
        time.sleep(3)
        
        self.test_query("Calculate total rework count across all products")
        time.sleep(3)
        
        self.test_query("Sum of all maintenance costs by machine")
        time.sleep(3)
        
        # Edge Cases & Complex Scenarios
        print("\n\n📁 CATEGORY: EDGE CASES & COMPLEX SCENARIOS")
        print("-" * 80)
        
        self.test_query("What products have zero defects?")
        time.sleep(3)
        
        self.test_query("Which machines never had breakdowns?")
        time.sleep(3)
        
        self.test_query("Show materials with highest wastage percentage")
        time.sleep(3)
        
        # Generate report
        self.generate_final_report()
    
    def generate_final_report(self):
        """Generate final comprehensive report"""
        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0
        
        print("\n\n" + "="*80)
        print("📊 EXTENDED VALIDATION TEST REPORT")
        print("="*80)
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"Success Rate: {success_rate:.1f}%")
        print("="*80)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "provider": PROVIDER,
            "test_type": "Extended Validation",
            "summary": {
                "total": total,
                "passed": self.passed,
                "failed": self.failed,
                "success_rate": round(success_rate, 2)
            }
        }
        
        with open('extended_validation_results.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Results saved to: extended_validation_results.json")
        
        if success_rate >= 90:
            print("\n🎉 EXCELLENT! System is production-ready!")
            print("✅ 90%+ success rate achieved")
            print("\n🎯 You can now confidently use the system!")
        else:
            print(f"\n⚠️ Success rate: {success_rate:.1f}% (Target: 90%+)")

def main():
    validator = ExtendedValidator()
    validator.run_extended_tests()

if __name__ == "__main__":
    main()

