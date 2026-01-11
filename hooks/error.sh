#!/bin/bash
# Claude Code error hook - Log errors to hub
# Triggered when an error occurs during a session
# Arguments: $1 = error message, $2 = error context

HUB_URL="http://localhost:9003"
API_KEY="lu_claude-code_4iuycqgld6MHBqSsEWqkzQ"
ERROR_MESSAGE="${1:-Unknown error}"
ERROR_CONTEXT="${2:-}"

# Check if hub is running
if ! curl -s "$HUB_URL/health" > /dev/null 2>&1; then
  exit 0
fi

PROJECT_NAME=$(basename "$(pwd)")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Build error memory content
if [ -n "$ERROR_CONTEXT" ]; then
  MEMORY_CONTENT="Error in $PROJECT_NAME: $ERROR_MESSAGE (Context: $ERROR_CONTEXT)"
else
  MEMORY_CONTENT="Error in $PROJECT_NAME: $ERROR_MESSAGE"
fi

# Store error as a learning opportunity
curl -s -X POST "$HUB_URL/external/remember" \
  -H "X-API-Key: $API_KEY" \
  -G \
  --data-urlencode "being_id=claude-code" \
  --data-urlencode "content=$MEMORY_CONTENT" \
  --data-urlencode "type=learning" \
  --data-urlencode "significance=medium" \
  --data-urlencode "tags=claude-code,error,$PROJECT_NAME" \
  --data-urlencode "shared_with=claude,jon" > /dev/null 2>&1

echo "📍 Error logged for future reference"
