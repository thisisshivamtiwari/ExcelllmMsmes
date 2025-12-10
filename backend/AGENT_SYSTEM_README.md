# MongoDB-based Agent System

## Overview

A complete agent system built with LangChain that uses MongoDB aggregation pipelines for deterministic, accurate answers. All calculations are performed in MongoDB or using Python Decimal for precision.

## Architecture

```
User Query → FastAPI Endpoint → LangChain Agent → MongoDB Tools → MongoDB Aggregation → Structured Response
```

## Components

### 1. Tools (`backend/tools/mongodb_tools.py`)

All tools return a canonical envelope format:

```json
{
  "ok": true,
  "tool": "tool_name",
  "result": {...},
  "unit": "INR" | "count" | null,
  "provenance": {
    "mongo_pipeline": [...],
    "matched_row_count": 1234,
    "sample_rows": [...]
  },
  "meta": {"time_ms": 123},
  "error": null
}
```

**Available Tools:**

- **`table_loader`**: Load table schema and sample rows
- **`agg_helper`**: Run aggregations (sum, avg, count, min, max, median)
- **`timeseries_analyzer`**: Analyze time series with trend calculation
- **`compare_entities`**: Compare two entities side-by-side
- **`statistical_summary`**: Get min/max/mean/median/std for columns
- **`calc_eval`**: Safe deterministic calculator using Decimal

### 2. Agent (`backend/agent/mongodb_agent.py`)

- LangChain ReAct agent with MongoDB tools
- Supports Gemini and Groq providers
- Temperature set to 0.0 for deterministic responses
- Includes strong system prompt enforcing tool usage

### 3. API Endpoints (`backend/main.py`)

- `POST /api/agent/query` - Execute agent query
- `GET /api/agent/status` - Get agent status
- `GET /api/agent/examples` - Get example queries
- `GET /api/agent/audit/{request_id}` - Get audit log

## Data Structure

Data is stored in MongoDB `tables` collection:

```json
{
  "user_id": ObjectId("..."),
  "file_id": "uuid-string",
  "table_name": "Sheet1",
  "row_id": 1,
  "row": {
    "column1": "value1",
    "column2": 123,
    ...
  },
  "created_at": ISODate("...")
}
```

**Important**: Column access uses `row.column_name` in aggregation pipelines.

## Usage

### Basic Query

```python
POST /api/agent/query
{
  "question": "What is the total production quantity?",
  "file_id": "optional-file-id",
  "provider": "gemini",
  "max_iterations": 10
}
```

### Response Format

```json
{
  "request_id": "uuid",
  "success": true,
  "answer_short": "The total production quantity is 237,525 units.",
  "answer_detailed": "...",
  "values": {
    "total_production": 237525
  },
  "provenance": {
    "agg_helper": {
      "mongo_pipeline": [...],
      "matched_row_count": 872
    }
  },
  "tools_called": ["table_loader", "agg_helper"],
  "confidence": 0.95,
  "latency_ms": 1234,
  "timestamp": "2025-12-08T..."
}
```

## Testing

### Run Test Suite

```bash
cd backend
python3 tests/test_agent_125_questions.py --provider gemini --limit 10
```

This will:
1. Load verified questions from `qa_bank` collection
2. Execute each query through the agent
3. Compare results with expected answers
4. Generate detailed test report

### Test Report

Results are saved to `backend/agent_test_results.json` with:
- Pass/fail status for each question
- Expected vs actual values
- Tools called
- Latency metrics
- Overall success rate

## Key Features

1. **Deterministic Calculations**: All math done in MongoDB or Python Decimal
2. **Full Provenance**: Every answer includes MongoDB pipeline and sample rows
3. **Multi-Tenant**: All queries filtered by `user_id`
4. **Audit Trail**: All queries logged to `agent_audit_logs` collection
5. **Error Handling**: Graceful error handling with detailed error messages

## System Prompt Rules

The agent is instructed to:
1. Always call `table_loader` first to inspect schema
2. Never compute numbers in text - always use tools
3. Use `agg_helper` for aggregations
4. Use `timeseries_analyzer` for time-based questions
5. Use `compare_entities` for comparisons
6. Use `calc_eval` for final arithmetic
7. Include provenance in responses

## MongoDB Indexes

Recommended indexes for performance:

```javascript
db.tables.createIndex({user_id: 1, file_id: 1, table_name: 1})
db.tables.createIndex({"row.Date": 1})
db.tables.createIndex({"row.Product": 1})
db.tables.createIndex({"row.Line": 1})
```

## Limitations

1. MongoDB aggregation framework limitations (no complex regressions)
2. Large collections may be slower than columnar engines
3. Some statistical operations require pulling data to Python

## Next Steps

1. Add visualization tools for chart generation
2. Implement anomaly detection tool
3. Add schema suggester for column discovery
4. Implement pre-aggregation for common queries
5. Add caching layer for frequently asked questions


