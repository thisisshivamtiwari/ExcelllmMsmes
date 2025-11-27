## ExcelLLM – PRD (Product Requirements Document)

### 1. Product Overview

**Product name**: ExcelLLM – LLM-Based Excel Assistant for MSME Shopfloor Analytics  
**Owner**: Shivam (Founding Engineer / Researcher)  
**Version**: v0.1 (initial PRD)

**Problem**  
MSME manufacturing units record production, quality, maintenance, and inventory data primarily in Excel. Analysis is manual, slow, error-prone, and dependent on one “Excel expert” in the team. Managers and engineers struggle to quickly answer questions like:
- “Which product had the most rework this quarter?”
- “Show daily production efficiency trends for Line 3.”
- “Summarize rejected batches by defect type.”

**Vision**  
ExcelLLM is a domain-specialized assistant that understands messy, real-world shopfloor Excel files and lets non-technical users ask natural-language questions and receive:
- Correct metrics and tables
- Clear textual explanations
- Suggested and auto-rendered charts/visuals

The system is built on top of a small open-source LLM (SLM) fine-tuned on synthetic and/or real MSME-like data, plus a robust Excel-processing and semantic retrieval layer.

**High-level goals**
- Reduce analysis time for common shopfloor questions from hours to seconds.
- Make insights accessible to non-technical users (supervisors, line managers, quality engineers).
- Provide interpretable answers (explicit calculations, tables, and visual specs).
- Work on commodity hardware / low-cost cloud (small models + efficient tooling).

---

### 2. Target Users & Personas

**Persona 1 – Production Supervisor (Primary)**
- **Context**: Oversees 1–3 production lines, uses Excel logs for shift reporting.
- **Needs**:
  - Track daily/shift-wise output and efficiency.
  - Identify bottlenecks (machines, shifts, products).
  - Compare performance across time or shifts.
- **Success**: Can quickly query “Which shift underperformed this week and why?” from a set of logs and get a clear, trusted answer.

**Persona 2 – Quality Engineer**
- **Context**: Manages QC reports, defect logs, and rework/rejection data.
- **Needs**:
  - Understand defect trends by product, line, shift, and suppliers.
  - Monitor FPY, defect rates (PPM), and rework percentages.
  - Quickly see whether quality is improving over time.
- **Success**: Can query “Top 5 defects this month by frequency and associated lines” and use the results directly in reports.

**Persona 3 – Maintenance / Planning Engineer**
- **Context**: Tracks downtime, maintenance logs, and schedules.
- **Needs**:
  - Identify frequent breakdown machines and MTBF/MTTR trends.
  - Check adherence to preventive maintenance schedules.
- **Success**: Can ask “Which machines have the highest downtime this quarter?” and see a ranked table and a bar chart.

**Persona 4 – SME Owner / Operations Manager**
- **Context**: Higher-level, less technical, wants performance snapshots.
- **Needs**:
  - Simple dashboards / summaries across production, quality, and inventory.
  - Exportable reports for reviews.
- **Success**: Gets a monthly “operations summary” as an easily digestible narrative + visuals without touching pivot tables.

---

### 3. Problem & Scope

**In-scope**
- MSME-scale Excel files:
  - Production logs
  - QC / inspection records
  - Maintenance / downtime logs
  - Inventory/stock/wastage sheets
- Natural-language queries that:
  - Aggregate metrics (sums, averages, counts, rates).
  - Analyze trends over time.
  - Group by categories (product, line, defect type, shift, machine).
  - Compare entities (products, lines, time periods).
- Data scale:
  - 50–100 Excel files.
  - Each up to ~50k rows and 20–50 columns (per sheet, per file).
  - ~2,000 labeled query–answer pairs for fine-tuning/evaluation.

**Out-of-scope (for v0)**
- Real-time data ingestion from machines/PLC/SCADA.
- Complex optimization (e.g., auto-scheduling, advanced forecasting).
- Non-Excel data sources (databases, ERPs, PDFs) except as future extensions.
- Multi-user, multi-tenant SaaS scaling (v0 is single-tenant / demo-focused).

---

### 4. User Journeys

#### 4.1 First-Time Setup – Upload & Index
1. User opens the web app.
2. User uploads one or more Excel/CSV files (production, QC, etc.).
3. Backend:
   - Parses files.
   - Attempts schema detection and normalization (e.g., mapping `Product_Name` vs `ProdName` to `product`).
   - Infers column types (date, categorical, numeric, IDs).
   - Builds semantic/metadata index for fast retrieval.
4. User sees:
   - List of uploaded files.
   - Detected tables/sheets.
   - Basic inferred schema summary (columns, inferred types).

#### 4.2 Ask a Question & Get an Answer
1. User types a natural-language question, e.g.:
   - “Which product had the most rework this quarter?”
   - “Show daily production efficiency trends for Line 3 in May.”
2. System:
   - Uses embeddings/RAG to locate relevant file(s), sheet(s), and columns.
   - Translates question into a sequence of structured operations:
     - Filter rows.
     - Group by fields.
     - Aggregate metrics / compute KPIs.
     - Optionally compare across groups or time windows.
   - Executes computations via a safe calculation engine (e.g., pandas-like tool).
   - Optionally calls a chart recommendation tool to choose chart type and spec.
3. User sees:
   - Final answer with:
     - Key metric(s) in text.
     - Tabular result.
     - Chart(s) (e.g., line, bar) auto-rendered on the frontend.
   - Optional “Explain how this was calculated” view.

#### 4.3 Multi-File Question
1. User asks:
   - “Compare defect rate and downtime for each line this month.”
2. System:
   - Identifies production log + QC + maintenance sheets.
   - Uses schema registry to understand relationships (e.g., `LineID`, `MachineID`, `BatchID`).
   - Joins across tables.
   - Computes combined metrics and renders comparative visuals.

#### 4.4 Evaluation / Benchmarking (Internal User)
1. Internal evaluator runs a suite of predefined questions (~500–2,000).
2. System:
   - Executes each question against the synthetic “ground-truth” dataset.
   - Logs accuracy (exact/approx match), latency, hallucination indicators, and visualization suitability.
3. Evaluator views dashboard summarizing:
   - Accuracy by query type.
   - Latency distribution.
   - Tool-selection correctness.

---

### 5. Functional Requirements

#### 5.1 Excel/CSV Ingestion & Preprocessing
- **FR-1**: Support upload of `.xlsx` and `.csv` files via the web UI.
- **FR-2**: For each uploaded file:
  - Detect sheets/tables.
  - Infer column types (date, numeric, categorical, text, IDs).
  - Normalize common manufacturing column names (e.g., `Product`, `SKU`, `Item_Code` → `product`).
- **FR-3**: Perform basic data cleaning:
  - Handle empty rows/columns.
  - Standardize date formats.
  - Coerce numeric columns where possible.
  - Flag and log anomalies (missing key fields, invalid dates).
- **FR-4**: Store a lightweight schema registry containing:
  - File name, sheet/table name.
  - Column names and normalized names.
  - Column types and basic stats.
  - Guessed relationships (e.g., `BatchID` across multiple sheets).

#### 5.2 Semantic Indexing & Retrieval
- **FR-5**: Compute embeddings for:
  - Column names and description-like headers.
  - Optional sample rows / derived features.
- **FR-6**: Enable semantic search over schema such that given a query, the system:
  - Returns top-k candidate columns/files relevant to the query.
  - Provides scores and metadata for downstream tools.
- **FR-7**: Expose a `ExcelDataRetriever` tool API (for the agent) that:
  - Accepts filters (time range, product, line, etc.).
  - Returns filtered rows and summary statistics from relevant tables.

#### 5.3 Query Understanding & Reasoning
- **FR-8**: Support core query types:
  - Aggregations (sum/avg/min/max/count, ratios, percentages).
  - Trend analysis over time (day/week/month/quarter).
  - Categorical breakdowns (by product, line, defect type, shift).
  - Comparisons (A vs B, this month vs last, line 1 vs line 2).
- **FR-9**: Implement a ReAct-style agent that:
  - Breaks down queries into steps.
  - Calls tools in sequence:
    - `ExcelDataRetriever`
    - `DataCalculator`
    - `TrendAnalyzer`
    - `ComparativeAnalyzer`
    - `ChartRecommender`
    - (Optional) `SQLGenerator` for complex joins/filters.
  - Validates interim results (e.g., ensure non-empty data before computing).
- **FR-10**: Provide an “explain reasoning” trace (for debugging/internal use) capturing:
  - Tools called.
  - Parameters passed.
  - Brief summary of each observation (not raw large data dumps).

#### 5.4 Calculations & KPI Library
- **FR-11**: Provide a canonical KPI library for MSME manufacturing:
  - OEE (Availability × Performance × Quality).
  - Production per shift/hour.
  - Cycle time vs target time.
  - FPY, defect rate (PPM), rework percentage.
  - Downtime hours, changeover time, utilization.
- **FR-12**: Ensure the agent can:
  - Map query language (“efficiency”, “rework rate”, “FPY”) to KPI formulas.
  - Select the correct underlying fields/columns given the schema registry.
- **FR-13**: All final numeric outputs must be reproducible from:
  - A clear formula.
  - A defined subset of rows and columns.

#### 5.5 Visualization Generation
- **FR-14**: For each answered query, system should optionally return:
  - A visualization spec (e.g., Vega-Lite/Chart.js-like) describing chart type, axes, grouping, and labels.
- **FR-15**: `ChartRecommender` must:
  - Map query + data shape to an appropriate chart type:
    - Line: trends over time.
    - Bar/column: comparisons between products/lines/defects.
    - Stacked bar: composition (e.g., defects by type per month).
  - Provide axis labels and titles derived from KPI and units.
- **FR-16**: Frontend must:
  - Render charts automatically from the spec.
  - Handle empty/no data cases gracefully (show a friendly message).

#### 5.6 Web Application (Frontend)
- **FR-17**: Build a SPA using Vite + React + Tailwind.
- **FR-18**: Core screens:
  - **Upload & Data Overview**:
    - File upload area (drag/drop + browse).
    - List of uploaded files with status.
    - Basic schema summary per file.
  - **Query Console**:
    - NL input box.
    - History of queries and answers.
    - Results area with:
      - Textual answer.
      - Table view.
      - Chart view.
  - **Evaluation / Admin (later phase)**:
    - Simple dashboard to run benchmark suites and inspect metrics.
- **FR-19**: UX constraints:
  - Responsive layout (desktop-first, tablet-friendly).
  - Simple, clean, manufacturing-friendly theme (no cluttered UI).
  - Show loading/progress for long-running operations.

#### 5.7 Backend & Model Layer
- **FR-20**: Backend implemented using FastAPI (or similar Python framework).
- **FR-21**: Support pluggable base SLMs (e.g., Llama 3.x, Mistral, Phi-3), with:
  - Configuration for model selection.
  - Ability to run either locally or via a specified inference endpoint.
- **FR-22**: Provide a fine-tuning pipeline (LoRA/PEFT) that:
  - Consumes (query, context, answer) triplets.
  - Produces a domain-adapted model for ExcelLLM.
  - Is scriptable and reproducible (not necessarily UI-exposed).

#### 5.8 Evaluation & Benchmarking
- **FR-23**: Support an evaluation harness that:
  - Runs a fixed set of test queries.
  - Compares generated answers vs ground truth (numerical + table-level).
  - Computes:
    - Accuracy per query type.
    - Hallucination indicators (e.g., references to non-existent products).
    - Latency distributions.
    - Visualization appropriateness scores (manual or heuristic).
- **FR-24**: Provide a simple internal dashboard for these metrics (web-based).

---

### 6. Non-Functional Requirements

- **NFR-1 – Performance**:
  - Query response time (end-to-end) should be:
    - Target: ≤ 10 seconds for typical queries on MSME-scale data.
    - Maximum: ≤ 20 seconds under load or complex multi-file joins.
- **NFR-2 – Accuracy & Reliability**:
  - On the evaluation set:
    - Target ≥ 80% “acceptable” answer rate for single-table, simple aggregation/trend queries.
    - Target ≥ 60% for multi-table, more complex reasoning queries in v0.
  - System must avoid silently returning answers when inputs are clearly invalid (e.g., missing columns).
- **NFR-3 – Interpretability**:
  - Provide optional “show steps” to make results auditable.
  - Expose which files/columns were used.
- **NFR-4 – Security & Privacy (dev/demo scope)**:
  - All data stored locally or in a controlled environment.
  - No sharing of shopfloor data with external APIs without explicit configuration.
- **NFR-5 – Maintainability**:
  - Clear separation between:
    - Data ingestion/normalization.
    - Retrieval & embeddings.
    - Agent tooling.
    - Model-serving layer.
    - Frontend.
- **NFR-6 – Extensibility**:
  - Designed so that:
    - Additional tools (e.g., optimization, forecasting) can be added later.
    - Other domains (retail/logistics) can reuse the same core architecture with new KPIs and schema mappings.

---

### 7. Phased Delivery Scope (MVP vs Later)

**MVP (Phase 1) – “End-to-End Working Demo”**
- Single-user web app.
- Upload 3–5 representative Excel files (production + QC + maintenance).
- Basic schema inference and normalization.
- Semantic retrieval over schema.
- Agent with:
  - Retrieval.
  - Calculation.
  - Simple trend and comparison analysis.
  - Chart recommendation for line and bar charts.
- Support core queries:
  - “Most rework product this quarter.”
  - “Daily production efficiency trend for a line.”
  - “Rejected batches by defect type.”
- Minimal evaluation suite (~50 questions).

**Phase 2 – Robust Data & Question Generators (Internal)**
- Synthetic data generator with stateful patterns (using Gemini or similar).
- Question + answer generator building a ~2,000 query dataset.
- Better schema normalization and multi-file join logic.

**Phase 3 – Model Selection, Fine-Tuning & Agent Refinement**
- Benchmark multiple SLMs zero-shot.
- Fine-tune best candidate using LoRA/PEFT.
- Improve tool selection and failure handling.

**Phase 4 – Evaluation Dashboard & Reporting**
- Full benchmarking dashboard.
- Report export (PDF/Excel) for selected queries/runs.

---

### 8. Risks & Open Questions

- **Data heterogeneity**:
  - How variable are real MSME Excel schemas compared to synthetic ones?
- **Ground-truth generation quality**:
  - Can synthetic data + programmatically computed answers approximate real performance?
- **Deployment constraints**:
  - Local-only vs cloud inference; GPU vs CPU-only MSME environments.
- **User trust**:
  - What explanation level is needed for supervisors to trust the system’s numbers?

These will be refined as real data and feedback become available.


