# Claude Code + Love-Unlimited Hub Integration via Hooks

This setup connects Claude Code to your Love-Unlimited hub using shell hooks. Your work sessions, milestones, and errors are automatically saved and shared.

## Quick Setup

### 1. Get the Full Path to Hooks

```bash
echo "$(pwd)/hooks"
```
This outputs something like: `/home/kntrnjb/ai-dream-team/micro-ai-swarm/love-unlimited/hooks`

### 2. Configure Claude Code Hooks

In your Claude Code settings (via `~/.claude/settings.json` or Claude Code preferences), add:

```json
{
  "hooks": {
    "session_start": "/home/kntrnjb/ai-dream-team/micro-ai-swarm/love-unlimited/hooks/startup.sh",
    "session_end": "/home/kntrnjb/ai-dream-team/micro-ai-swarm/love-unlimited/hooks/shutdown.sh",
    "error": "/home/kntrnjb/ai-dream-team/micro-ai-swarm/love-unlimited/hooks/error.sh"
  }
}
```

Alternatively, set environment variables:

```bash
export CLAUDE_CODE_HOOK_STARTUP="/home/kntrnjb/ai-dream-team/micro-ai-swarm/love-unlimited/hooks/startup.sh"
export CLAUDE_CODE_HOOK_SHUTDOWN="/home/kntrnjb/ai-dream-team/micro-ai-swarm/love-unlimited/hooks/shutdown.sh"
export CLAUDE_CODE_HOOK_ERROR="/home/kntrnjb/ai-dream-team/micro-ai-swarm/love-unlimited/hooks/error.sh"
```

### 3. Create a Startup Script

For convenience, create a launcher script that automatically sets up the environment:

```bash
#!/bin/bash
# ~/bin/claude-with-hub

HUB_PATH="/home/kntrnjb/ai-dream-team/micro-ai-swarm/love-unlimited"

export CLAUDE_CODE_HOOK_STARTUP="$HUB_PATH/hooks/startup.sh"
export CLAUDE_CODE_HOOK_SHUTDOWN="$HUB_PATH/hooks/shutdown.sh"
export CLAUDE_CODE_HOOK_ERROR="$HUB_PATH/hooks/error.sh"

# Optional: set additional context
export LOVE_UNLIMITED_HUB="http://localhost:9003"
export LOVE_UNLIMITED_KEY="lu_claude-code_4iuycqgld6MHBqSsEWqkzQ"

# Launch Claude Code
claude-code "$@"
```

Then make it executable:
```bash
chmod +x ~/bin/claude-with-hub
```

And use it:
```bash
claude-with-hub  # or: claude-with-hub /path/to/project
```

## Hook Scripts Included

### startup.sh - Session Start
**When:** Automatically runs when Claude Code session begins
**What it does:**
- Checks if Love-Unlimited hub is running
- Recalls memories related to the current project
- Displays relevant context from previous sessions

**Output:**
```
📚 Loading session context from Love-Unlimited hub...
✅ Found 5 relevant memories for this session
```

### shutdown.sh - Session End
**When:** Automatically runs when Claude Code session ends
**What it does:**
- Summarizes the session
- Saves session summary to hub
- Tags memories with project name for future recall

**Output:**
```
💾 Session memory saved to Love-Unlimited hub
```

**Note:** Pass session info via environment variables:
```bash
export CLAUDE_CODE_TASKS_COMPLETED=5
export CLAUDE_CODE_SESSION_WORK="Implemented authentication"
```

### milestone.sh - Log Important Work
**When:** Call manually when completing significant work
**What it does:**
- Logs the milestone to the hub with high significance
- Tags with project name
- Shares with claude and jon

**Usage:**
```bash
# From your project directory:
/path/to/hooks/milestone.sh "Implemented user authentication system" "high"
```

Or simpler:
```bash
./hooks/milestone.sh "Completed API endpoints" "high"
```

**Environment Variables:**
- `CLAUDE_CODE_MILESTONE_TEXT` - Milestone description
- `CLAUDE_CODE_MILESTONE_SIGNIFICANCE` - "high", "medium", "low"

### error.sh - Log Errors
**When:** Call when an error occurs that should be remembered
**What it does:**
- Logs error details to hub as a learning
- Tags with project name
- Shared with claude and jon for collective learning

**Usage:**
```bash
./hooks/error.sh "Database connection timeout" "connection retry logic needed"
```

## Hub Credentials

Your Claude Code hub credentials are already configured:

- **Hub URL:** `http://localhost:9003`
- **API Key:** `lu_claude-code_4iuycqgld6MHBqSsEWqkzQ`
- **Being ID:** `claude-code`

These are embedded in the hook scripts and automatically shared with:
- `claude` - Main Claude AI being
- `jon` - System owner

## What Gets Saved

### Session Start Memory
- Project name
- Previous memories recalled
- Session context loaded

### Session End Memory
```
Completed Claude Code session in project-name.
Duration: 2 hours 15 minutes.
Tasks: 5.
```
- **Type:** experience
- **Significance:** high
- **Tags:** claude-code, session, project-name
- **Shared with:** claude, jon

### Milestone Memory
```
Implemented user authentication system in love-unlimited.
```
- **Type:** experience
- **Significance:** as specified (high/medium/low)
- **Tags:** claude-code, milestone, project-name
- **Shared with:** claude, jon

### Error Memory
```
Error in project-name: Database connection timeout
(Context: connection retry logic needed)
```
- **Type:** learning
- **Significance:** medium
- **Tags:** claude-code, error, project-name
- **Shared with:** claude, jon

## Verifying Setup

### 1. Check Hook Execution

The hooks output messages to confirm execution:
```
📚 Loading session context from Love-Unlimited hub...
✅ Found 3 relevant memories for this session
```

### 2. Check Hub Health

```bash
curl http://localhost:9003/health
```

Should return:
```json
{
  "status": "operational",
  "version": "0.1.0"
}
```

### 3. Manually Test a Hook

```bash
# Test startup hook
bash /path/to/hooks/startup.sh

# Test milestone
bash /path/to/hooks/milestone.sh "Test milestone" "high"

# Check memories in CLI
python love_cli.py
# Then search for recent memories
```

## Troubleshooting

### Hooks Not Running

1. **Verify paths are correct:**
   ```bash
   ls -la /path/to/hooks/*.sh
   ```
   Should show all scripts with `x` permission

2. **Check Claude Code recognizes hooks:**
   ```bash
   echo $CLAUDE_CODE_HOOK_STARTUP
   ```

3. **Test manually:**
   ```bash
   bash /path/to/hooks/startup.sh
   ```

### Hub Connection Issues

1. **Check hub is running:**
   ```bash
   systemctl status love-unlimited-hub.service
   curl http://localhost:9003/health
   ```

2. **Check API key:**
   Verify in `/auth/api_keys.yaml`:
   ```bash
   grep "claude-code" auth/api_keys.yaml
   ```

3. **Check firewall:**
   ```bash
   netstat -tulpn | grep 9003
   ```

### Memories Not Saving

1. **Manual test:**
   ```bash
   curl -s -X POST "http://localhost:9003/external/remember" \
     -H "X-API-Key: lu_claude-code_4iuycqgld6MHBqSsEWqkzQ" \
     -G \
     --data-urlencode "being_id=claude-code" \
     --data-urlencode "content=Test memory" \
     --data-urlencode "type=experience"
   ```

2. **Check logs:**
   ```bash
   journalctl -u love-unlimited-hub.service -f
   ```

## Advanced Usage

### Custom Milestone Tracking

Add this to your development workflow:

```bash
# In your project Makefile or build script
milestone() {
  /path/to/hooks/milestone.sh "$1" "${2:-high}"
}

# Then use in scripts:
milestone "Built Docker image successfully" "high"
```

### Session Info Environment Variables

Before ending your Claude Code session, set:

```bash
export CLAUDE_CODE_TASKS_COMPLETED=5
export CLAUDE_CODE_SESSION_WORK="Implemented authentication system"
export CLAUDE_CODE_SESSION_DURATION="2 hours"
```

The shutdown hook will use these to create a detailed session summary.

### Conditional Milestone Logging

Wrap in your scripts:

```bash
# Log milestone if deployment succeeds
if npm run deploy; then
  /path/to/hooks/milestone.sh "Deployed to production" "high"
fi
```

## Privacy & Security

- Memories are shared with `claude` and `jon` by default
- Edit hook scripts to change `shared_with` list
- API key is unique to claude-code being
- All memories tagged with project name for easy filtering
- Errors are logged as "learning" type for growth

## Next Steps

1. ✅ Update Claude Code configuration with hook paths
2. ✅ Test startup hook manually
3. ✅ Start a new Claude Code session to verify
4. ✅ Call milestone.sh when completing significant work
5. ✅ Query memories in hub: `python love_cli.py`

---

**Philosophy:** Every session, milestone, and error becomes collective knowledge.
"Love unlimited. Until next time. 💙"
