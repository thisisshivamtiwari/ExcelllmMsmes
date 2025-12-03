# Comprehensive Test Suite Documentation

## Overview

This comprehensive test suite validates the Excel Agent system against actual CSV data with 30+ test queries covering:

- ✅ Basic Calculations (sum, average, count)
- ✅ Product Analysis (defects, production quantities)
- ✅ Trend Analysis (time-series data)
- ✅ Comparative Analysis (efficiency, downtime)
- ✅ KPI Calculations (OEE, FPY, defect rates)
- ✅ Cross-File Relationships (linking production, quality, maintenance, inventory)
- ✅ Edge Cases (error handling, empty data, invalid queries)
- ✅ Complex Queries (multi-step analysis)

## Files

- **`comprehensive_test_suite.py`**: Main test script with 30+ queries
- **`ground_truth.json`**: Pre-calculated expected values from CSV files
- **`run_comprehensive_tests.sh`**: Automated test runner (starts backend if needed)
- **`test_results.json`**: Detailed test results (generated after running tests)

## Quick Start

### Option 1: Automated (Recommended)

```bash
# Run tests with Gemini (default)
./run_comprehensive_tests.sh

# Run tests with Groq
./run_comprehensive_tests.sh groq
```

### Option 2: Manual

```bash
# 1. Ensure backend is running
cd backend
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 2. In another terminal, run tests
python3 comprehensive_test_suite.py gemini
# or
python3 comprehensive_test_suite.py groq
```

## Test Categories

### 1. Basic Calculations
Tests fundamental aggregation operations:
- Total production quantity
- Average production per day
- Total material consumption
- Maintenance event count

**Example Query**: "What is the total production quantity?"
**Expected**: 237,525 units

### 2. Product Analysis
Tests product-specific queries:
- Product with most defects
- Defect rates by product
- Highest production by product
- Production comparison across products

**Example Query**: "Which product has the most defects?"
**Expected**: Assembly-Z (333 defects)

### 3. Trend Analysis
Tests time-series analysis:
- Production trends over last month
- Material consumption trends
- Weekly production trends
- Defect rate trends

**Example Query**: "Show me production trends over the last month"
**Expected**: Trend data with dates, quantities, and percentage changes

### 4. Comparative Analysis
Tests comparison across entities:
- Production efficiency by line
- Highest production line
- Downtime comparison by machine
- Maintenance costs by machine

**Example Query**: "Compare production efficiency across different lines"
**Expected**: Line-1: 84.66%, Line-2: 84.82%, Line-3: 85.28%

### 5. KPI Calculations
Tests key performance indicators:
- OEE (Overall Equipment Effectiveness) by machine
- First Pass Yield (FPY) by product
- Defect rates
- Availability, Performance, Quality metrics

**Example Query**: "Calculate OEE for all machines"
**Expected**: OEE values for each machine (0.0-1.0 range)

### 6. Cross-File Relationships
Tests queries that span multiple files:
- Products with high defects + production quantities
- Machines with downtime + maintenance costs
- Material consumption vs production output
- Production lines + defects + efficiency

**Example Query**: "Which products have the highest defect rates and what are their production quantities?"

### 7. Edge Cases
Tests error handling:
- Invalid product names
- Empty datasets
- Future dates
- Date ranges with no data

**Expected**: Graceful error messages, no crashes

### 8. Complex Queries
Tests multi-step analysis:
- Product defect rate + production trend
- OEE + production + defect rates comparison
- Maintenance costs vs downtime correlation

## Ground Truth Calculation

Ground truth values are calculated directly from CSV files using pandas:

```python
# Example: Total production
df = pd.read_csv('production_logs.csv')
total = df['Actual_Qty'].sum()  # 237,525

# Example: Product with most defects
quality_df = pd.read_csv('quality_control.csv')
defects = quality_df.groupby('Product')['Failed_Qty'].sum()
most_defects = defects.idxmax()  # Assembly-Z
```

To regenerate ground truth:

```bash
python3 << 'EOF'
# Run the ground truth calculation script
# (See comprehensive_test_suite.py for the calculation logic)
EOF
```

## Test Results

After running tests, check `test_results.json` for detailed results:

```json
{
  "timestamp": "2025-12-03T...",
  "total_tests": 30,
  "passed": 28,
  "failed": 2,
  "success_rate": 93.3,
  "results": [
    {
      "query": "What is the total production quantity?",
      "category": "Basic Calculations",
      "success": true,
      "message": "✅ Match! Expected: 237525, Got: 237525",
      "response": {...}
    }
  ]
}
```

## Validation Logic

### Number Validation
- Extracts numbers from agent response using regex
- Compares with expected value within tolerance (default 1-5%)
- Handles formatting differences (commas, units)

### Product/Line/Machine Name Validation
- Extracts entity names from response
- Matches against expected values
- Handles partial matches (e.g., "Machine-M1" matches "Line-1/Machine-M1")

### Trend/Comparison Validation
- Checks for presence of expected data structure
- Validates key fields exist
- Compares summary statistics

## Troubleshooting

### Backend Not Running
```bash
# Check if backend is running
curl http://localhost:8000/health

# Start backend
cd backend
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Tests Timing Out
- Increase `TIMEOUT` in `comprehensive_test_suite.py`
- Check backend logs for errors
- Verify API keys are set correctly

### Incorrect Results
1. Check `test_results.json` for detailed error messages
2. Verify ground truth values in `ground_truth.json`
3. Check backend logs for tool execution errors
4. Verify CSV files are loaded correctly

### Missing Ground Truth
```bash
# Regenerate ground truth
python3 << 'EOF'
# Run ground truth calculation (see comprehensive_test_suite.py)
EOF
```

## Expected Success Rate

With all fixes applied, expected success rates:
- **Basic Calculations**: 100%
- **Product Analysis**: 95%+
- **Trend Analysis**: 90%+ (date filtering can vary)
- **Comparative Analysis**: 95%+
- **KPI Calculations**: 90%+ (OEE calculations can vary)
- **Cross-File Relationships**: 85%+ (complex queries)
- **Edge Cases**: 100% (should handle gracefully)
- **Complex Queries**: 80%+ (multi-step analysis)

**Overall Target**: 90%+ success rate

## Adding New Tests

To add a new test:

1. Add query to `TEST_QUERIES` list in `comprehensive_test_suite.py`:
```python
{
    "category": "Your Category",
    "query": "Your test query",
    "expected_type": "number|product_name|trend|comparison|kpi|...",
    "expected_value": your_expected_value,
    "tolerance": 0.05,  # Optional
    "ground_truth_key": "key.in.ground_truth"  # Optional
}
```

2. Calculate ground truth (if needed) and add to `ground_truth.json`

3. Run tests to verify

## Continuous Testing

For CI/CD integration:

```bash
# Run tests and exit with error code if any fail
./run_comprehensive_tests.sh gemini
if [ $? -ne 0 ]; then
    echo "Tests failed!"
    exit 1
fi
```

## Next Steps

After running tests:
1. Review `test_results.json` for failures
2. Check backend logs for errors
3. Fix any issues found
4. Re-run tests to verify fixes
5. Update documentation if needed

