#!/bin/bash

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Add project root to PYTHONPATH
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"

# Check if .env file exists and export OPENAI_API_KEY if not already set
if [ -z "$OPENAI_API_KEY" ] && [ -f "${PROJECT_ROOT}/.env" ]; then
    export OPENAI_API_KEY=$(grep OPENAI_API_KEY "${PROJECT_ROOT}/.env" | cut -d '=' -f2)
fi

# Run the evaluation script
PYTHON_CMD="python3"
if [ -f "${PROJECT_ROOT}/.venv/bin/python" ]; then
    PYTHON_CMD="${PROJECT_ROOT}/.venv/bin/python"
fi
"$PYTHON_CMD" "${PROJECT_ROOT}/POC_RAGAS/scripts/run_evaluation.py" "$@"
