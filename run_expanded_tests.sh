#!/bin/bash

# Expanded Test Suite Runner
# This script will run the expanded comprehensive test suite

set -e

PROVIDER="${1:-gemini}"  # Default to gemini

echo "=========================================="
echo "Expanded Comprehensive Test Suite"
echo "=========================================="
echo "Provider: $PROVIDER"
echo ""

# Check if backend is running
check_backend() {
    curl -s -f "http://localhost:8000/health" > /dev/null 2>&1
}

if ! check_backend; then
    echo "⚠️  Backend is not running!"
    echo ""
    echo "Please start the backend first:"
    echo "  cd backend"
    echo "  python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
    echo ""
    echo "Then run this script again:"
    echo "  ./run_expanded_tests.sh $PROVIDER"
    exit 1
fi

echo "✅ Backend is running"
echo ""
echo "Running expanded test suite with $PROVIDER..."
echo ""

# Run expanded tests
python3 expanded_test_suite.py "$PROVIDER"

TEST_EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "⚠️  Some tests failed. Check expanded_test_results.json for details."
fi
echo "=========================================="

exit $TEST_EXIT_CODE

