#!/bin/bash
# Love-Unlimited Hub Starter

cd "$(dirname "$0")"

echo "======================================================================"
echo "Love-Unlimited Hub - Starting"
echo "======================================================================"

export PYTHONPATH="$(pwd):$PYTHONPATH"

# Activate virtual environment if it exists
if [ -f "../venv2/bin/activate" ]; then
    source ../venv2/bin/activate
fi

python -m uvicorn hub.main:app --host 0.0.0.0 --port 9002 --log-level info
