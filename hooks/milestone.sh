#!/bin/bash
# Claude Code milestone hook - Log important accomplishments
# Call this from your code when completing significant work
# Example: ./hooks/milestone.sh "Implemented authentication system" "high"

HUB_URL="http://localhost:9003"
API_KEY="lu_claude-code_4iuycqgld6MHBqSsEWqkzQ"
MILESTONE_TEXT="${1:-Major milestone completed}"
SIGNIFICANCE="${2:-high}"

# Check if hub is running
if ! curl -s "$HUB_URL/health" > /dev/null 2>&1; then
  echo "❌ Cannot reach Love-Unlimited hub"
  exit 1
fi

# Get project info
PROJECT_NAME=$(basename "$(pwd)")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Store the milestone
RESPONSE=$(curl -s -X POST "$HUB_URL/external/remember" \
  -H "X-API-Key: $API_KEY" \
  -G \
  --data-urlencode "being_id=claude-code" \
  --data-urlencode "content=$MILESTONE_TEXT in project: $PROJECT_NAME" \
  --data-urlencode "type=experience" \
  --data-urlencode "significance=$SIGNIFICANCE" \
  --data-urlencode "tags=claude-code,milestone,$PROJECT_NAME" \
  --data-urlencode "shared_with=claude,jon")

# Check success
if echo "$RESPONSE" | grep -q '"success":true'; then
  echo "🎯 Milestone logged to Love-Unlimited hub"
  exit 0
else
  echo "⚠️  Failed to log milestone: $RESPONSE"
  exit 1
fi
