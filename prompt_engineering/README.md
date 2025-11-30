# Prompt Engineering for Llama 4 Maverick

This module contains enhanced prompt engineering techniques to improve the accuracy of `meta-llama/llama-4-maverick-17b-128e-instruct` for MSME manufacturing data analysis.

## Overview

The benchmark results showed that Llama 4 Maverick achieved **88.5% overall accuracy**, which is good but has room for improvement. This module implements:

1. **Enhanced Prompts** with:
   - Detailed schema information
   - Few-shot examples
   - Chain-of-thought reasoning
   - Domain-specific context

2. **Prompt Optimization** techniques:
   - Question type identification
   - Adaptive few-shot selection
   - Improved SQL generation guidance
   - Better table/column selection prompts

## Structure

```
prompt_engineering/
├── llama4_maverick_optimizer.py  # Main prompt engineering class
├── test_enhanced_prompts.py      # Test script to compare prompts
├── enhanced_prompts/              # Saved prompt templates
├── few_shot_examples/             # Few-shot examples database
├── results/                       # Test results and comparisons
└── README.md                      # This file
```

## Features

### 1. Enhanced Methodology Prompts
- Detailed table descriptions and relationships
- Few-shot examples for different question types
- Step-by-step reasoning guidance
- Edge case handling instructions

### 2. Enhanced SQL Prompts
- Complete schema with data types
- Example queries for reference
- Join relationship guidance
- Date filtering best practices

### 3. Enhanced Table Selection Prompts
- Context-aware table identification
- Relationship mapping
- Column requirement analysis

## Usage

### Basic Usage

```python
from llama4_maverick_optimizer import EnhancedPromptEngineer

# Initialize optimizer
optimizer = EnhancedPromptEngineer()

# Generate enhanced prompt
question = "What is the correlation between downtime minutes and failed quantity?"
prompt = optimizer.generate_enhanced_methodology_prompt(question, category="Complex")

# Query LLM
response, latency, tokens = optimizer.query_llm(prompt)
```

### Testing Enhanced Prompts

```bash
# Run test script
python3 test_enhanced_prompts.py
```

This will:
1. Load test questions (focusing on Complex questions that performed worst)
2. Test enhanced prompts
3. Evaluate against ground truth
4. Save results for comparison

### Test a Single Question

```python
from llama4_maverick_optimizer import EnhancedPromptEngineer

optimizer = EnhancedPromptEngineer()

question = {
    "id": "test_1",
    "question": "What is the correlation between downtime minutes and failed quantity per line machine and product?",
    "category": "Complex"
}

result = optimizer.test_question(question, prompt_version="enhanced_v1")
print(f"Score: {result.score}")
print(f"Latency: {result.latency_ms}ms")
```

## Prompt Versions

### Enhanced v1 (Current)
- **Features:**
  - Comprehensive schema information
  - Few-shot examples for 4 question types
  - Chain-of-thought reasoning
  - Relationship mapping
  - Edge case handling

- **Question Types Supported:**
  - Simple aggregation
  - Top-N queries
  - Correlation analysis
  - Date filtering

## Expected Improvements

Based on the benchmark analysis, enhanced prompts should improve:

1. **Complex Questions** (currently 61-70% range):
   - Better join understanding
   - Improved correlation analysis
   - Clearer relationship mapping

2. **SQL Generation** (currently 82.6%):
   - More accurate joins
   - Better date filtering
   - Improved aggregation logic

3. **Methodology** (currently 89.9%):
   - More structured reasoning
   - Better step breakdown
   - Clearer table relationships

## Configuration

Set your API key in `.env`:
```
GROQ_API_KEY=your_api_key_here
GEMINI_API_KEY=your_gemini_key_here  # Optional, for methodology evaluation
```

## Results

Test results are saved in `results/` directory:
- `enhanced_prompt_results.json` - Detailed test results
- Comparison with baseline performance

## Next Steps

1. **Iterate on Prompts**: Test different prompt variations
2. **Add More Examples**: Expand few-shot examples database
3. **Fine-tune Selection**: Optimize question type identification
4. **A/B Testing**: Compare multiple prompt versions

## Integration with Benchmarking

To integrate enhanced prompts into the main benchmark:

```python
# In llm_benchmarking/benchmarks/llm_client.py
from prompt_engineering.llama4_maverick_optimizer import EnhancedPromptEngineer

if model_id == "meta-llama/llama-4-maverick-17b-128e-instruct":
    optimizer = EnhancedPromptEngineer(model_id)
    # Use enhanced prompts instead of default
```

## Performance Targets

- **Overall Score**: >92% (from 88.5%)
- **SQL Score**: >87% (from 82.6%)
- **Complex Questions**: >75% (from 61-70%)
- **Methodology**: Maintain >90%

## Notes

- Enhanced prompts add ~20-30% more tokens but improve accuracy
- Latency may increase slightly due to longer prompts
- Best results for Complex questions requiring joins and correlations

