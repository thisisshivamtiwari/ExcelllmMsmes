#!/bin/bash
# LLM Benchmark Runner Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   LLM Benchmark Runner${NC}"
echo -e "${GREEN}========================================${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo -e "Please create .env file with your API keys:"
    echo -e "  GROQ_API_KEY=your_groq_api_key"
    echo -e "  GEMINI_API_KEY=your_gemini_api_key"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Find Python with required packages
PYTHON_PATHS=(
    "/opt/anaconda3/bin/python3"
    "$HOME/anaconda3/bin/python3"
    "$HOME/miniconda3/bin/python3"
    "python3"
    "python"
)

PYTHON_CMD=""
for py in "${PYTHON_PATHS[@]}"; do
    if command -v "$py" &> /dev/null; then
        if $py -c "import groq; import pandas" &> /dev/null; then
            PYTHON_CMD="$py"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}ERROR: Could not find Python with required packages${NC}"
    echo -e "Install requirements: pip install -r requirements.txt"
    exit 1
fi

echo -e "${GREEN}Using Python: ${PYTHON_CMD}${NC}"

# Parse arguments
SAMPLE_SIZE=""
NO_GEMINI=""
MODELS=""
CATEGORIES=""
VISUALIZE_ONLY=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --sample)
            SAMPLE_SIZE="--sample $2"
            shift 2
            ;;
        --no-gemini)
            NO_GEMINI="--no-gemini"
            shift
            ;;
        --models)
            MODELS="--models $2"
            shift 2
            ;;
        --categories)
            CATEGORIES="--categories $2"
            shift 2
            ;;
        --visualize)
            VISUALIZE_ONLY="true"
            shift
            ;;
        --help)
            echo "Usage: ./run_benchmark.sh [options]"
            echo ""
            echo "Options:"
            echo "  --sample N        Sample N questions (default: all)"
            echo "  --no-gemini       Disable Gemini-based evaluation"
            echo "  --models 'ids'    Specify model IDs to benchmark"
            echo "  --categories 'cats' Categories to include (Easy, Medium, Complex)"
            echo "  --visualize       Only generate visualizations (skip benchmark)"
            echo "  --help            Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Run visualization only or full benchmark
if [ "$VISUALIZE_ONLY" == "true" ]; then
    echo -e "${YELLOW}Generating visualizations only...${NC}"
    $PYTHON_CMD -c "
from analysis.visualizations import BenchmarkVisualizer
from analysis.metrics_aggregator import MetricsAggregator

# Generate visualizations
viz = BenchmarkVisualizer()
if viz.load_results():
    viz.generate_all_visualizations()
    
    # Generate report
    agg = MetricsAggregator()
    if agg.load_results():
        report = agg.generate_report(viz.results_dir / 'logs' / 'analysis_report.txt')
        print(report)
else:
    print('No results found. Run benchmark first.')
"
else
    echo -e "${YELLOW}Running benchmark...${NC}"
    $PYTHON_CMD benchmarks/benchmark_runner.py $SAMPLE_SIZE $NO_GEMINI $MODELS $CATEGORIES
    
    echo -e "${YELLOW}Generating visualizations...${NC}"
    $PYTHON_CMD -c "
from analysis.visualizations import BenchmarkVisualizer
from analysis.metrics_aggregator import MetricsAggregator

# Generate visualizations
viz = BenchmarkVisualizer()
if viz.load_results():
    viz.generate_all_visualizations()
    
    # Generate report
    agg = MetricsAggregator()
    if agg.load_results():
        report = agg.generate_report(viz.results_dir / 'logs' / 'analysis_report.txt')
"
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Benchmark Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Results: ${SCRIPT_DIR}/results/"
echo -e "Visualizations: ${SCRIPT_DIR}/results/visualizations/"
echo -e "Logs: ${SCRIPT_DIR}/results/logs/"
