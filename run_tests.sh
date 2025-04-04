#!/bin/bash

# Exit on error
set -e

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the tests
python tests/run_tests.py

# Or use pytest if preferred
# pytest tests/
