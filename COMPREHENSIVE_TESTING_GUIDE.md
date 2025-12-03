# Comprehensive Agent Testing Guide

## Overview
This guide provides detailed instructions for testing all agent tools with 20+ questions and verifying answers against ground truth data from the CSV files.

## Ground Truth Data

### File: production_logs.csv (b5b34b6b-2301-4422-860d-e9a5bdfb6a8a.csv)
- **Total Rows**: 872
- **Columns**: Date, Shift, Line_Machine, Product, Target_Qty, Actual_Qty, Downtime_Minutes, Operator
- **Total Actual Qty**: 237,525 units
- **Total Target Qty**: 279,820 units
- **Total Downtime**: 11,276 minutes (187.93 hours)
- **Average Actual Qty**: 272.39 units/day

### File: quality_control.csv (29aca7f4-7202-4c2b-bb92-ceb5dfd33b9a.csv)
- **Total Rows**: 675
- **Columns**: Inspection_Date, Batch_ID, Product, Line, Inspected_Qty, Passed_Qty, Failed_Qty, Defect_Type, Rework_Count, Inspector_Name
- **Total Inspected Qty**: 49,107 units
- **Total Passed Qty**: 47,420 units
- **Total Failed Qty**: 1,687 units
- **Pass Rate**: 96.57%

### File: maintenance_logs.csv (d5d3a697-68da-49db-a2b3-064b86912fba.csv)
- **Total Rows**: 132
- **Columns**: Breakdown_Date, Maintenance_Date, Issue_Description
- **Total Cost**: 1,030,300 Rupees (if Cost_Rupees column exists)
- **Average Cost**: 7,805.30 Rupees
- **Breakdown Count**: 42

### File: inventory.csv (e3941372-efe1-46dd-a3b4-abc31a6dee99.csv)
- **Total Rows**: 418
- **Columns**: Date, Material_Code, Material_Name, Opening_Stock_Kg, Consumption_Kg, Received_Kg, Closing_Stock_Kg, Wastage_Kg, Supplier, Unit_Cost_Rupees
- **Total Consumption**: 136,428 Kg
- **Total Received**: 106,200 Kg
- **Total Wastage**: 3,704 Kg

---

## Test Questions (20+)

### Category 1: Basic Data Retrieval & Summation

#### Test 1: Total Production Quantity
**Question**: "What is the total production quantity?"
**Expected Answer**: 237,525 units
**Verification Steps**:
1. Agent should find `production_logs.csv` file
2. Retrieve `Actual_Qty` column
3. Sum all values
4. Return: 237,525

**How to Verify**:
```python
# In Python or Excel
import pandas as pd
df = pd.read_csv("uploaded_files/b5b34b6b-2301-4422-860d-e9a5bdfb6a8a.csv")
total = df["Actual_Qty"].sum()  # Should be 237525
```

#### Test 2: Total Inspected Quantity
**Question**: "What is the total inspected quantity?"
**Expected Answer**: 49,107 units
**File**: quality_control.csv
**Column**: Inspected_Qty
**Operation**: sum

#### Test 3: Total Failed Quantity
**Question**: "How many units failed inspection?"
**Expected Answer**: 1,687 units
**File**: quality_control.csv
**Column**: Failed_Qty
**Operation**: sum

#### Test 4: Total Maintenance Cost
**Question**: "What is the total maintenance cost?"
**Expected Answer**: 1,030,300 Rupees (if column exists)
**File**: maintenance_logs.csv
**Column**: Cost_Rupees
**Operation**: sum

#### Test 5: Total Material Consumption
**Question**: "What is the total material consumption?"
**Expected Answer**: 136,428 Kg
**File**: inventory.csv
**Column**: Consumption_Kg
**Operation**: sum

---

### Category 2: Average Calculations

#### Test 6: Average Production per Day
**Question**: "What is the average production quantity per day?"
**Expected Answer**: ~272.39 units/day
**File**: production_logs.csv
**Column**: Actual_Qty
**Operation**: avg

#### Test 7: Average Maintenance Cost
**Question**: "What is the average maintenance cost per maintenance event?"
**Expected Answer**: ~7,805.30 Rupees
**File**: maintenance_logs.csv
**Column**: Cost_Rupees
**Operation**: avg

---

### Category 3: Ratio Calculations

#### Test 8: Pass Rate Percentage
**Question**: "What is the pass rate percentage?"
**Expected Answer**: ~96.57%
**Calculation**: (Total Passed Qty / Total Inspected Qty) * 100
**File**: quality_control.csv
**Columns**: Passed_Qty, Inspected_Qty

**Verification**:
```python
df = pd.read_csv("uploaded_files/29aca7f4-7202-4c2b-bb92-ceb5dfd33b9a.csv")
total_passed = df["Passed_Qty"].sum()  # 47420
total_inspected = df["Inspected_Qty"].sum()  # 49107
pass_rate = (total_passed / total_inspected) * 100  # 96.57%
```

---

### Category 4: Time-based Conversions

#### Test 9: Total Downtime in Hours
**Question**: "What is the total downtime in hours?"
**Expected Answer**: ~187.93 hours
**Calculation**: Total Downtime Minutes / 60
**File**: production_logs.csv
**Column**: Downtime_Minutes

**Verification**:
```python
df = pd.read_csv("uploaded_files/b5b34b6b-2301-4422-860d-e9a5bdfb6a8a.csv")
total_minutes = df["Downtime_Minutes"].sum()  # 11276
total_hours = total_minutes / 60  # 187.93
```

---

### Category 5: Count Operations

#### Test 10: Number of Breakdowns
**Question**: "How many breakdowns occurred?"
**Expected Answer**: 42
**File**: maintenance_logs.csv
**Column**: Breakdown_Date
**Operation**: count (non-null values)

---

### Category 6: Grouped Calculations

#### Test 11: Production by Product
**Question**: "What is the total production quantity for each product?"
**Expected Answer**: Grouped sum by Product column
**File**: production_logs.csv
**Column**: Actual_Qty
**Group By**: Product
**Operation**: sum

#### Test 12: Quality by Line
**Question**: "What is the total inspected quantity for each production line?"
**Expected Answer**: Grouped sum by Line column
**File**: quality_control.csv
**Column**: Inspected_Qty
**Group By**: Line
**Operation**: sum

---

### Category 7: Min/Max Operations

#### Test 13: Maximum Production Day
**Question**: "What is the maximum production quantity in a single day?"
**Expected Answer**: Max value from Actual_Qty column
**File**: production_logs.csv
**Column**: Actual_Qty
**Operation**: max

#### Test 14: Minimum Production Day
**Question**: "What is the minimum production quantity in a single day?"
**Expected Answer**: Min value from Actual_Qty column
**File**: production_logs.csv
**Column**: Actual_Qty
**Operation**: min

---

### Category 8: Filtered Queries

#### Test 15: Production for Specific Product
**Question**: "What is the total production quantity for Widget-A?"
**Expected Answer**: Sum of Actual_Qty where Product = "Widget-A"
**File**: production_logs.csv
**Filter**: Product = "Widget-A"
**Column**: Actual_Qty
**Operation**: sum

#### Test 16: Quality Issues by Defect Type
**Question**: "How many units failed due to Dimensional defects?"
**Expected Answer**: Sum of Failed_Qty where Defect_Type = "Dimensional"
**File**: quality_control.csv
**Filter**: Defect_Type = "Dimensional"
**Column**: Failed_Qty
**Operation**: sum

---

### Category 9: Complex Calculations

#### Test 17: Production Efficiency
**Question**: "What is the overall production efficiency percentage?"
**Expected Answer**: (Total Actual Qty / Total Target Qty) * 100
**Calculation**: (237,525 / 279,820) * 100 = ~84.92%

#### Test 18: Defect Rate
**Question**: "What is the overall defect rate?"
**Expected Answer**: (Total Failed Qty / Total Inspected Qty) * 100
**Calculation**: (1,687 / 49,107) * 100 = ~3.43%

---

### Category 10: Date Range Queries

#### Test 19: Production in Specific Month
**Question**: "What is the total production quantity for November 2025?"
**Expected Answer**: Sum of Actual_Qty where Date is in November 2025
**File**: production_logs.csv
**Filter**: Date between 2025-11-01 and 2025-11-30
**Column**: Actual_Qty
**Operation**: sum

---

### Category 11: Comparative Analysis

#### Test 20: Best Performing Product
**Question**: "Which product has the highest total production?"
**Expected Answer**: Product with maximum sum of Actual_Qty
**File**: production_logs.csv
**Group By**: Product
**Column**: Actual_Qty
**Operation**: sum, then max

#### Test 21: Worst Performing Line
**Question**: "Which production line has the highest failure rate?"
**Expected Answer**: Line with maximum (Failed_Qty / Inspected_Qty)
**File**: quality_control.csv
**Group By**: Line
**Calculation**: (Failed_Qty / Inspected_Qty) * 100, then max

---

## How to Run Tests

### Option 1: Using the Test Script
```bash
cd /Users/shivamtiwari/Softwares/ExcelllmMsmes
python3 test_agent_comprehensive.py
```

### Option 2: Manual Testing via Frontend
1. Start the backend:
   ```bash
   cd backend
   python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. Start the frontend:
   ```bash
   cd frontend
   npm run dev
   ```

3. Navigate to Agent Chat page
4. Ask each question one by one
5. Verify the answer matches the expected value

### Option 3: Using Python Script
```python
import requests

API_BASE = "http://localhost:8000"

questions = [
    "What is the total production quantity?",
    "What is the total inspected quantity?",
    # ... add all questions
]

for question in questions:
    response = requests.post(
        f"{API_BASE}/api/agent/query",
        json={"question": question, "provider": "groq"}
    )
    result = response.json()
    print(f"Q: {question}")
    print(f"A: {result.get('answer', 'No answer')}")
    print()
```

---

## Expected Tool Behavior

### excel_data_retriever Tool
1. **File Finding**: Should find files by name (e.g., "production_logs" → production_logs.csv)
2. **Semantic Search**: Should use semantic search to find relevant columns
3. **Data Limiting**: Should limit results to 100 rows to prevent token overflow
4. **Column Selection**: Should retrieve only relevant columns

### data_calculator Tool
1. **Sum Operation**: Should sum all values in a numeric column
2. **Average Operation**: Should calculate mean of values
3. **Count Operation**: Should count non-null values
4. **Group By**: Should group results by specified columns

### trend_analyzer Tool
1. **Time Series**: Should analyze trends over time periods
2. **Period Aggregation**: Should aggregate by daily/weekly/monthly

### comparative_analyzer Tool
1. **Entity Comparison**: Should compare entities (products, lines, etc.)
2. **Top N**: Should return top N entities

---

## Troubleshooting

### Issue: Agent can't find file
**Solution**: Check that file name matching is working. The tool should:
- Try exact filename match first
- Try pattern matching (production → production_logs)
- Use semantic search as fallback

### Issue: Token limit exceeded (413 error)
**Solution**: The tool should automatically limit data to 100 rows. If still failing:
- Check that limit is being applied
- Reduce number of columns retrieved
- Use summary statistics instead of raw data

### Issue: Wrong calculation result
**Solution**: 
1. Verify the CSV file has the expected data
2. Check that the correct column is being used
3. Verify the operation (sum/avg/count) is correct
4. Check for null values that might affect calculations

### Issue: Agent returns "cannot find file"
**Solution**:
1. Check that files are uploaded and indexed
2. Verify semantic search is working
3. Check file metadata exists
4. Try using exact filename in query

---

## Verification Checklist

After asking each question, verify:

- [ ] Agent found the correct file
- [ ] Agent retrieved the correct column(s)
- [ ] Calculation result matches expected value (within tolerance)
- [ ] Answer is formatted clearly with units
- [ ] No errors in backend logs
- [ ] Response time is reasonable (< 10 seconds)

---

## Success Criteria

All tests pass if:
1. ✅ File finding works for all file types
2. ✅ Data retrieval returns correct columns
3. ✅ Calculations match ground truth (within tolerance)
4. ✅ No token limit errors
5. ✅ Agent provides clear, formatted answers
6. ✅ All 20+ questions answered correctly

---

## Notes

- **Tolerance**: Allow small differences due to rounding (typically 0.01% for sums, 1 unit for averages)
- **Data Changes**: If CSV files are updated, recalculate ground truth values
- **Column Names**: Verify column names match exactly (case-sensitive)
- **Null Values**: Some calculations may need to handle null values

---

## Next Steps

After completing all tests:
1. Document any failures
2. Fix identified issues
3. Re-run tests to verify fixes
4. Update this guide with any new findings

