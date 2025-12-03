#!/bin/bash

# Comprehensive Test Runner
# This script starts the backend (if needed) and runs comprehensive tests

set -e

BACKEND_URL="http://localhost:8000"
PROVIDER="${1:-gemini}"  # Default to gemini, can override with $1

echo "=========================================="
echo "Comprehensive Test Suite Runner"
echo "=========================================="
echo "Provider: $PROVIDER"
echo ""

# Check if backend is running
check_backend() {
    curl -s -f "$BACKEND_URL/health" > /dev/null 2>&1
}

# Start backend if not running
if ! check_backend; then
    echo "⚠️  Backend is not running. Starting backend..."
    echo ""
    
    cd backend
    python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
    BACKEND_PID=$!
    cd ..
    
    echo "Backend started with PID: $BACKEND_PID"
    echo "Waiting for backend to be ready..."
    
    # Wait up to 30 seconds for backend to start
    for i in {1..30}; do
        if check_backend; then
            echo "✅ Backend is ready!"
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""
    
    if ! check_backend; then
        echo "❌ Backend failed to start. Check backend.log for details."
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    
    BACKEND_STARTED=true
else
    echo "✅ Backend is already running"
    BACKEND_STARTED=false
fi

# Run comprehensive tests
echo ""
echo "=========================================="
echo "Running Comprehensive Tests"
echo "=========================================="
echo ""

python3 comprehensive_test_suite.py "$PROVIDER"

TEST_EXIT_CODE=$?

# Cleanup
if [ "$BACKEND_STARTED" = true ]; then
    echo ""
    echo "Stopping backend (PID: $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null || true
fi

echo ""
echo "=========================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Some tests failed. Check test_results.json for details."
fi
echo "=========================================="

exit $TEST_EXIT_CODE

