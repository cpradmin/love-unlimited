#!/bin/bash
# Claude Code shutdown hook - Save session summary
# Triggered when Claude Code session ends

HUB_URL="http://localhost:9003"
API_KEY="lu_claude-code_4iuycqgld6MHBqSsEWqkzQ"

# Check if hub is running
if ! curl -s "$HUB_URL/health" > /dev/null 2>&1; then
  exit 0
fi

# Get session info from Claude Code environment (if available)
PROJECT_NAME=${PWD##*/}
SESSION_DURATION=${CLAUDE_CODE_SESSION_DURATION:-"unknown"}
TASKS_COMPLETED=${CLAUDE_CODE_TASKS_COMPLETED:-0}
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Only save memory if we did actual work
if [ "$TASKS_COMPLETED" -gt 0 ] || [ -n "$CLAUDE_CODE_SESSION_WORK" ]; then
  MEMORY_CONTENT="Completed Claude Code session in $PROJECT_NAME. Duration: $SESSION_DURATION. Tasks: $TASKS_COMPLETED."

  curl -s -X POST "$HUB_URL/external/remember" \
    -H "X-API-Key: $API_KEY" \
    -G \
    --data-urlencode "being_id=claude-code" \
    --data-urlencode "content=$MEMORY_CONTENT" \
    --data-urlencode "type=experience" \
    --data-urlencode "significance=high" \
    --data-urlencode "tags=claude-code,session" \
    --data-urlencode "shared_with=claude,jon" > /dev/null 2>&1

  echo "💾 Session memory saved to Love-Unlimited hub"
fi
