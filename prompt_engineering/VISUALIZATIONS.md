# Comparison Visualizations

## Overview
Visualizations comparing baseline vs enhanced prompt performance for Llama 4 Maverick.

## Generated Charts

All visualizations are saved in `results/visualizations/`:

### 1. **overall_comparison.png**
- Bar chart comparing overall scores for each question
- Shows baseline vs enhanced side-by-side
- Includes average lines for both approaches
- Highlights which questions improved/degraded

### 2. **component_comparison.png**
- Three-panel comparison of SQL, Tables/Columns, and Methodology
- Shows baseline vs enhanced for each component
- Color-coded bars (green = improvement, red = degradation)
- Component-specific averages

### 3. **improvement_heatmap.png**
- Heatmap showing improvement/degradation across all components
- Green = improvement, Red = degradation
- Easy to spot patterns and outliers
- Shows which components improved most

### 4. **average_comparison.png**
- Bar chart comparing average scores across all components
- Shows overall performance difference
- Includes improvement annotations
- Quick overview of overall impact

### 5. **category_comparison.png**
- Performance comparison by question category (Easy/Medium/Complex)
- Shows which categories benefit most from enhanced prompts
- Category-specific averages and improvements

### 6. **improvement_distribution.png**
- Box plots showing distribution of improvements
- Four panels: SQL, Tables, Methodology, Overall
- Shows median, quartiles, and outliers
- Helps identify consistency of improvements

### 7. **radar_chart.png**
- Radar/spider chart comparing baseline vs enhanced
- Visual representation of multi-dimensional comparison
- Easy to see overall shape of performance

## Usage

### Generate All Visualizations
```bash
cd prompt_engineering
python3 visualize_comparison.py
```

### Auto-generate with Comparison
The comparison script automatically generates visualizations:
```bash
python3 compare_baseline_vs_enhanced.py
```

## Requirements

- `matplotlib`
- `seaborn`
- `pandas`
- `numpy`

Install with:
```bash
pip install matplotlib seaborn pandas numpy
```

## File Structure

```
prompt_engineering/
├── compare_baseline_vs_enhanced.py  # Main comparison script
├── visualize_comparison.py           # Visualization generator
├── results/
│   ├── baseline_vs_enhanced_comparison.json
│   ├── baseline_vs_enhanced_comparison.csv
│   └── visualizations/
│       ├── overall_comparison.png
│       ├── component_comparison.png
│       ├── improvement_heatmap.png
│       ├── average_comparison.png
│       ├── category_comparison.png
│       ├── improvement_distribution.png
│       └── radar_chart.png
```

## Interpreting Results

### Positive Improvements (Green)
- Indicates enhanced prompts performed better
- Look for consistent improvements across multiple questions

### Negative Changes (Red)
- Indicates baseline performed better
- May indicate areas where enhanced prompts need refinement

### Patterns to Look For
- **Consistent improvements**: Multiple questions showing similar gains
- **Component-specific**: Some components (e.g., Methodology) improving more than others
- **Category patterns**: Certain question types benefiting more from enhanced prompts

## Notes

- SQL scores currently showing 0% due to extraction/evaluation issues (being debugged)
- Methodology and Tables/Columns evaluations are working correctly
- Visualizations update automatically when you re-run the comparison

