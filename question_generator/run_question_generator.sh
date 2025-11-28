#!/bin/bash
# Helper script to run question generator with correct Python interpreter

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Find Anaconda Python
PYTHON=""
if [ -f "/opt/anaconda3/bin/python3" ]; then
    PYTHON="/opt/anaconda3/bin/python3"
elif [ -f "$HOME/anaconda3/bin/python3" ]; then
    PYTHON="$HOME/anaconda3/bin/python3"
elif [ -f "$HOME/miniconda3/bin/python3" ]; then
    PYTHON="$HOME/miniconda3/bin/python3"
else
    PYTHON="python3"
fi

echo "Using Python: $PYTHON"
echo ""

# Check for .env file
if [ ! -f ".env" ] && [ ! -f "../datagenerator/.env" ]; then
    echo "Warning: .env file not found. Make sure GEMINI_API_KEY is set."
    echo "You can create .env file or use the one in ../datagenerator/"
fi

# Run the question generator
exec "$PYTHON" question_generator.py "$@"

