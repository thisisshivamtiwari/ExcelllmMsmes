# Graph Generator Tool - Comprehensive Guide

## Overview

The Graph Generator tool has been added to generate chart data in JSON format for visualization. It supports 6 chart types and integrates seamlessly with the existing agent system.

## Chart Types Supported

### 1. Line Charts
- **Use Case**: Time series data, trends over time
- **Example Queries**:
  - "Create a line chart showing production quantity over time"
  - "Show me production trends as a line graph"
  - "Plot quality control inspections over time"

### 2. Bar Charts
- **Use Case**: Comparisons between categories
- **Example Queries**:
  - "Create a bar chart comparing production by different lines"
  - "Show me a bar graph of defects by product"
  - "Generate a bar chart comparing maintenance costs by machine"

### 3. Pie Charts
- **Use Case**: Distribution and proportions
- **Example Queries**:
  - "Create a pie chart showing defect type distribution"
  - "Show me a pie chart of production by product"
  - "Generate a pie chart for maintenance types distribution"

### 4. Scatter Charts
- **Use Case**: Correlations and relationships
- **Example Queries**:
  - "Create a scatter plot showing production vs downtime"
  - "Show me a scatter chart of production vs target quantity"
  - "Generate a scatter plot for defects vs production quantity"

### 5. Area Charts
- **Use Case**: Filled trends, cumulative data
- **Example Queries**:
  - "Create an area chart showing production over time"
  - "Show me an area chart of quality inspections over time"
  - "Generate an area chart for inventory levels over time"

### 6. Heatmaps
- **Use Case**: 2D matrix visualizations
- **Example Queries**:
  - "Create a heatmap showing production by line and shift"
  - "Show me a heatmap of defects by product and defect type"
  - "Generate a heatmap for maintenance by machine and type"

## How It Works

1. **User asks for visualization**: "Create a line chart showing production over time"
2. **Agent retrieves data**: Uses `excel_data_retriever` to get production_logs data
3. **Agent generates chart**: Uses `graph_generator` tool with:
   - `chart_type`: "line"
   - `data`: production_logs data (or query string)
   - `x_column`: "Date"
   - `y_column`: "Actual_Qty"
4. **Returns JSON chart data**: Structured JSON that can be rendered by frontend

## Chart Data Format

The tool returns JSON in this format:

```json
{
  "success": true,
  "chart": {
    "type": "line",
    "title": "Production Quantity over Date",
    "x_axis": {
      "label": "Date",
      "data": []
    },
    "y_axis": {
      "label": "Actual_Qty",
      "data": []
    },
    "series": [
      {
        "name": "Actual_Qty",
        "data": [
          {"x": "2025-11-02", "y": 258.0},
          {"x": "2025-11-03", "y": 275.0}
        ]
      }
    ]
  },
  "metadata": {
    "data_points": 872,
    "x_column": "Date",
    "y_column": "Actual_Qty"
  }
}
```

## Integration

The graph generator is automatically available to the agent. When users request visualizations, the agent will:
1. Understand the request
2. Retrieve appropriate data
3. Select the right chart type
4. Generate chart data
5. Return structured JSON response

## Testing

Run the comprehensive visualization test suite:

```bash
python3 visualization_test_suite.py
```

This tests 50+ visualization queries covering:
- All 6 chart types
- Multi-series charts
- Relationship visualizations
- Edge cases

## Known Issues & Fixes Needed

Based on the comprehensive test suite, the following issues need attention:

1. **Date Columns Not Always Retrieved**: Some queries don't get date columns
   - **Fix**: Ensure date columns are always included for trend queries
   - **Status**: Partially fixed - date columns auto-added for trend queries

2. **Product Column Missing**: Quality control queries sometimes miss Product column
   - **Fix**: Ensure ALL columns retrieved for comparative analysis
   - **Status**: Fixed - comparative_analyzer now gets all columns

3. **OEE Calculation Returns 100%**: Incorrect OEE calculation
   - **Fix**: Review OEE calculation logic in kpi_calculator
   - **Status**: Needs investigation

4. **"No Generation Chunks" Errors**: Some queries fail silently
   - **Fix**: Improve error handling and data validation
   - **Status**: Needs investigation

## Next Steps

1. ✅ Graph generator tool created
2. ✅ Visualization test suite created (50+ queries)
3. ⏳ Fix remaining issues from comprehensive test suite
4. ⏳ Run full test suite and verify all queries work
5. ⏳ Create frontend integration (when ready)

## Usage Examples

### Example 1: Simple Line Chart
**Query**: "Create a line chart showing production over time"

**Agent Response**: Returns JSON with line chart data showing production quantity by date

### Example 2: Comparison Bar Chart
**Query**: "Show me a bar chart comparing production by line"

**Agent Response**: Returns JSON with bar chart data comparing production across different lines

### Example 3: Distribution Pie Chart
**Query**: "Create a pie chart showing defect type distribution"

**Agent Response**: Returns JSON with pie chart data showing percentage distribution of defect types

## Technical Details

- **Tool Name**: `graph_generator`
- **Input Format**: JSON string with chart parameters
- **Output Format**: JSON string with chart data
- **Data Source**: Can accept data array or query string (auto-fetches)
- **Chart Library**: Frontend-agnostic (returns standard JSON format)

