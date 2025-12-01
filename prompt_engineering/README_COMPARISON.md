# Baseline vs Enhanced Prompt Comparison

## Overview
This script compares the performance of Llama 4 Maverick with baseline prompts vs enhanced prompts.

## Usage

```bash
cd prompt_engineering
python3 compare_baseline_vs_enhanced.py
```

## Current Status

### ✅ Working
- **Table/Column Evaluation**: 100% working - correctly extracts and evaluates table/column selections
- **Methodology Evaluation**: Working - uses Gemini API for semantic similarity
- **Comparison Logic**: Fully functional - compares baseline vs enhanced results

### ⚠️ Needs Fix
- **SQL Extraction**: Currently returning 0% scores. The SQL responses are being generated correctly, but extraction from markdown code blocks is failing.

## Results Summary

From the latest run (10 Complex questions):

- **Baseline Average**: 85.2%
- **Enhanced Average**: 58.9%
- **Improvement**: -26.3% (degraded)

### Component Breakdown:
- **SQL**: -79.3% (extraction issue)
- **Tables/Columns**: +2.4% ✅
- **Methodology**: +3.3% ✅

## Next Steps

1. **Fix SQL Extraction**: The SQLComparator's `extract_sql_from_response()` method needs debugging. SQL responses contain ```sql blocks but extraction is failing.

2. **Investigate SQL Format**: Check if the SQL response format matches what SQLComparator expects.

3. **Re-run Comparison**: Once SQL extraction is fixed, re-run to get accurate comparison.

## Files

- `compare_baseline_vs_enhanced.py`: Main comparison script
- `results/baseline_vs_enhanced_comparison.json`: Detailed comparison results
- `results/baseline_vs_enhanced_comparison.csv`: CSV export for analysis


