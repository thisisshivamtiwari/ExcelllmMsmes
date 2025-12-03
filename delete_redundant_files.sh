#!/bin/bash

# Script to delete redundant documentation and test files
# Creates backup before deletion

echo "Creating backup..."
mkdir -p .backup_$(date +%Y%m%d)
cp *.md .backup_$(date +%Y%m%d)/ 2>/dev/null || true
cp *test*.py .backup_$(date +%Y%m%d)/ 2>/dev/null || true
cp *test*.json .backup_$(date +%Y%m%d)/ 2>/dev/null || true

echo "Deleting redundant MD files..."
rm -f ACTION_PLAN.md
rm -f AGENT_FIXES_DECEMBER3.md
rm -f AGENT_TESTING_DOCUMENTATION.md
rm -f CHANGELOG_DEC3_2025.md
rm -f COMPREHENSIVE_FIXES_DEC3.md
rm -f COMPREHENSIVE_TESTING_GUIDE.md
rm -f COMPREHENSIVE_TESTING_SUMMARY.md
rm -f DATA_PREPROCESSING_ANALYSIS.md
rm -f FINAL_100_PERCENT_FIXES.md
rm -f FIXES_AND_TESTING_SUMMARY.md
rm -f FIXES_IMPLEMENTED.md
rm -f FIXES_SUMMARY.md
rm -f FUTURE_PLAN.md
rm -f GEMINI_API_KEY_FIX.md
rm -f GEMINI_GROQ_TOGGLE_GUIDE.md
rm -f GRAPH_TEST_SCENARIOS.md
rm -f GRAPH_VISUALIZATION_COMPLETE.md
rm -f GROQ_API_KEY_TROUBLESHOOTING.md
rm -f JSON_PARSING_FIXES.md
rm -f NEXT_STEPS.md
rm -f PHASE3_COMPLETE.md
rm -f PHASE3_COMPLETION_SUMMARY.md
rm -f PHASE3_FINAL_STATUS.md
rm -f PHASE3_STATUS.md
rm -f PHASE3_TEST_REPORT.md
rm -f PHASE4_INTEGRATION_SUMMARY.md
rm -f PHASE4_TESTING_GUIDE.md
rm -f PLAN_ALIGNMENT_ANALYSIS.md
rm -f QUICK_START_GRAPH_VIZ.md
rm -f READY_FOR_TESTING.md
rm -f TEST_RESULTS_ANALYSIS.md
rm -f TEST_SUITE_README.md
rm -f TESTING_STATUS_REPORT.md
rm -f TROUBLESHOOTING_GEMINI.md
rm -f VECTOR_STORE_ANALYSIS.md

echo "Deleting redundant test files..."
rm -f test_agent.py
rm -f test_agent_comprehensive.py
rm -f test_complex_queries.py
rm -f test_critical_fixes.py
rm -f test_groq_key.py
rm -f test_phase3.py
rm -f comprehensive_agent_test.py
rm -f comprehensive_graph_test.py
rm -f comprehensive_test_suite.py
rm -f expanded_test_suite.py
rm -f quick_validation.py
rm -f quick_fix_validation.py

echo "Deleting redundant result files..."
rm -f *_test_results.json
rm -f *_test_output.log
rm -f *_test_run.log
rm -f test_ground_truth.json
rm -f viz_ground_truth.json
rm -f complex_query_test_results.json
rm -f graph_test_results.json
rm -f phase3_test_results.json
rm -f relationship_test_results.json
rm -f test_results.json

echo "Deleting redundant scripts..."
rm -f run_comprehensive_tests.sh
rm -f run_expanded_tests.sh

echo "Deleting redundant log files..."
rm -f backend_test.log
rm -f backend_final.log
rm -f backend_server.log
rm -f comprehensive_test_output.log
rm -f comprehensive_test_results.log
rm -f expanded_test_run.log
rm -f relationship_test_output.log
rm -f test_output.log
rm -f test_run.log

echo "Deleting file structure analysis..."
rm -f file_structure.json

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Kept essential files:"
echo "  - SYSTEM_REPORT.md (consolidated documentation)"
echo "  - COMPLETE_CODEBASE_UNDERSTANDING.md"
echo "  - unified_test_suite.py (consolidated tests)"
echo "  - ground_truth.json"
echo ""
echo "Backup created in: .backup_$(date +%Y%m%d)/"
