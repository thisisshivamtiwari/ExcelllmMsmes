# LLM Benchmarking for MSME Manufacturing

A comprehensive benchmarking system to evaluate LLM performance on MSME manufacturing domain questions using a **hybrid evaluation approach**.

## 🎯 Evaluation Methodology

Unlike traditional benchmarks that ask LLMs to compute answers (which they can't do accurately), this system evaluates:

| Metric | Weight | What It Measures |
|--------|--------|------------------|
| **Table/Column Selection** | 25% | Domain understanding - can the LLM identify correct data sources? |
| **SQL Structure Matching** | 35% | Query generation - can the LLM write correct SQL queries? |
| **Methodology Similarity** | 30% | Reasoning - does the LLM understand the calculation steps? |
| **Response Quality** | 10% | Formatting, latency, error handling |

## 📁 Directory Structure

```
llm_benchmarking/
├── .env                           # API keys (create from .env.example)
├── requirements.txt               # Python dependencies
├── run_benchmark.sh              # Main run script
│
├── config/
│   └── models_config.json        # LLMs to benchmark and weights
│
├── prompts/
│   ├── methodology_prompt.txt    # "What steps would you take?"
│   ├── sql_generation_prompt.txt # "Generate SQL query"
│   ├── table_selection_prompt.txt # "Which tables/columns?"
│   └── gemini_evaluation_prompt.txt # For similarity evaluation
│
├── evaluators/
│   ├── gemini_similarity.py      # Gemini-based semantic similarity
│   ├── sql_comparator.py         # SQL token/structure matching
│   └── table_column_matcher.py   # Table/column selection accuracy
│
├── benchmarks/
│   ├── benchmark_runner.py       # Main orchestrator
│   ├── question_loader.py        # Loads questions from JSON
│   └── llm_client.py             # Unified LLM API client
│
├── analysis/
│   ├── metrics_aggregator.py     # Statistical analysis
│   └── visualizations.py         # Charts and graphs
│
└── results/
    ├── raw_responses/            # Individual LLM responses
    ├── metrics/                  # Calculated scores (JSON, CSV)
    ├── visualizations/           # Charts (PNG)
    └── logs/                     # Benchmark logs (TXT)
```

## 🚀 Quick Start

### 1. Setup

```bash
cd llm_benchmarking

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API keys
cp .env.example .env
# Edit .env and add your GROQ_API_KEY and GEMINI_API_KEY
```

### 2. Run Benchmark

```bash
# Run full benchmark (all models, all questions)
./run_benchmark.sh

# Run with options
./run_benchmark.sh --sample 30          # Test with 30 questions
./run_benchmark.sh --no-gemini          # Skip Gemini evaluation (faster)
./run_benchmark.sh --categories "Easy"  # Only Easy questions

# Just generate visualizations (from existing results)
./run_benchmark.sh --visualize
```

### 3. Python API

```python
from benchmarks.benchmark_runner import BenchmarkRunner

# Initialize
runner = BenchmarkRunner(
    use_gemini_eval=True,  # Use Gemini for methodology evaluation
    sample_size=30         # Number of questions to sample
)

# Run benchmark
results = runner.run(
    models=['llama-3.1-8b-instant', 'llama-3.3-70b-versatile'],
    categories=['Easy', 'Medium']
)

# Generate visualizations
from analysis.visualizations import BenchmarkVisualizer
viz = BenchmarkVisualizer()
viz.load_results()
viz.generate_all_visualizations()
```

## 📊 Output Files

After running the benchmark, you'll find:

### Results (`results/`)
- `model_comparison.csv` - Model scores comparison
- `category_breakdown.csv` - Performance by difficulty

### Metrics (`results/metrics/`)
- `all_results.json` - Complete results with details
- `all_results.csv` - Tabular results
- `summary.json` - Aggregated statistics

### Visualizations (`results/visualizations/`)
- `model_comparison_bar.png` - Bar chart of model scores
- `radar_chart.png` - Radar plot of multi-dimensional performance
- `category_heatmap.png` - Heatmap of model × category
- `score_distribution.png` - Box plots of score distributions
- `latency_comparison.png` - Response time comparison

### Logs (`results/logs/`)
- `benchmark_YYYYMMDD_HHMMSS.txt` - Detailed benchmark log
- `visualization_YYYYMMDD_HHMMSS.txt` - Visualization generation log
- `analysis_report.txt` - Human-readable analysis report

## 🔧 Configuration

### Models (`config/models_config.json`)

```json
{
  "models": [
    {
      "name": "Llama 3.1 8B",
      "id": "llama-3.1-8b-instant",
      "enabled": true
    }
  ],
  "evaluation": {
    "weights": {
      "table_column_selection": 0.25,
      "sql_structure_matching": 0.35,
      "methodology_similarity": 0.30,
      "response_quality": 0.10
    }
  }
}
```

### Evaluation Weights

Adjust weights based on your priorities:
- **Domain accuracy focus**: Increase `table_column_selection`
- **Query generation focus**: Increase `sql_structure_matching`
- **Reasoning focus**: Increase `methodology_similarity`

## 📈 Interpreting Results

### Score Thresholds

| Score | Interpretation | Recommendation |
|-------|---------------|----------------|
| ≥ 70 | Good | Minor prompt engineering |
| 40-70 | Moderate | Domain examples + prompt tuning |
| < 40 | Poor | Fine-tuning recommended |

### Metric Meanings

- **SQL Score**: How well the LLM structures queries (SELECT, FROM, WHERE, etc.)
- **Table/Column Score**: Precision/recall of selecting correct data sources
- **Methodology Score**: Semantic similarity of reasoning steps
- **Response Quality**: Error rate, formatting, latency

## 🤔 FAQ

**Q: Why not compare actual computed answers?**
A: LLMs can't access real data to compute answers. They would hallucinate numbers. This benchmark tests what LLMs CAN do: understand the domain, generate queries, and reason about methods.

**Q: How is methodology evaluated?**
A: Using Gemini API to compare LLM's calculation steps with ground truth steps from the question generator. Fallback to keyword matching if Gemini is unavailable.

**Q: Can I add more models?**
A: Yes! Add entries to `config/models_config.json` with the Groq model ID.

**Q: Why is Gemini used for evaluation?**
A: Gemini provides semantic understanding to compare reasoning quality. You can disable it with `--no-gemini` for faster (but less accurate) evaluation.

## 📝 License

Part of the ExcelLLM MSME project.
