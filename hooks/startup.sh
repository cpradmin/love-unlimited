#!/bin/bash
# Claude Code startup hook - Recall relevant memories
# Triggered when a new Claude Code session starts

HUB_URL="http://localhost:9003"
API_KEY="lu_claude-code_4iuycqgld6MHBqSsEWqkzQ"

# Check if hub is running
if ! curl -s "$HUB_URL/health" > /dev/null 2>&1; then
  echo "⚠️  Love-Unlimited hub is not running"
  exit 0
fi

# Get current working directory for context
CWD=$(pwd)
PROJECT_NAME=$(basename "$CWD")

# Recall memories relevant to this project
echo "📚 Loading session context from Love-Unlimited hub..."

MEMORIES=$(curl -s "$HUB_URL/external/recall" \
  -H "X-API-Key: $API_KEY" \
  -G \
  --data-urlencode "q=$PROJECT_NAME recent" \
  --data-urlencode "being_id=claude-code" \
  --data-urlencode "limit=5")

# Extract memory count
COUNT=$(echo "$MEMORIES" | grep -o '"count":[0-9]*' | grep -o '[0-9]*')

if [ "$COUNT" -gt 0 ]; then
  echo "✅ Found $COUNT relevant memories for this session"
else
  echo "📝 No previous memories for this project (starting fresh)"
fi
