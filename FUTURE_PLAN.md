# ExcelLLM - Future Development Plan

## Current State Assessment

### ✅ Completed Components

1. **Data Generation** (`datagenerator/`)
   - ✅ Stateful MSME manufacturing data generation (production, quality, maintenance, inventory)
   - ✅ Realistic relationships and patterns maintained
   - ✅ 4 CSV files with comprehensive shopfloor data

2. **Question Generation** (`question_generator/`)
   - ✅ ~2,000 query-answer pairs with ground truth
   - ✅ Categorized by difficulty (Easy, Medium, Complex)
   - ✅ Includes SQL formulas, calculation steps, related tables/columns

3. **LLM Benchmarking** (`llm_benchmarking/`)
   - ✅ Comprehensive evaluation framework
   - ✅ Tested 7 models (Llama 3.1, Llama 3.3, Allam 2, Qwen 3, Llama 4 Scout, Llama 4 Maverick, Kimi K2)
   - ✅ Multi-metric evaluation (SQL, Tables, Methodology, Quality)
   - ✅ **Top Performer Identified: Llama 4 Maverick (88.5% overall score)**
   - ✅ Visualizations and detailed reports

4. **Prompt Engineering** (`prompt_engineering/`)
   - ✅ Enhanced prompts for methodology and table selection
   - ✅ Baseline vs Enhanced comparison
   - ✅ **Enhanced prompts show +2.1% improvement (87.3% vs 85.2%)**
   - ✅ Methodology: +4.3%, Tables: +3.0%, SQL: +0.5%

5. **Model Selection**
   - ✅ **Selected Model: Llama 4 Maverick 17B (meta-llama/llama-4-maverick-17b-128e-instruct)**
   - ✅ Performance: 88.5% overall, 82.6% SQL, 94.1% Tables, 89.9% Methodology
   - ✅ Enhanced prompts optimized for this model

### 🎯 Gap Analysis

**What's Missing for Full System:**

1. ❌ **Excel/CSV File Parser & Schema Normalization**
2. ❌ **Semantic Indexing & RAG (Embeddings + Vector DB)**
3. ❌ **LangChain Agent System with Tools**
4. ❌ **KPI Calculation Library**
5. ❌ **Visualization Generation Engine**
6. ❌ **FastAPI Backend**
7. ❌ **React Frontend (Vite + React + Tailwind)**
8. ❌ **Fine-tuning Pipeline (LoRA/PEFT)** - Optional, model already performs well

---

## Phase-by-Phase Implementation Plan

### **Phase 1: Data Ingestion & Schema Management** (Priority: HIGH)
**Goal**: Build robust Excel/CSV parsing with automatic schema detection and normalization

#### 1.1 Excel Parser Module (`excel_parser/`)
**Files to Create:**
- `excel_parser/excel_loader.py` - Main parser for .xlsx and .csv files
- `excel_parser/schema_detector.py` - Auto-detect column types, relationships
- `excel_parser/schema_normalizer.py` - Normalize column names (Product_Name → product)
- `excel_parser/data_cleaner.py` - Handle missing values, date standardization
- `excel_parser/schema_registry.py` - Store and query schema metadata

**Key Features:**
- Support multiple sheets per Excel file
- Infer column types (date, numeric, categorical, text, IDs)
- Handle common manufacturing column name variations:
  - `Product_Name`, `ProductName`, `Prod`, `Item` → `product`
  - `Date`, `Inspection_Date`, `Maintenance_Date` → `date`
  - `Line_Machine`, `Line`, `Machine` → normalize appropriately
- Detect relationships (BatchID, Product, Line across files)
- Store schema in JSON format for fast lookup

**Dependencies:**
```python
pandas>=2.0.0
openpyxl>=3.1.0  # For .xlsx files
python-dateutil>=2.8.0
```

**Estimated Time**: 1-2 weeks

---

#### 1.2 Schema Registry & Metadata Store (`schema_registry/`)
**Files to Create:**
- `schema_registry/registry.py` - Central schema storage
- `schema_registry/relationship_mapper.py` - Map relationships between tables
- `schema_registry/kpi_mapper.py` - Map KPIs to required columns

**Key Features:**
- Store normalized schemas for all uploaded files
- Track relationships (e.g., `production_logs.Product` ↔ `quality_control.Product`)
- KPI-to-column mapping (e.g., "OEE" requires Availability, Performance, Quality columns)
- Fast lookup by column name, table name, or semantic meaning

**Estimated Time**: 3-5 days

---

### **Phase 2: Semantic Indexing & Retrieval** (Priority: HIGH)
**Goal**: Enable semantic search over Excel data for RAG-based query answering

#### 2.1 Embedding Pipeline (`embeddings/`)
**Files to Create:**
- `embeddings/embedder.py` - Generate embeddings for columns, sample rows
- `embeddings/vector_store.py` - Interface to ChromaDB/FAISS
- `embeddings/retriever.py` - Semantic search over indexed data

**Key Features:**
- Embed column names and descriptions
- Embed sample rows (top 10-20 rows per column for context)
- Use lightweight embedding model (e.g., `sentence-transformers/all-MiniLM-L6-v2`)
- Store in ChromaDB for fast similarity search
- Return top-k relevant columns/files for a query

**Dependencies:**
```python
sentence-transformers>=2.2.0
chromadb>=0.4.0
# OR
faiss-cpu>=1.7.4  # Alternative vector store
```

**Estimated Time**: 1 week

---

#### 2.2 Data Retrieval Tool (`tools/excel_retriever.py`)
**Files to Create:**
- `tools/excel_retriever.py` - LangChain tool for retrieving Excel data
- `tools/filters.py` - Filter logic (date ranges, product, line, etc.)

**Key Features:**
- Accept natural language filters
- Return filtered rows from relevant tables
- Provide summary statistics (count, min, max, avg)
- Handle multi-table queries

**Estimated Time**: 3-5 days

---

### **Phase 3: LangChain Agent System** (Priority: HIGH)
**Goal**: Build ReAct-style agent that orchestrates tools to answer queries

#### 3.1 Core Tools (`tools/`)
**Files to Create:**
- `tools/__init__.py` - Tool exports
- `tools/excel_retriever.py` - Retrieve data from Excel files
- `tools/data_calculator.py` - Perform aggregations (sum, avg, count, etc.)
- `tools/trend_analyzer.py` - Analyze trends over time
- `tools/comparative_analyzer.py` - Compare entities (products, lines, periods)
- `tools/kpi_calculator.py` - Calculate manufacturing KPIs (OEE, FPY, etc.)
- `tools/chart_recommender.py` - Recommend visualization type and spec
- `tools/sql_generator.py` - Generate SQL for complex queries (optional)

**Tool Specifications:**

**1. ExcelDataRetriever**
```python
def retrieve_data(
    table_name: str,
    filters: Dict[str, Any],  # {"product": "Widget-A", "date_range": ("2026-01-01", "2026-12-31")}
    columns: List[str] = None,
    limit: int = 1000
) -> pd.DataFrame
```

**2. DataCalculator**
```python
def calculate_aggregation(
    data: pd.DataFrame,
    operation: str,  # "sum", "avg", "count", "min", "max"
    column: str,
    group_by: List[str] = None
) -> Dict[str, Any]
```

**3. TrendAnalyzer**
```python
def analyze_trends(
    data: pd.DataFrame,
    date_column: str,
    value_column: str,
    period: str  # "day", "week", "month", "quarter"
) -> pd.DataFrame
```

**4. ComparativeAnalyzer**
```python
def compare_entities(
    data: pd.DataFrame,
    entity_column: str,  # "Product", "Line", etc.
    metric_column: str,
    entities: List[str] = None  # If None, compare all
) -> pd.DataFrame
```

**5. KPICalculator**
```python
def calculate_kpi(
    kpi_name: str,  # "OEE", "FPY", "rework_rate", etc.
    data: Dict[str, pd.DataFrame],  # Multiple tables if needed
    params: Dict[str, Any]
) -> float
```

**6. ChartRecommender**
```python
def recommend_chart(
    query: str,
    data_shape: Dict[str, Any],  # Rows, columns, data type
    query_type: str  # "trend", "comparison", "distribution"
) -> Dict[str, Any]  # Chart spec (type, axes, labels)
```

**Dependencies:**
```python
langchain>=0.1.0
langchain-community>=0.0.20
pandas>=2.0.0
numpy>=1.24.0
```

**Estimated Time**: 2-3 weeks

---

#### 3.2 ReAct Agent (`agent/`)
**Files to Create:**
- `agent/react_agent.py` - Main ReAct agent implementation
- `agent/prompt_templates.py` - System prompts for agent
- `agent/agent_executor.py` - Execute agent with tools
- `agent/reasoning_tracer.py` - Track agent reasoning steps

**Agent System Prompt Template:**
```python
system_prompt = f"""
You are an expert MSME manufacturing data analyst assistant.
Your goal is to answer questions about production, quality, maintenance, and inventory data.

Available Tools:
{tool_descriptions}

Manufacturing KPIs:
- OEE (Overall Equipment Effectiveness) = Availability × Performance × Quality
- FPY (First Pass Yield) = (Passed_Qty / Inspected_Qty) × 100
- Rework Rate = (Rework_Count / Inspected_Qty) × 100
- Defect Rate (PPM) = (Failed_Qty / Inspected_Qty) × 1,000,000

When answering:
1. Break down complex queries into steps
2. Use appropriate tools in sequence
3. Validate data before calculating
4. Provide context with industry benchmarks
5. Recommend visualizations

Response Format:
Thought: [your reasoning]
Action: [tool_name]
Action Input: [tool_input]
Observation: [tool_output]
... (repeat as needed)
Final Answer: [comprehensive response with visualization spec]
"""
```

**Key Features:**
- Use Llama 4 Maverick as the base LLM (via Groq API)
- Integrate all 6-7 tools
- Handle multi-step reasoning
- Provide explainable answers (show reasoning steps)
- Error handling and fallback mechanisms

**Estimated Time**: 1-2 weeks

---

### **Phase 4: KPI Library** (Priority: MEDIUM)
**Goal**: Implement canonical manufacturing KPIs

#### 4.1 KPI Implementation (`kpi_library/`)
**Files to Create:**
- `kpi_library/kpi_definitions.py` - KPI formulas and metadata
- `kpi_library/kpi_calculator.py` - Calculate KPIs from data
- `kpi_library/kpi_validator.py` - Validate required columns exist

**KPIs to Implement:**
1. **OEE** (Overall Equipment Effectiveness)
   - Formula: Availability × Performance × Quality
   - Required columns: Downtime, Target_Qty, Actual_Qty, Passed_Qty

2. **FPY** (First Pass Yield)
   - Formula: (Passed_Qty / Inspected_Qty) × 100
   - Required columns: Passed_Qty, Inspected_Qty

3. **Rework Rate**
   - Formula: (Rework_Count / Inspected_Qty) × 100
   - Required columns: Rework_Count, Inspected_Qty

4. **Defect Rate (PPM)**
   - Formula: (Failed_Qty / Inspected_Qty) × 1,000,000
   - Required columns: Failed_Qty, Inspected_Qty

5. **Production Efficiency**
   - Formula: (Actual_Qty / Target_Qty) × 100
   - Required columns: Actual_Qty, Target_Qty

6. **Downtime Percentage**
   - Formula: (Downtime_Minutes / Total_Minutes) × 100
   - Required columns: Downtime_Minutes

7. **Material Wastage Rate**
   - Formula: (Wastage_Kg / Consumption_Kg) × 100
   - Required columns: Wastage_Kg, Consumption_Kg

**Estimated Time**: 1 week

---

### **Phase 5: Visualization Generation** (Priority: MEDIUM)
**Goal**: Generate chart specifications for frontend rendering

#### 5.1 Chart Spec Generator (`visualization/`)
**Files to Create:**
- `visualization/chart_recommender.py` - Recommend chart type based on query/data
- `visualization/chart_spec_generator.py` - Generate Vega-Lite/Chart.js specs
- `visualization/chart_templates.py` - Pre-defined chart templates

**Chart Types:**
- **Line Chart**: Trends over time (daily/weekly/monthly)
- **Bar Chart**: Comparisons (products, lines, defects)
- **Stacked Bar**: Composition (defects by type per month)
- **Pie Chart**: Distribution (defect types, shift breakdown)
- **Scatter Plot**: Correlations (downtime vs production)

**Chart Spec Format (Vega-Lite):**
```json
{
  "mark": "line",
  "encoding": {
    "x": {"field": "Date", "type": "temporal"},
    "y": {"field": "Actual_Qty", "type": "quantitative"},
    "color": {"field": "Product", "type": "nominal"}
  },
  "title": "Daily Production Trends by Product"
}
```

**Estimated Time**: 1 week

---

### **Phase 6: FastAPI Backend** (Priority: HIGH)
**Goal**: Build REST API for frontend integration

#### 6.1 API Endpoints (`backend/`)
**Files to Create:**
- `backend/main.py` - FastAPI app entry point
- `backend/routes/upload.py` - File upload endpoints
- `backend/routes/query.py` - Query processing endpoints
- `backend/routes/schema.py` - Schema inspection endpoints
- `backend/routes/history.py` - Query history endpoints
- `backend/models/request.py` - Pydantic request models
- `backend/models/response.py` - Pydantic response models
- `backend/services/agent_service.py` - Agent orchestration service
- `backend/services/file_service.py` - File processing service

**API Endpoints:**

**1. Upload Files**
```
POST /api/upload
Request: multipart/form-data (files)
Response: {file_id, schema_summary, status}
```

**2. Process Query**
```
POST /api/query
Request: {query: str, file_ids: List[str]}
Response: {
  answer: str,
  data: pd.DataFrame (as JSON),
  chart_spec: Dict,
  reasoning_steps: List[Dict],
  kpis: Dict[str, float]
}
```

**3. Get Schema**
```
GET /api/schema/{file_id}
Response: {tables: List[Dict], relationships: List[Dict]}
```

**4. Query History**
```
GET /api/history
Response: List[{query, answer, timestamp, file_ids}]
```

**Dependencies:**
```python
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
python-multipart>=0.0.6  # For file uploads
```

**Estimated Time**: 1-2 weeks

---

### **Phase 7: React Frontend** (Priority: HIGH)
**Goal**: Build user-friendly web interface

#### 7.1 Frontend Structure (`frontend/`)
**Files to Create:**
- `frontend/vite.config.js` - Vite configuration
- `frontend/package.json` - Dependencies
- `frontend/src/App.jsx` - Main app component
- `frontend/src/components/FileUpload.jsx` - File upload component
- `frontend/src/components/QueryConsole.jsx` - Query input and results
- `frontend/src/components/DataTable.jsx` - Table display
- `frontend/src/components/ChartRenderer.jsx` - Chart rendering
- `frontend/src/components/SchemaViewer.jsx` - Schema inspection
- `frontend/src/components/QueryHistory.jsx` - History sidebar
- `frontend/src/services/api.js` - API client
- `frontend/src/utils/chartUtils.js` - Chart rendering utilities
- `frontend/src/styles/globals.css` - Tailwind styles

**Key Features:**
- Drag-and-drop file upload
- Real-time query processing with loading states
- Display answers, tables, and charts
- Show reasoning steps (expandable)
- Query history with search
- Schema viewer for uploaded files
- Responsive design (desktop-first, tablet-friendly)

**Dependencies:**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.0",
    "recharts": "^2.10.0",  // For charts
    "react-table": "^7.8.0",  // For tables
    "react-dropzone": "^14.2.0"  // For file upload
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.2.0",
    "tailwindcss": "^3.3.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

**Estimated Time**: 2-3 weeks

---

### **Phase 8: Fine-Tuning Pipeline** (Priority: LOW - Optional)
**Goal**: Fine-tune Llama 4 Maverick on domain-specific data (if needed)

#### 8.1 Fine-Tuning Setup (`finetuning/`)
**Files to Create:**
- `finetuning/data_preparation.py` - Prepare training data from questions
- `finetuning/lora_trainer.py` - LoRA fine-tuning script
- `finetuning/evaluation.py` - Evaluate fine-tuned model
- `finetuning/config.yaml` - Training configuration

**Note**: Since Llama 4 Maverick already achieves 88.5% with enhanced prompts, fine-tuning may not be necessary. However, if we want to improve further:

**Training Data Format:**
```json
{
  "instruction": "Given the following question and data schema, generate SQL query and calculation steps.",
  "input": "Question: {question}\nSchema: {schema}",
  "output": "SQL: {sql}\nSteps: {steps}"
}
```

**Dependencies:**
```python
peft>=0.7.0
transformers>=4.35.0
datasets>=2.14.0
accelerate>=0.24.0
bitsandbytes>=0.41.0  # For quantization
```

**Estimated Time**: 2-3 weeks (if needed)

---

## Implementation Priority & Timeline

### **Sprint 1 (Weeks 1-2): Foundation**
- ✅ Phase 1: Excel Parser & Schema Management
- ✅ Phase 2: Semantic Indexing (basic)

### **Sprint 2 (Weeks 3-4): Core Tools**
- ✅ Phase 3: LangChain Agent System (core tools)
- ✅ Phase 4: KPI Library

### **Sprint 3 (Weeks 5-6): Backend**
- ✅ Phase 6: FastAPI Backend
- ✅ Integration testing

### **Sprint 4 (Weeks 7-8): Frontend**
- ✅ Phase 7: React Frontend
- ✅ End-to-end testing

### **Sprint 5 (Weeks 9-10): Polish & Optimization**
- ✅ Phase 5: Visualization Generation (enhancement)
- ✅ Performance optimization
- ✅ Documentation
- ✅ Demo preparation

**Total Estimated Time**: 10-12 weeks for MVP

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      React Frontend                          │
│  (Vite + React + Tailwind)                                   │
│  - File Upload | Query Console | Results Display            │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST
┌──────────────────────▼──────────────────────────────────────┐
│                    FastAPI Backend                           │
│  - /api/upload | /api/query | /api/schema                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              LangChain ReAct Agent                           │
│  (Llama 4 Maverick via Groq API)                            │
│  - Tool Selection | Multi-step Reasoning                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌────▼──────┐
│   Tools      │ │  KPI Lib    │ │  Charts    │
│ - Retriever  │ │ - OEE       │ │ - Recommender│
│ - Calculator │ │ - FPY       │ │ - Spec Gen │
│ - Trend      │ │ - Rework    │ │            │
│ - Compare    │ │ - Defect    │ │            │
└───────┬──────┘ └─────────────┘ └────────────┘
        │
┌───────▼──────────────────────────────────────┐
│      Data Layer                              │
│  - Excel Parser | Schema Registry           │
│  - Embeddings (ChromaDB) | Vector Search    │
│  - CSV/Excel Files (Storage)                │
└──────────────────────────────────────────────┘
```

---

## Key Design Decisions

### 1. **Model Selection**
- **Chosen**: Llama 4 Maverick 17B (via Groq API)
- **Rationale**: 88.5% overall score, best SQL generation (82.6%), excellent methodology (89.9%)
- **Alternative**: Can switch to local inference if needed (Ollama, vLLM)

### 2. **Vector Store**
- **Chosen**: ChromaDB (lightweight, easy to use)
- **Alternative**: FAISS (faster, but more complex setup)

### 3. **Embedding Model**
- **Chosen**: `sentence-transformers/all-MiniLM-L6-v2` (lightweight, fast)
- **Alternative**: `all-mpnet-base-v2` (better quality, slower)

### 4. **Chart Library**
- **Chosen**: Recharts (React-native, easy integration)
- **Alternative**: Chart.js, D3.js, Vega-Lite

### 5. **Fine-Tuning**
- **Decision**: **Skip for MVP** (model already performs well with enhanced prompts)
- **Future**: Consider fine-tuning if accuracy drops below 85% on real data

---

## Risk Mitigation

### 1. **Data Heterogeneity**
- **Risk**: Real MSME Excel files may have very different schemas
- **Mitigation**: Robust schema normalization, user feedback loop for corrections

### 2. **Performance**
- **Risk**: Query latency > 10 seconds
- **Mitigation**: Caching, parallel tool execution, optimized embeddings

### 3. **Accuracy**
- **Risk**: Model generates incorrect SQL or calculations
- **Mitigation**: Validation layers, explainable reasoning, user confirmation for critical queries

### 4. **Scalability**
- **Risk**: System slow with 50+ Excel files
- **Mitigation**: Lazy loading, pagination, efficient indexing

---

## Success Metrics

### MVP Success Criteria:
1. ✅ Upload 3-5 Excel files successfully
2. ✅ Answer 80%+ of simple queries correctly
3. ✅ Generate accurate SQL queries
4. ✅ Render charts correctly
5. ✅ Response time < 10 seconds for typical queries

### Phase 2 Success Criteria:
1. ✅ Handle 50+ Excel files
2. ✅ Answer 60%+ of complex multi-table queries
3. ✅ Support all manufacturing KPIs
4. ✅ User satisfaction score > 4/5

---

## Next Steps (Immediate Actions)

1. **Create Project Structure**
   ```bash
   mkdir -p excel_parser schema_registry embeddings tools agent kpi_library visualization backend frontend
   ```

2. **Start with Phase 1: Excel Parser**
   - Implement `excel_parser/excel_loader.py`
   - Test with existing CSV files
   - Build schema detection logic

3. **Set Up Development Environment**
   - Create virtual environment
   - Install dependencies
   - Set up testing framework

4. **Create MVP Backlog**
   - Break down each phase into tasks
   - Assign priorities
   - Set up project management (GitHub Projects, etc.)

---

## References

- **PRD**: `projectPrd.md`
- **Problem Statement**: `problemStatement.txt`
- **Roadmap**: `projectRoadmap.txt`
- **Benchmark Results**: `llm_benchmarking/results/metrics/summary.json`
- **Enhanced Prompts**: `prompt_engineering/`

---

**Last Updated**: 2025-11-30
**Status**: Ready for Implementation
**Next Phase**: Phase 1 - Excel Parser & Schema Management


