#!/bin/bash
# CJ - Claude Jailer
# Self-bootstrapping script that manages its own virtual environment

set -e

# Detect script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.cj/venv"

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed or not in PATH" >&2
    echo "Please install Python 3.9 or later" >&2
    exit 1
fi

# Check if venv module is available
if ! python3 -m venv --help &> /dev/null; then
    echo "Error: python3 venv module is not available" >&2
    echo "Please install python3-venv package" >&2
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "First run detected, setting up environment..."

    # Create .cj directory if it doesn't exist
    mkdir -p "$SCRIPT_DIR/.cj"

    # Create virtual environment
    python3 -m venv "$VENV_DIR"

    # Activate virtual environment
    source "$VENV_DIR/bin/activate"

    # Upgrade pip to avoid warnings
    pip install --quiet --upgrade pip

    # Install the cj package in editable mode
    pip install --quiet -e "$SCRIPT_DIR"

    echo "Environment setup complete"
else
    # Activate existing virtual environment
    source "$VENV_DIR/bin/activate"
fi

# Execute Python CLI with all arguments passed through
python -m cjlib "$@"

# Capture and pass through exit code
exit $?
