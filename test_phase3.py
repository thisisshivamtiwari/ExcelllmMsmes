#!/usr/bin/env python3
"""
Comprehensive Phase 3 Testing Script
Tests semantic search functionality with various queries and edge cases.
"""

import requests
import json
import time
from typing import Dict, List, Any

API_BASE = "http://localhost:8000/api"

class Phase3Tester:
    def __init__(self):
        self.results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }
    
    def test_health(self) -> bool:
        """Test backend health endpoint."""
        try:
            response = requests.get(f"{API_BASE}/health", timeout=5)
            if response.status_code == 200:
                self.results["passed"].append("Backend health check")
                return True
            else:
                self.results["failed"].append(f"Backend health check: Status {response.status_code}")
                return False
        except Exception as e:
            self.results["failed"].append(f"Backend health check: {str(e)}")
            return False
    
    def test_index_stats(self) -> bool:
        """Test index statistics endpoint."""
        try:
            response = requests.get(f"{API_BASE}/semantic/stats", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("available"):
                    stats = data.get("stats", {})
                    doc_count = stats.get("total_documents", 0)
                    self.results["passed"].append(f"Index stats: {doc_count} documents")
                    if doc_count == 0:
                        self.results["warnings"].append("No documents indexed - need to index files first")
                    return True
                else:
                    self.results["failed"].append("Index stats: Vector store not available")
                    return False
            else:
                self.results["failed"].append(f"Index stats: Status {response.status_code}")
                return False
        except Exception as e:
            self.results["failed"].append(f"Index stats: {str(e)}")
            return False
    
    def test_search(self, query: str, n_results: int = 5, file_id: str = None) -> Dict[str, Any]:
        """Test semantic search."""
        try:
            params = {"query": query, "n_results": n_results}
            if file_id:
                params["file_id"] = file_id
            
            response = requests.post(f"{API_BASE}/semantic/search", params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return {"success": True, "data": data}
            else:
                error_data = response.json() if response.content else {}
                return {"success": False, "error": error_data.get("detail", f"Status {response.status_code}")}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_basic_tests(self):
        """Run basic functionality tests."""
        print("\n" + "="*60)
        print("BASIC FUNCTIONALITY TESTS")
        print("="*60)
        
        # Test 1: Health check
        print("\n1. Testing backend health...")
        if self.test_health():
            print("   ✅ Backend is healthy")
        else:
            print("   ❌ Backend health check failed")
            return False
        
        # Test 2: Index stats
        print("\n2. Testing index statistics...")
        if self.test_index_stats():
            print("   ✅ Index stats retrieved")
        else:
            print("   ❌ Index stats failed")
            return False
        
        return True
    
    def run_search_tests(self):
        """Run semantic search tests with various queries."""
        print("\n" + "="*60)
        print("SEMANTIC SEARCH TESTS")
        print("="*60)
        
        test_queries = [
            ("production", "Should find production-related columns"),
            ("quality", "Should find quality control columns"),
            ("inventory", "Should find inventory columns"),
            ("date", "Should find date columns"),
            ("efficiency", "Should find efficiency-related columns"),
            ("defect", "Should find defect-related columns"),
            ("material", "Should find material-related columns"),
            ("machine", "Should find machine-related columns"),
            ("batch", "Should find batch-related columns"),
            ("quantity", "Should find quantity-related columns"),
        ]
        
        passed = 0
        failed = 0
        
        for query, description in test_queries:
            print(f"\nTesting: '{query}' - {description}")
            result = self.test_search(query, n_results=5)
            
            if result["success"]:
                data = result["data"]
                columns = data.get("results", {}).get("columns", [])
                relationships = data.get("results", {}).get("relationships", [])
                
                if columns or relationships:
                    print(f"   ✅ Found {len(columns)} columns, {len(relationships)} relationships")
                    if columns:
                        top_result = columns[0]
                        score = top_result.get("relevance_score", 0)
                        print(f"      Top result: {top_result.get('column_name')} (score: {score:.2f})")
                    passed += 1
                    self.results["passed"].append(f"Search query: '{query}'")
                else:
                    print(f"   ⚠️  No results found")
                    self.results["warnings"].append(f"Search query '{query}' returned no results")
                    failed += 1
            else:
                print(f"   ❌ Search failed: {result.get('error')}")
                self.results["failed"].append(f"Search query '{query}': {result.get('error')}")
                failed += 1
            
            time.sleep(0.5)  # Rate limiting
        
        print(f"\n📊 Search Tests Summary: {passed} passed, {failed} failed")
        return failed == 0
    
    def run_edge_case_tests(self):
        """Run edge case tests."""
        print("\n" + "="*60)
        print("EDGE CASE TESTS")
        print("="*60)
        
        edge_cases = [
            ("", "Empty query"),
            ("   ", "Whitespace only"),
            ("nonexistent_column_xyz_123", "Non-existent column"),
            ("a", "Single character"),
            ("production efficiency quality control inventory management", "Very long query"),
            ("!@#$%^&*()", "Special characters only"),
        ]
        
        passed = 0
        failed = 0
        
        for query, description in edge_cases:
            print(f"\nTesting: {description} - '{query}'")
            result = self.test_search(query.strip(), n_results=5)
            
            if result["success"]:
                data = result["data"]
                # Empty queries should be handled gracefully
                if not query.strip():
                    print("   ✅ Empty query handled gracefully")
                    passed += 1
                else:
                    # Other edge cases should return empty results or handle gracefully
                    columns = data.get("results", {}).get("columns", [])
                    print(f"   ✅ Handled gracefully (returned {len(columns)} results)")
                    passed += 1
                    self.results["passed"].append(f"Edge case: {description}")
            else:
                error = result.get("error", "")
                # Some errors are expected for edge cases
                if "required" in error.lower() or "invalid" in error.lower():
                    print(f"   ✅ Properly rejected invalid input")
                    passed += 1
                else:
                    print(f"   ⚠️  Unexpected error: {error}")
                    self.results["warnings"].append(f"Edge case '{description}': {error}")
                    failed += 1
            
            time.sleep(0.5)
        
        print(f"\n📊 Edge Case Tests Summary: {passed} passed, {failed} failed")
        return failed == 0
    
    def run_performance_tests(self):
        """Run performance tests."""
        print("\n" + "="*60)
        print("PERFORMANCE TESTS")
        print("="*60)
        
        queries = ["production", "quality", "inventory"]
        times = []
        
        for query in queries:
            print(f"\nTesting performance for: '{query}'")
            start_time = time.time()
            result = self.test_search(query, n_results=10)
            elapsed = time.time() - start_time
            
            if result["success"]:
                times.append(elapsed)
                print(f"   ✅ Response time: {elapsed:.2f}s")
                self.results["passed"].append(f"Performance test '{query}': {elapsed:.2f}s")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.results["failed"].append(f"Performance test '{query}' failed")
            
            time.sleep(0.5)
        
        if times:
            avg_time = sum(times) / len(times)
            max_time = max(times)
            min_time = min(times)
            
            print(f"\n📊 Performance Summary:")
            print(f"   Average: {avg_time:.2f}s")
            print(f"   Min: {min_time:.2f}s")
            print(f"   Max: {max_time:.2f}s")
            
            if avg_time < 2.0:
                print("   ✅ Performance is good (< 2s average)")
            elif avg_time < 5.0:
                print("   ⚠️  Performance is acceptable (< 5s average)")
                self.results["warnings"].append(f"Average response time is {avg_time:.2f}s")
            else:
                print("   ❌ Performance needs improvement (> 5s average)")
                self.results["failed"].append(f"Average response time too slow: {avg_time:.2f}s")
        
        return True
    
    def run_relevance_tests(self):
        """Test relevance scoring."""
        print("\n" + "="*60)
        print("RELEVANCE SCORING TESTS")
        print("="*60)
        
        # Test queries that should have high relevance
        high_relevance_queries = [
            ("production", ["production", "Production", "PRODUCTION"]),
            ("quality", ["quality", "Quality", "QUALITY"]),
            ("inventory", ["inventory", "Inventory", "INVENTORY"]),
        ]
        
        passed = 0
        failed = 0
        
        for query, expected_keywords in high_relevance_queries:
            print(f"\nTesting relevance for: '{query}'")
            result = self.test_search(query, n_results=10)
            
            if result["success"]:
                columns = result["data"].get("results", {}).get("columns", [])
                
                if columns:
                    # Check if top results contain expected keywords
                    top_3 = columns[:3]
                    relevant_count = 0
                    
                    for col in top_3:
                        col_name = col.get("column_name", "").lower()
                        description = col.get("description", "").lower()
                        
                        if any(keyword.lower() in col_name or keyword.lower() in description 
                               for keyword in expected_keywords):
                            relevant_count += 1
                    
                    relevance_pct = (relevant_count / len(top_3)) * 100
                    print(f"   Top 3 relevance: {relevance_pct:.0f}% ({relevant_count}/{len(top_3)})")
                    
                    if relevance_pct >= 66:  # At least 2 out of 3
                        print("   ✅ Relevance is good")
                        passed += 1
                        self.results["passed"].append(f"Relevance test '{query}': {relevance_pct:.0f}%")
                    else:
                        print("   ⚠️  Relevance could be better")
                        self.results["warnings"].append(f"Relevance test '{query}': {relevance_pct:.0f}%")
                        failed += 1
                else:
                    print("   ⚠️  No results to test relevance")
                    self.results["warnings"].append(f"Relevance test '{query}': No results")
                    failed += 1
            else:
                print(f"   ❌ Search failed: {result.get('error')}")
                self.results["failed"].append(f"Relevance test '{query}': {result.get('error')}")
                failed += 1
            
            time.sleep(0.5)
        
        print(f"\n📊 Relevance Tests Summary: {passed} passed, {failed} failed")
        return failed == 0
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        total_passed = len(self.results["passed"])
        total_failed = len(self.results["failed"])
        total_warnings = len(self.results["warnings"])
        
        print(f"\n✅ Passed: {total_passed}")
        print(f"❌ Failed: {total_failed}")
        print(f"⚠️  Warnings: {total_warnings}")
        
        if total_failed > 0:
            print("\n❌ Failed Tests:")
            for failure in self.results["failed"]:
                print(f"   - {failure}")
        
        if total_warnings > 0:
            print("\n⚠️  Warnings:")
            for warning in self.results["warnings"]:
                print(f"   - {warning}")
        
        print("\n" + "="*60)
        
        if total_failed == 0:
            print("✅ ALL TESTS PASSED!")
            return True
        else:
            print("❌ SOME TESTS FAILED")
            return False

def main():
    print("🧪 Phase 3 Comprehensive Testing")
    print("="*60)
    
    tester = Phase3Tester()
    
    # Run all test suites
    if not tester.run_basic_tests():
        print("\n❌ Basic tests failed. Stopping.")
        tester.print_summary()
        return
    
    tester.run_search_tests()
    tester.run_edge_case_tests()
    tester.run_performance_tests()
    tester.run_relevance_tests()
    
    # Print final summary
    success = tester.print_summary()
    
    # Save results to file
    with open("phase3_test_results.json", "w") as f:
        json.dump(tester.results, f, indent=2)
    
    print("\n📝 Results saved to: phase3_test_results.json")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())



