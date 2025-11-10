#!/bin/bash
# Runner script for OpenAI tools test
# Uses the virtual environment Python

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
source venv/bin/activate

# Run the test
python3 test_openai_tools.py "$@"
