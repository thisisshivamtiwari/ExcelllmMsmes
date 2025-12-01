# Usage Guide - Prompt Engineering for Llama 4 Maverick

## Quick Start

### 1. View Enhanced Prompts (No API Key Required)

```bash
cd prompt_engineering
python3 quick_demo.py
```

This shows how enhanced prompts are generated without making API calls.

### 2. Test Enhanced Prompts (Requires API Key)

```bash
# Make sure .env file has GROQ_API_KEY
python3 test_enhanced_prompts.py
```

This will:
- Load 10 Complex questions (worst performing category)
- Test with enhanced prompts
- Evaluate against ground truth
- Save results to `results/enhanced_prompt_results.json`

### 3. Test Single Question

```python
from llama4_maverick_optimizer import EnhancedPromptEngineer

optimizer = EnhancedPromptEngineer()

question = {
    "id": "test_1",
    "question": "What is the correlation between downtime minutes and failed quantity?",
    "category": "Complex"
}

result = optimizer.test_question(question)
print(f"Response: {result.response}")
print(f"Latency: {result.latency_ms}ms")
```

## Key Features

### 1. Question Type Identification
Automatically identifies question type and selects appropriate few-shot example:
- `simple_aggregation` - Basic SUM, COUNT, AVG queries
- `top_n_query` - Top 3/5/10 queries
- `correlation_analysis` - Relationship/correlation questions
- `date_filtering` - Year/month filtering questions

### 2. Enhanced Prompts Include:
- **Detailed Schema**: Full table descriptions with relationships
- **Few-Shot Examples**: Relevant examples based on question type
- **Chain-of-Thought**: Step-by-step reasoning guidance
- **Edge Cases**: NULL handling, date filtering, join instructions

### 3. Three Prompt Types:
1. **Methodology Prompt**: Step-by-step calculation guidance
2. **SQL Prompt**: SQL query generation with examples
3. **Table Selection Prompt**: Table/column identification

## Expected Improvements

Based on benchmark analysis, enhanced prompts should improve:

| Metric | Baseline | Target | Improvement |
|--------|----------|--------|-------------|
| Overall Score | 88.5% | >92% | +3.5% |
| SQL Score | 82.6% | >87% | +4.4% |
| Complex Questions | 61-70% | >75% | +5-14% |
| Methodology | 89.9% | >92% | +2.1% |

## Integration with Main Benchmark

To use enhanced prompts in the main benchmark:

1. **Option 1: Modify llm_client.py**
```python
# In llm_benchmarking/benchmarks/llm_client.py
from prompt_engineering.llama4_maverick_optimizer import EnhancedPromptEngineer

if model_id == "meta-llama/llama-4-maverick-17b-128e-instruct":
    optimizer = EnhancedPromptEngineer(model_id)
    # Use optimizer.generate_enhanced_sql_prompt() instead of default
```

2. **Option 2: Create Wrapper**
Create a wrapper that uses enhanced prompts for Maverick and default for others.

## Files Created

- `llama4_maverick_optimizer.py` - Main prompt engineering class
- `test_enhanced_prompts.py` - Test and evaluation script
- `quick_demo.py` - Demo without API calls
- `README.md` - Full documentation
- `requirements.txt` - Dependencies

## Next Steps

1. **Run Tests**: Execute `test_enhanced_prompts.py` to see improvements
2. **Compare Results**: Compare with baseline 88.5% score
3. **Iterate**: Adjust prompts based on results
4. **Integrate**: Add to main benchmark if improvements are significant

## Troubleshooting

**Error: GROQ_API_KEY not found**
- Create `.env` file in project root with `GROQ_API_KEY=your_key`
- Or set environment variable: `export GROQ_API_KEY=your_key`

**Error: Module not found**
- Install dependencies: `pip install -r requirements.txt`
- Make sure you're in the correct directory

**No improvements seen**
- Check that questions are Complex type (worst performing)
- Verify evaluators are working correctly
- Review prompt output to ensure enhanced prompts are being used


