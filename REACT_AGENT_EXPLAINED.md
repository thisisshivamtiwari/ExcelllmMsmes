# ReAct Agent Explained - For ExcelLLM Project

## What is ReAct?

**ReAct** stands for **Reasoning + Acting**. It's a framework for building AI agents that can:
1. **Reason** about problems (think step-by-step)
2. **Act** by using tools (execute actions)
3. **Observe** results and iterate until the problem is solved

Think of it like a human analyst who:
- **Thinks**: "I need to find which product had the most rework"
- **Acts**: Opens the quality control Excel file
- **Observes**: Sees the data
- **Thinks**: "Now I need to sum rework counts by product"
- **Acts**: Uses a calculator tool to aggregate
- **Observes**: Gets the result
- **Final Answer**: "Widget-A had 450 rework units, the highest"

---

## How ReAct Works: The Loop

```
┌─────────────────────────────────────────────────────────┐
│                    USER QUERY                           │
│  "Which product had the most rework this quarter?"      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 1: THOUGHT (Reasoning)                            │
│  "I need to:                                            │
│   1. Find the quality_control table                     │
│   2. Filter for this quarter (Q1 2026)                  │
│   3. Group by Product                                    │
│   4. Sum Rework_Count                                    │
│   5. Find the maximum"                                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 2: ACTION                                         │
│  Tool: ExcelDataRetriever                               │
│  Input: {                                                │
│    table: "quality_control",                            │
│    filters: {date_range: ["2026-01-01", "2026-03-31"]} │
│  }                                                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 3: OBSERVATION                                    │
│  Result: DataFrame with 150 rows                        │
│  Columns: Product, Rework_Count, Inspection_Date       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 4: THOUGHT (Reasoning)                            │
│  "Good, I have the data. Now I need to:                 │
│   1. Group by Product                                   │
│   2. Sum Rework_Count                                    │
│   3. Sort descending"                                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 5: ACTION                                         │
│  Tool: DataCalculator                                   │
│  Input: {                                                │
│    operation: "sum",                                    │
│    column: "Rework_Count",                              │
│    group_by: ["Product"]                                │
│  }                                                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 6: OBSERVATION                                    │
│  Result: {                                               │
│    "Widget-A": 450,                                     │
│    "Widget-B": 320,                                     │
│    "Component-X": 180                                   │
│  }                                                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 7: THOUGHT (Final Reasoning)                      │
│  "Widget-A has the highest rework count (450).            │
│  I should also recommend a bar chart to visualize this." │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 8: ACTION                                         │
│  Tool: ChartRecommender                                  │
│  Input: {                                                │
│    data_type: "comparison",                             │
│    entities: ["Widget-A", "Widget-B", "Component-X"]   │
│  }                                                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  FINAL ANSWER                                           │
│  "Widget-A had the most rework this quarter with 450   │
│  units, followed by Widget-B (320) and Component-X (180).│
│                                                          │
│  [Bar Chart Spec]                                       │
│  [Data Table]                                           │
└─────────────────────────────────────────────────────────┘
```

---

## ReAct Format (Text-Based)

The agent communicates in a structured format:

```
Thought: [The agent's reasoning about what to do next]
Action: [Tool name to use]
Action Input: [Parameters for the tool]
Observation: [Result from the tool]
... (repeat Thought → Action → Observation as needed)
Final Answer: [The complete answer to the user's question]
```

### Example Conversation:

```
User: "Show daily production efficiency trends for Line 3 in May."

Agent:
Thought: I need to analyze production efficiency trends. This requires:
1. Finding production_logs table
2. Filtering for Line 3 (Line_Machine LIKE 'Line-3%')
3. Filtering for May 2026
4. Calculating efficiency = (Actual_Qty / Target_Qty) * 100
5. Grouping by Date
6. Visualizing as a line chart

Action: ExcelDataRetriever
Action Input: {
  "table": "production_logs",
  "filters": {
    "line_machine": "Line-3%",
    "date_range": ["2026-05-01", "2026-05-31"]
  },
  "columns": ["Date", "Actual_Qty", "Target_Qty"]
}
Observation: Retrieved 93 rows. Data contains Date, Actual_Qty, Target_Qty columns.

Thought: Good, I have the data. Now I need to calculate efficiency for each day.

Action: DataCalculator
Action Input: {
  "operation": "calculate_efficiency",
  "actual_column": "Actual_Qty",
  "target_column": "Target_Qty",
  "group_by": ["Date"]
}
Observation: Calculated efficiency percentages:
- 2026-05-01: 95.2%
- 2026-05-02: 98.7%
- 2026-05-03: 92.1%
... (31 days)

Thought: Perfect! Now I should visualize this as a line chart showing the trend over time.

Action: ChartRecommender
Action Input: {
  "query_type": "trend",
  "data_shape": {"rows": 31, "columns": 2},
  "x_axis": "Date",
  "y_axis": "Efficiency (%)"
}
Observation: Recommended: Line chart with Date on x-axis, Efficiency (%) on y-axis.

Final Answer: Daily production efficiency for Line 3 in May 2026 shows an average efficiency of 94.3%. The trend shows:
- Highest efficiency: May 15 (102.1%)
- Lowest efficiency: May 8 (87.5%)
- Overall trend: Slight improvement from start (92%) to end (96%) of month

[Line Chart Visualization]
[Data Table with daily breakdown]
```

---

## Why ReAct for ExcelLLM?

### 1. **Multi-Step Reasoning**
ExcelLLM queries often require multiple steps:
- Find the right table
- Filter data
- Calculate metrics
- Compare results
- Generate visualizations

ReAct handles this naturally.

### 2. **Tool Integration**
ReAct agents can use specialized tools:
- `ExcelDataRetriever` - Get data from Excel files
- `DataCalculator` - Perform aggregations
- `TrendAnalyzer` - Analyze time-series data
- `KPICalculator` - Calculate manufacturing KPIs
- `ChartRecommender` - Suggest visualizations

### 3. **Explainability**
Every step is visible:
- Users can see how the answer was derived
- Debugging is easier
- Trust is built through transparency

### 4. **Error Recovery**
If a tool fails, the agent can:
- Try a different approach
- Use an alternative tool
- Ask for clarification

---

## ReAct vs Traditional LLM Approach

### Traditional Approach (Single Shot):
```
User: "Which product had the most rework?"
LLM: "Based on the data, Widget-A had 450 rework units."
```
**Problem**: LLM might hallucinate or guess without actually checking data.

### ReAct Approach:
```
User: "Which product had the most rework?"
Agent:
  Thought: Need to query quality_control table
  Action: ExcelDataRetriever → Get actual data
  Observation: Retrieved real data
  Thought: Now calculate sums by product
  Action: DataCalculator → Real calculation
  Observation: Widget-A = 450, Widget-B = 320
  Final Answer: Widget-A (based on actual data)
```
**Advantage**: Uses real data, verifiable, explainable.

---

## Tools for ExcelLLM ReAct Agent

### 1. **ExcelDataRetriever**
```python
def retrieve_data(table_name, filters, columns=None):
    """
    Retrieve data from Excel files.
    
    Example:
    retrieve_data(
        table_name="quality_control",
        filters={"product": "Widget-A", "date_range": ("2026-01-01", "2026-03-31")},
        columns=["Product", "Rework_Count", "Inspection_Date"]
    )
    """
    # Implementation: Load Excel, filter, return DataFrame
    pass
```

### 2. **DataCalculator**
```python
def calculate_aggregation(data, operation, column, group_by=None):
    """
    Perform aggregations: sum, avg, count, min, max.
    
    Example:
    calculate_aggregation(
        data=df,
        operation="sum",
        column="Rework_Count",
        group_by=["Product"]
    )
    """
    # Implementation: pandas groupby and aggregation
    pass
```

### 3. **TrendAnalyzer**
```python
def analyze_trends(data, date_column, value_column, period="day"):
    """
    Analyze trends over time.
    
    Example:
    analyze_trends(
        data=df,
        date_column="Date",
        value_column="Actual_Qty",
        period="week"
    )
    """
    # Implementation: Group by time period, calculate trends
    pass
```

### 4. **ComparativeAnalyzer**
```python
def compare_entities(data, entity_column, metric_column, entities=None):
    """
    Compare entities (products, lines, shifts).
    
    Example:
    compare_entities(
        data=df,
        entity_column="Product",
        metric_column="Rework_Count",
        entities=["Widget-A", "Widget-B"]
    )
    """
    # Implementation: Filter and compare
    pass
```

### 5. **KPICalculator**
```python
def calculate_kpi(kpi_name, data, params):
    """
    Calculate manufacturing KPIs: OEE, FPY, Rework Rate, etc.
    
    Example:
    calculate_kpi(
        kpi_name="OEE",
        data={"production": prod_df, "quality": qc_df},
        params={"line": "Line-1", "date": "2026-05"}
    )
    """
    # Implementation: KPI-specific formulas
    pass
```

### 6. **ChartRecommender**
```python
def recommend_chart(query, data_shape, query_type):
    """
    Recommend visualization type and generate spec.
    
    Example:
    recommend_chart(
        query="Show daily production trends",
        data_shape={"rows": 31, "columns": 2},
        query_type="trend"
    )
    # Returns: {"type": "line", "spec": {...}}
    """
    # Implementation: Analyze query and data, recommend chart type
    pass
```

---

## LangChain Implementation Example

```python
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from langchain.llms import Groq

# Initialize LLM (Llama 4 Maverick via Groq)
llm = Groq(model="meta-llama/llama-4-maverick-17b-128e-instruct")

# Define tools
tools = [
    Tool(
        name="ExcelDataRetriever",
        func=retrieve_data,
        description="Retrieve data from Excel files. Use this to get data from production_logs, quality_control, maintenance_logs, or inventory_logs tables."
    ),
    Tool(
        name="DataCalculator",
        func=calculate_aggregation,
        description="Perform aggregations: sum, avg, count, min, max. Use this after retrieving data."
    ),
    Tool(
        name="TrendAnalyzer",
        func=analyze_trends,
        description="Analyze trends over time (daily, weekly, monthly). Use this for time-series queries."
    ),
    Tool(
        name="KPICalculator",
        func=calculate_kpi,
        description="Calculate manufacturing KPIs: OEE, FPY, Rework Rate, Defect Rate, etc."
    ),
    Tool(
        name="ChartRecommender",
        func=recommend_chart,
        description="Recommend visualization type and generate chart specification."
    ),
]

# Initialize ReAct agent
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.REACT_DOCSTORE,  # ReAct agent type
    verbose=True,  # Show reasoning steps
    handle_parsing_errors=True
)

# Use the agent
response = agent.run(
    "Which product had the most rework this quarter?"
)
```

---

## Benefits for ExcelLLM

1. **Accurate**: Uses real data, not hallucinations
2. **Explainable**: Shows reasoning steps
3. **Flexible**: Can handle complex multi-step queries
4. **Extensible**: Easy to add new tools
5. **Debuggable**: Can trace where things went wrong
6. **User Trust**: Users see how answers are derived

---

## Example: Complex Query with ReAct

**User Query**: "Compare defect rate and downtime for each line this month, then show which line has the worst overall performance."

**ReAct Agent Steps**:

```
Thought: This is a complex query requiring:
1. Get quality_control data for defect rates
2. Get maintenance_logs data for downtime
3. Join/combine by Line
4. Calculate defect rate (Failed_Qty / Inspected_Qty)
5. Sum downtime by line
6. Compare and rank

Action: ExcelDataRetriever
Action Input: {
  "tables": ["quality_control", "maintenance_logs"],
  "filters": {"date_range": ["2026-05-01", "2026-05-31"]}
}
Observation: Retrieved data from both tables.

Thought: Now I need to calculate defect rate from quality_control and sum downtime from maintenance_logs, grouped by Line.

Action: DataCalculator
Action Input: {
  "operation": "calculate_defect_rate",
  "data": quality_control_df,
  "group_by": ["Line"]
}
Observation: Defect rates by line:
- Line-1: 2.3%
- Line-2: 3.1%
- Line-3: 1.8%

Action: DataCalculator
Action Input: {
  "operation": "sum",
  "data": maintenance_logs_df,
  "column": "Downtime_Hours",
  "group_by": ["Machine"]  # Need to map Machine to Line
}
Observation: Downtime by machine (need to map to lines):
- Machine-M1 (Line-1): 45 hours
- Machine-M2 (Line-1): 38 hours
- Machine-M3 (Line-2): 52 hours
...

Thought: I need to aggregate downtime by Line. Let me sum all machines for each line.

Action: DataCalculator
Action Input: {
  "operation": "sum_by_line",
  "data": downtime_data,
  "line_mapping": {"Machine-M1": "Line-1", "Machine-M2": "Line-1", ...}
}
Observation: Downtime by line:
- Line-1: 83 hours
- Line-2: 67 hours
- Line-3: 42 hours

Thought: Now I need to combine defect rate and downtime to determine overall performance. I'll normalize both metrics and create a composite score.

Action: ComparativeAnalyzer
Action Input: {
  "data": combined_metrics,
  "metrics": ["defect_rate", "downtime_hours"],
  "comparison_type": "composite_score"
}
Observation: Overall performance scores (lower is better):
- Line-1: 6.2 (worst)
- Line-2: 5.1
- Line-3: 3.5 (best)

Thought: Line-1 has the worst overall performance. I should recommend a comparison chart.

Action: ChartRecommender
Action Input: {
  "query_type": "comparison",
  "data_shape": {"entities": 3, "metrics": 2}
}
Observation: Recommended: Grouped bar chart comparing defect rate and downtime by line.

Final Answer: 
Line-1 has the worst overall performance this month:
- Defect Rate: 2.3% (highest)
- Downtime: 83 hours (highest)
- Composite Score: 6.2 (worst)

Line-3 performs best:
- Defect Rate: 1.8% (lowest)
- Downtime: 42 hours (lowest)
- Composite Score: 3.5 (best)

[Grouped Bar Chart showing defect rate and downtime by line]
```

---

## Key Takeaways

1. **ReAct = Reasoning + Acting**: The agent thinks, acts, observes, and iterates
2. **Tool-Based**: Uses specialized tools for specific tasks
3. **Explainable**: Every step is visible and traceable
4. **Iterative**: Can handle complex multi-step queries
5. **Perfect for ExcelLLM**: Matches the need for data-driven, explainable answers

---

## Next Steps for ExcelLLM

1. **Implement Tools**: Build the 6-7 tools (ExcelDataRetriever, DataCalculator, etc.)
2. **Set Up LangChain**: Initialize ReAct agent with Llama 4 Maverick
3. **Create System Prompt**: Define agent behavior and tool usage guidelines
4. **Test with Sample Queries**: Validate agent reasoning and tool selection
5. **Add Error Handling**: Handle tool failures gracefully
6. **Integrate with Frontend**: Display reasoning steps to users

---

**References:**
- [LangChain ReAct Documentation](https://python.langchain.com/docs/modules/agents/agent_types/react)
- [ReAct Paper](https://arxiv.org/abs/2210.03629)
- Your project roadmap: `projectRoadmap.txt` (lines 178-197)


