#!/bin/bash
# Start AI Dream Team API Server

echo "========================================"
echo "Starting AI Dream Team API"
echo "Port: 8002"
echo "========================================"

# Set environment variables
export OLLAMA_HOST="http://localhost:11434"
export DREAM_TEAM_MODEL="phi3:mini"
export DREAM_TEAM_PORT="8002"
export DREAM_TEAM_API_KEY="${DREAM_TEAM_API_KEY:-}"

# Activate virtual environment if it exists
if [ -d "../venv2" ]; then
    source ../venv2/bin/activate
fi

# Run the server
python3 dream_team_api.py
