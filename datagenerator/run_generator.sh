#!/bin/bash
# Helper script to run the data generator with the correct Python interpreter

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Function to test if Python has required packages
test_python_packages() {
    local python_path="$1"
    "$python_path" -c "import google.generativeai; import pandas; import dotenv" 2>/dev/null
    return $?
}

# Try to find Python with required packages
PYTHON=""
PYTHON_PATHS=(
    "/opt/anaconda3/bin/python3"
    "$HOME/anaconda3/bin/python3"
    "$HOME/miniconda3/bin/python3"
)

# First, try Anaconda/Miniconda Python (most likely to have packages)
for python_path in "${PYTHON_PATHS[@]}"; do
    if [ -f "$python_path" ]; then
        if test_python_packages "$python_path"; then
            PYTHON="$python_path"
            break
        fi
    fi
done

# If not found, try system python3
if [ -z "$PYTHON" ]; then
    if command -v python3 &> /dev/null; then
        if test_python_packages python3; then
            PYTHON="python3"
        fi
    fi
fi

# If still not found, use Anaconda Python anyway (it likely has packages)
if [ -z "$PYTHON" ]; then
    if [ -f "/opt/anaconda3/bin/python3" ]; then
        PYTHON="/opt/anaconda3/bin/python3"
        echo "Warning: Could not verify packages, but using Anaconda Python (likely has packages)"
    elif [ -f "$HOME/anaconda3/bin/python3" ]; then
        PYTHON="$HOME/anaconda3/bin/python3"
        echo "Warning: Could not verify packages, but using Anaconda Python (likely has packages)"
    else
        echo "Error: Python 3 with required packages not found."
        echo ""
        echo "Please install required packages:"
        echo "  pip install google-generativeai pandas python-dotenv"
        echo ""
        echo "Or use Anaconda Python:"
        echo "  /opt/anaconda3/bin/python3 data_generator.py"
        exit 1
    fi
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found!"
    echo "Please create .env file from .env.example and add your GEMINI_API_KEY"
    echo ""
    echo "Example:"
    echo "  cp .env.example .env"
    echo "  # Then edit .env and add your API key"
    exit 1
fi

# Run the generator
echo "Using Python: $PYTHON"
echo "Python version: $($PYTHON --version)"
echo ""
exec "$PYTHON" data_generator.py "$@"

