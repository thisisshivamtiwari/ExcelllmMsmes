# Agent Testing Documentation

## Overview
This document provides comprehensive test cases and expected answers for verifying the LangChain Agent System. All answers are verified against the actual CSV files in `uploaded_files/`.

## Ground Truth Data Summary

### File 1: quality_control.csv (29aca7f4-7202-4c2b-bb92-ceb5dfd33b9a.csv)
- **Total Rows**: 675
- **Columns**: Inspection_Date, Batch_ID, Product, Line, Inspected_Qty, Passed_Qty, Failed_Qty, Defect_Type, Rework_Count, Inspector_Name
- **Total Inspected Qty**: 49,107
- **Total Passed Qty**: 47,420
- **Total Failed Qty**: 1,687

### File 2: production_logs.csv (b5b34b6b-2301-4422-860d-e9a5bdfb6a8a.csv)
- **Total Rows**: 872
- **Columns**: Date, Shift, Line_Machine, Product, Target_Qty, Actual_Qty, Downtime_Minutes, Operator
- **Total Actual Qty**: 237,525
- **Total Target Qty**: 279,820
- **Total Downtime**: 11,276 minutes

### File 3: maintenance_logs.csv (d5d3a697-68da-49db-a2b3-064b86912fba.csv)
- **Total Rows**: 132
- **Columns**: Maintenance_Date, Machine, Maintenance_Type, Breakdown_Date, Downtime_Hours, Issue_Description, Technician, Parts_Replaced, Cost_Rupees
- **Total Cost**: 1,030,300 Rupees
- **Breakdown Count**: 42

### File 4: inventory.csv (e3941372-efe1-46dd-a3b4-abc31a6dee99.csv)
- **Total Rows**: 418
- **Columns**: Date, Material_Code, Material_Name, Opening_Stock_Kg, Consumption_Kg, Received_Kg, Closing_Stock_Kg, Wastage_Kg, Supplier, Unit_Cost_Rupees
- **Total Consumption**: 136,428 Kg
- **Total Received**: 106,200 Kg
- **Total Wastage**: 3,704 Kg

---

## Test Cases (20+ Questions)

### Category 1: Basic Data Retrieval

#### Test 1: Total Production Quantity
**Question**: "What is the total production quantity?"
**Expected Answer**: 237,525 units
**Verification**: Sum of `Actual_Qty` column in production_logs.csv
**File**: b5b34b6b-2301-4422-860d-e9a5bdfb6a8a.csv

#### Test 2: Total Inspected Quantity
**Question**: "What is the total inspected quantity?"
**Expected Answer**: 49,107 units
**Verification**: Sum of `Inspected_Qty` column in quality_control.csv
**File**: 29aca7f4-7202-4c2b-bb92-ceb5dfd33b9a.csv

#### Test 3: Total Failed Quantity
**Question**: "How many units failed inspection?"
**Expected Answer**: 1,687 units
**Verification**: Sum of `Failed_Qty` column in quality_control.csv
**File**: 29aca7f4-7202-4c2b-bb92-ceb5dfd33b9a.csv

#### Test 4: Total Maintenance Cost
**Question**: "What is the total maintenance cost?"
**Expected Answer**: 1,030,300 Rupees
**Verification**: Sum of `Cost_Rupees` column in maintenance_logs.csv
**File**: d5d3a697-68da-49db-a2b3-064b86912fba.csv

#### Test 5: Total Material Consumption
**Question**: "What is the total material consumption?"
**Expected Answer**: 136,428 Kg
**Verification**: Sum of `Consumption_Kg` column in inventory.csv
**File**: e3941372-efe1-46dd-a3b4-abc31a6dee99.csv

---

### Category 2: Aggregations and Calculations

#### Test 6: Average Production per Day
**Question**: "What is the average production quantity per day?"
**Expected Answer**: ~272 units/day (237,525 / 872 rows)
**Verification**: Average of `Actual_Qty` column in production_logs.csv
**File**: b5b34b6b-2301-4422-860d-e9a5bdfb6a8a.csv

#### Test 7: Pass Rate Percentage
**Question**: "What is the pass rate percentage?"
**Expected Answer**: ~96.57% (47,420 / 49,107 * 100)
**Verification**: (Passed_Qty / Inspected_Qty) * 100 in quality_control.csv
**File**: 29aca7f4-7202-4c2b-bb92-ceb5dfd33b9a.csv

#### Test 8: Total Downtime Hours
**Question**: "What is the total downtime in hours?"
**Expected Answer**: ~187.93 hours (11,276 minutes / 60)
**Verification**: Sum of `Downtime_Minutes` / 60 in production_logs.csv
**File**: b5b34b6b-2301-4422-860d-e9a5bdfb6a8a.csv

#### Test 9: Average Maintenance Cost
**Question**: "What is the average maintenance cost per maintenance event?"
**Expected Answer**: ~7,805 Rupees (1,030,300 / 132)
**Verification**: Average of `Cost_Rupees` in maintenance_logs.csv
**File**: d5d3a697-68da-49db-a2b3-064b86912fba.csv

#### Test 10: Total Wastage
**Question**: "What is the total material wastage?"
**Expected Answer**: 3,704 Kg
**Verification**: Sum of `Wastage_Kg` column in inventory.csv
**File**: e3941372-efe1-46dd-a3b4-abc31a6dee99.csv

---

### Category 3: Grouped Analysis

#### Test 11: Production by Product
**Question**: "What is the total production quantity by product?"
**Expected Answer**: Sum of `Actual_Qty` grouped by `Product` column
**Verification**: Group by `Product` in production_logs.csv
**File**: b5b34b6b-2301-4422-860d-e9a5bdfb6a8a.csv

#### Test 12: Failed Quantity by Line
**Question**: "What is the total failed quantity by production line?"
**Expected Answer**: Sum of `Failed_Qty` grouped by `Line` column
**Verification**: Group by `Line` in quality_control.csv
**File**: 29aca7f4-7202-4c2b-bb92-ceb5dfd33b9a.csv

#### Test 13: Maintenance Cost by Machine
**Question**: "What is the total maintenance cost by machine?"
**Expected Answer**: Sum of `Cost_Rupees` grouped by `Machine` column
**Verification**: Group by `Machine` in maintenance_logs.csv
**File**: d5d3a697-68da-49db-a2b3-064b86912fba.csv

#### Test 14: Consumption by Material
**Question**: "What is the total consumption by material?"
**Expected Answer**: Sum of `Consumption_Kg` grouped by `Material_Name` or `Material_Code`
**Verification**: Group by `Material_Name` in inventory.csv
**File**: e3941372-efe1-46dd-a3b4-abc31a6dee99.csv

#### Test 15: Defects by Defect Type
**Question**: "What is the total failed quantity by defect type?"
**Expected Answer**: Sum of `Failed_Qty` grouped by `Defect_Type` (excluding nulls)
**Verification**: Group by `Defect_Type` in quality_control.csv
**File**: 29aca7f4-7202-4c2b-bb92-ceb5dfd33b9a.csv

---

### Category 4: Trend Analysis

#### Test 16: Production Trend Over Time
**Question**: "What is the production trend over time?"
**Expected Answer**: Daily/weekly/monthly aggregation of `Actual_Qty` by `Date`
**Verification**: Trend analysis on production_logs.csv
**File**: b5b34b6b-2301-4422-860d-e9a5bdfb6a8a.csv

#### Test 17: Quality Trend Over Time
**Question**: "What is the quality trend (pass rate) over time?"
**Expected Answer**: Daily aggregation of pass rate (Passed_Qty / Inspected_Qty) by `Inspection_Date`
**Verification**: Trend analysis on quality_control.csv
**File**: 29aca7f4-7202-4c2b-bb92-ceb5dfd33b9a.csv

#### Test 18: Maintenance Cost Trend
**Question**: "What is the maintenance cost trend over time?"
**Expected Answer**: Monthly aggregation of `Cost_Rupees` by `Maintenance_Date`
**Verification**: Trend analysis on maintenance_logs.csv
**File**: d5d3a697-68da-49db-a2b3-064b86912fba.csv

---

### Category 5: Comparative Analysis

#### Test 19: Top 5 Products by Production
**Question**: "What are the top 5 products by production quantity?"
**Expected Answer**: Top 5 products sorted by sum of `Actual_Qty`
**Verification**: Comparative analysis on production_logs.csv
**File**: b5b34b6b-2301-4422-860d-e9a5bdfb6a8a.csv

#### Test 20: Top 3 Lines by Failed Quantity
**Question**: "What are the top 3 production lines with highest failed quantity?"
**Expected Answer**: Top 3 lines sorted by sum of `Failed_Qty`
**Verification**: Comparative analysis on quality_control.csv
**File**: 29aca7f4-7202-4c2b-bb92-ceb5dfd33b9a.csv

#### Test 21: Machines with Highest Maintenance Cost
**Question**: "Which machines have the highest maintenance costs?"
**Expected Answer**: Machines sorted by sum of `Cost_Rupees`
**Verification**: Comparative analysis on maintenance_logs.csv
**File**: d5d3a697-68da-49db-a2b3-064b86912fba.csv

---

### Category 6: KPI Calculations

#### Test 22: First Pass Yield (FPY)
**Question**: "What is the First Pass Yield?"
**Expected Answer**: (Passed_Qty / Inspected_Qty) * 100 = ~96.57%
**Verification**: FPY calculation using `Passed_Qty` and `Inspected_Qty`
**File**: 29aca7f4-7202-4c2b-bb92-ceb5dfd33b9a.csv

#### Test 23: Defect Rate
**Question**: "What is the defect rate?"
**Expected Answer**: (Failed_Qty / Inspected_Qty) * 100 = ~3.43%
**Verification**: Defect rate calculation using `Failed_Qty` and `Inspected_Qty`
**File**: 29aca7f4-7202-4c2b-bb92-ceb5dfd33b9a.csv

#### Test 24: Production Efficiency
**Question**: "What is the production efficiency (Actual vs Target)?"
**Expected Answer**: (Actual_Qty / Target_Qty) * 100 = ~84.88%
**Verification**: Efficiency calculation using `Actual_Qty` and `Target_Qty`
**File**: b5b34b6b-2301-4422-860d-e9a5bdfb6a8a.csv

---

### Category 7: Complex Queries

#### Test 25: Production vs Quality Correlation
**Question**: "Compare production quantity and quality pass rate by product"
**Expected Answer**: Cross-file analysis combining production_logs and quality_control
**Verification**: Requires joining data from multiple files

#### Test 26: Downtime Impact on Production
**Question**: "What is the relationship between downtime and production quantity?"
**Expected Answer**: Correlation analysis between `Downtime_Minutes` and `Actual_Qty`
**Verification**: Analysis on production_logs.csv
**File**: b5b34b6b-2301-4422-860d-e9a5bdfb6a8a.csv

---

## How to Verify Answers

### Manual Verification (Python)
```python
import pandas as pd

# Load file
df = pd.read_csv('uploaded_files/[file_id].csv')

# Verify calculation
result = df['Column_Name'].sum()  # or .mean(), .count(), etc.
print(f"Expected: [value], Got: {result}")
```

### Using Agent API
1. Start backend: `cd backend && python3 -m uvicorn main:app --reload`
2. Open frontend: Navigate to `/agent-chat`
3. Ask question
4. Compare answer with expected value from this document

---

## Expected Tool Usage

### For Basic Retrieval:
- Tool: `excel_data_retriever`
- Should use semantic search to find relevant columns/files

### For Calculations:
- Tool: `data_calculator`
- Operations: sum, avg, count, min, max, median, std

### For Trends:
- Tool: `trend_analyzer`
- Periods: daily, weekly, monthly, quarterly, yearly

### For Comparisons:
- Tool: `comparative_analyzer`
- Operations: sum, avg, count, min, max

### For KPIs:
- Tool: `kpi_calculator`
- KPIs: OEE, FPY, defect_rate

---

## Troubleshooting

### If Agent Returns Wrong Answer:
1. Check backend logs for tool errors
2. Verify semantic search found correct columns
3. Check if data preprocessing worked correctly
4. Verify JSON parsing in tool wrappers

### Common Issues:
- **"No relevant columns found"**: Semantic search failed - check embeddings
- **"Column not found"**: Column name mismatch - check actual column names
- **"Invalid input format"**: JSON parsing error - check tool wrapper
- **"No data provided"**: Data retrieval failed - check file_id

---

## Success Criteria

✅ Agent correctly identifies relevant files/columns using semantic search
✅ Calculations match ground truth values (±1% tolerance)
✅ Grouped analyses return correct groupings
✅ Trend analyses show correct time-based aggregations
✅ KPI calculations match manual calculations
✅ Error messages are clear and actionable
✅ Response time < 10 seconds for simple queries
✅ Response time < 30 seconds for complex queries

---

## Notes

- All numeric values should be rounded to 2 decimal places for display
- Percentages should be shown with % symbol
- Dates should be in ISO format (YYYY-MM-DD)
- Large numbers should use comma separators (e.g., 237,525)
- Null/empty values should be handled gracefully



