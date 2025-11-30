# Enhanced vs Baseline vs Ground Truth Comparison

## Overview
This directory contains a comprehensive three-way comparison analysis comparing:
1. **Enhanced Prompts** - Methodology and table selection enhanced, SQL baseline
2. **Baseline Prompts** - Original benchmark prompts
3. **Ground Truth** - Perfect scores from `generated_questions.json`

## Files

### Code
- **`comparison_analysis.py`** - Single Python script that performs the complete analysis

### Results
- **`results/three_way_comparison.json`** - Detailed comparison data (JSON)
- **`results/three_way_comparison.csv`** - Comparison data (CSV format)
- **`results/comparison_report.txt`** - Comprehensive text report

### Visualizations
All visualizations are saved in `results/visualizations/`:

1. **`three_way_comparison.png`** - Bar chart comparing all three approaches
2. **`component_comparison.png`** - Four-panel component-wise comparison
3. **`gap_analysis.png`** - Distance from ground truth (100%) analysis
4. **`improvement_distribution.png`** - Distribution of improvements
5. **`radar_chart.png`** - Radar/spider chart comparison
6. **`category_comparison.png`** - Performance by question category

## Usage

```bash
cd enhanced_vs_baseline_vs_groundtruth
python3 comparison_analysis.py
```

## Key Metrics

### Overall Performance
- **Ground Truth**: 100.0% (Perfect Score)
- **Baseline Average**: 85.2%
- **Enhanced Average**: 87.3%
- **Improvement**: +2.1%

### Gap from Ground Truth
- **Baseline Gap**: 14.8%
- **Enhanced Gap**: 12.7%
- **Reduction**: Enhanced prompts are 2.1% closer to ground truth

### Component Breakdown
- **SQL**: Baseline 79.3% → Enhanced 79.8% (+0.5%)
- **Tables/Columns**: Baseline 92.9% → Enhanced 95.9% (+3.0%)
- **Methodology**: Baseline 83.7% → Enhanced 88.0% (+4.3%)

### Success Rate
- **Improved**: 7 out of 10 questions (70.0%)
- **Degraded**: 3 questions
- **Same**: 0 questions

## What This Shows

1. **Enhanced prompts perform better** than baseline (+2.1% overall)
2. **Closer to ground truth** - Enhanced reduces gap by 2.1%
3. **Methodology improvement** is the largest gain (+4.3%)
4. **Table selection** also improved (+3.0%)
5. **SQL performance** maintained (using baseline SQL prompt)

## Data Sources

- **Baseline Results**: `llm_benchmarking/results/metrics/all_results.json`
- **Enhanced Results**: `prompt_engineering/results/baseline_vs_enhanced_comparison.json`
- **Ground Truth**: `question_generator/generated_questions.json`

## Requirements

- `pandas`
- `matplotlib`
- `seaborn`
- `numpy`

Install with:
```bash
pip install pandas matplotlib seaborn numpy
```

## Output Structure

```
enhanced_vs_baseline_vs_groundtruth/
├── comparison_analysis.py          # Main analysis script
├── README.md                        # This file
└── results/
    ├── three_way_comparison.json   # Detailed results (JSON)
    ├── three_way_comparison.csv    # Detailed results (CSV)
    ├── comparison_report.txt       # Text report
    └── visualizations/
        ├── three_way_comparison.png
        ├── component_comparison.png
        ├── gap_analysis.png
        ├── improvement_distribution.png
        ├── radar_chart.png
        └── category_comparison.png
```

