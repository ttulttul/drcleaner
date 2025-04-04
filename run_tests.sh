#!/bin/bash

# Exit on error
set -e

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Or use pytest if preferred
pytest tests/
