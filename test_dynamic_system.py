"""
Test Dynamic System - Validate calculations and visualizations
"""

import sys
import json
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

# Test configuration
API_BASE_URL = "http://localhost:8000/api"
DATA_DIR = Path(__file__).parent / "datagenerator" / "generated_data"

class DynamicSystemTester:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "accuracy": 0.0
            }
        }
    
    def test_api_health(self):
        """Test if API is running"""
        print("\n🔍 Testing API Health...")
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                print("✅ API is running")
                return True
            else:
                print(f"❌ API returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API is not accessible: {e}")
            return False
    
    def test_dynamic_visualizations(self):
        """Test dynamic visualization endpoint"""
        print("\n🔍 Testing Dynamic Visualizations API...")
        try:
            response = requests.get(f"{API_BASE_URL}/visualizations/data/all", timeout=30)
            
            if response.status_code != 200:
                print(f"❌ API returned status {response.status_code}")
                return False
            
            data = response.json()
            
            if not data.get("success"):
                print("❌ API returned success=false")
                return False
            
            visualizations = data.get("visualizations", {})
            
            if not visualizations:
                print("❌ No visualizations returned")
                return False
            
            print(f"✅ Received visualizations for {len(visualizations)} files")
            
            # Validate each file's visualizations
            for file_name, file_data in visualizations.items():
                print(f"\n  📊 {file_name}:")
                print(f"     - Rows: {file_data.get('row_count', 0)}")
                print(f"     - Columns: {file_data.get('column_count', 0)}")
                print(f"     - Charts: {len(file_data.get('charts', []))}")
                print(f"     - Metrics: {len(file_data.get('metrics', {}))}")
                
                # Validate charts
                charts = file_data.get('charts', [])
                for chart in charts:
                    if not all(k in chart for k in ['type', 'title', 'data']):
                        print(f"     ❌ Invalid chart structure: {chart.get('title', 'Unknown')}")
                        return False
                    print(f"     ✅ {chart['type'].upper()} chart: {chart['title']}")
                
                # Validate metrics
                metrics = file_data.get('metrics', {})
                for metric_name, metric_data in metrics.items():
                    if not all(k in metric_data for k in ['value', 'formula']):
                        print(f"     ❌ Invalid metric structure: {metric_name}")
                        return False
                    print(f"     ✅ Metric: {metric_name} = {metric_data['value']} ({metric_data['formula']})")
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing visualizations: {e}")
            return False
    
    def validate_dynamic_calculations(self):
        """Validate that calculations are accurate"""
        print("\n🔍 Validating Dynamic Calculations...")
        
        try:
            # Get visualizations from API
            response = requests.get(f"{API_BASE_URL}/visualizations/data/all", timeout=30)
            data = response.json()
            visualizations = data.get("visualizations", {})
            
            all_valid = True
            
            # Test production_logs calculations
            if 'production_logs' in visualizations:
                print("\n  📊 Validating production_logs calculations...")
                df = pd.read_csv(DATA_DIR / "production_logs.csv")
                
                metrics = visualizations['production_logs'].get('metrics', {})
                
                # Validate efficiency calculation
                if 'efficiency' in metrics:
                    api_efficiency = metrics['efficiency']['value']
                    
                    # Calculate ground truth
                    if 'Target_Qty' in df.columns and 'Actual_Qty' in df.columns:
                        actual_efficiency = (df['Actual_Qty'].sum() / df['Target_Qty'].sum() * 100)
                        
                        diff = abs(api_efficiency - actual_efficiency)
                        if diff < 0.1:  # Within 0.1% tolerance
                            print(f"     ✅ Efficiency: {api_efficiency}% (Ground truth: {actual_efficiency:.2f}%)")
                        else:
                            print(f"     ❌ Efficiency mismatch: API={api_efficiency}%, Actual={actual_efficiency:.2f}%")
                            all_valid = False
                
                # Validate total quantity
                if 'total_quantity' in metrics:
                    api_total = metrics['total_quantity']['value']
                    
                    # Find quantity column dynamically
                    qty_cols = [col for col in df.columns if 'qty' in col.lower() or 'quantity' in col.lower()]
                    if qty_cols:
                        actual_total = df[qty_cols[0]].sum()
                        
                        diff = abs(api_total - actual_total)
                        if diff < 1:  # Within 1 unit tolerance
                            print(f"     ✅ Total Quantity: {api_total} (Ground truth: {actual_total})")
                        else:
                            print(f"     ❌ Total Quantity mismatch: API={api_total}, Actual={actual_total}")
                            all_valid = False
            
            # Test quality_control calculations
            if 'quality_control' in visualizations:
                print("\n  📊 Validating quality_control calculations...")
                df = pd.read_csv(DATA_DIR / "quality_control.csv")
                
                metrics = visualizations['quality_control'].get('metrics', {})
                
                # Validate total inspected
                if 'total_quantity' in metrics:
                    api_total = metrics['total_quantity']['value']
                    
                    if 'Inspected_Qty' in df.columns:
                        actual_total = df['Inspected_Qty'].sum()
                        
                        diff = abs(api_total - actual_total)
                        if diff < 1:
                            print(f"     ✅ Total Inspected: {api_total} (Ground truth: {actual_total})")
                        else:
                            print(f"     ❌ Total Inspected mismatch: API={api_total}, Actual={actual_total}")
                            all_valid = False
            
            # Test maintenance_logs calculations
            if 'maintenance_logs' in visualizations:
                print("\n  📊 Validating maintenance_logs calculations...")
                df = pd.read_csv(DATA_DIR / "maintenance_logs.csv")
                
                metrics = visualizations['maintenance_logs'].get('metrics', {})
                
                # Validate total cost
                if 'total_cost' in metrics:
                    api_cost = metrics['total_cost']['value']
                    
                    if 'Cost_Rupees' in df.columns:
                        actual_cost = df['Cost_Rupees'].sum()
                        
                        diff = abs(api_cost - actual_cost)
                        if diff < 1:
                            print(f"     ✅ Total Cost: ₹{api_cost} (Ground truth: ₹{actual_cost})")
                        else:
                            print(f"     ❌ Total Cost mismatch: API=₹{api_cost}, Actual=₹{actual_cost}")
                            all_valid = False
            
            # Test inventory_logs calculations
            if 'inventory_logs' in visualizations:
                print("\n  📊 Validating inventory_logs calculations...")
                df = pd.read_csv(DATA_DIR / "inventory_logs.csv")
                
                metrics = visualizations['inventory_logs'].get('metrics', {})
                
                # Validate total quantity (opening stock)
                if 'total_quantity' in metrics:
                    api_total = metrics['total_quantity']['value']
                    
                    if 'Opening_Stock_Kg' in df.columns:
                        actual_total = df['Opening_Stock_Kg'].sum()
                        
                        diff = abs(api_total - actual_total)
                        if diff < 1:
                            print(f"     ✅ Total Opening Stock: {api_total} kg (Ground truth: {actual_total} kg)")
                        else:
                            print(f"     ❌ Total Opening Stock mismatch: API={api_total}, Actual={actual_total}")
                            all_valid = False
            
            return all_valid
            
        except Exception as e:
            print(f"❌ Error validating calculations: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 80)
        print("🚀 DYNAMIC SYSTEM TEST SUITE")
        print("=" * 80)
        
        tests = [
            ("API Health Check", self.test_api_health),
            ("Dynamic Visualizations API", self.test_dynamic_visualizations),
            ("Dynamic Calculations Validation", self.validate_dynamic_calculations)
        ]
        
        for test_name, test_func in tests:
            self.results["summary"]["total"] += 1
            try:
                result = test_func()
                if result:
                    self.results["summary"]["passed"] += 1
                    self.results["tests"].append({
                        "name": test_name,
                        "status": "PASSED",
                        "error": None
                    })
                else:
                    self.results["summary"]["failed"] += 1
                    self.results["tests"].append({
                        "name": test_name,
                        "status": "FAILED",
                        "error": "Test returned False"
                    })
            except Exception as e:
                self.results["summary"]["failed"] += 1
                self.results["tests"].append({
                    "name": test_name,
                    "status": "FAILED",
                    "error": str(e)
                })
        
        # Calculate accuracy
        if self.results["summary"]["total"] > 0:
            self.results["summary"]["accuracy"] = (self.results["summary"]["passed"] / self.results["summary"]["total"]) * 100
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {self.results['summary']['total']}")
        print(f"✅ Passed: {self.results['summary']['passed']}")
        print(f"❌ Failed: {self.results['summary']['failed']}")
        print(f"🎯 Accuracy: {self.results['summary']['accuracy']:.1f}%")
        print("=" * 80)
        
        # Save results
        results_file = Path(__file__).parent / "dynamic_test_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Results saved to: {results_file}")
        
        return self.results["summary"]["accuracy"] >= 90.0


if __name__ == "__main__":
    tester = DynamicSystemTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

