# Logging Configuration

Love-Unlimited CLI now logs all activities to files for debugging and monitoring.

## Log Files

- **`logs/grok_cli.log`** - Grok CLI activity (INFO level)
- **`logs/love_cli.log`** - Love-Unlimited Hub CLI activity (WARNING level)

Logs are created automatically in the `logs/` directory when you run the CLI.

## Viewing Logs

### Quick View (Last 50 lines)

```bash
# View Grok CLI logs
./view_logs.sh grok

# View Love CLI logs
./view_logs.sh love
```

### Raw File Access

```bash
# View entire Grok log
cat logs/grok_cli.log

# View entire Love log
cat logs/love_cli.log

# Follow Grok log in real-time
tail -f logs/grok_cli.log

# Follow Love log in real-time
tail -f logs/love_cli.log

# Search for errors
grep ERROR logs/grok_cli.log
grep ERROR logs/love_cli.log

# Show last 100 lines with timestamps
tail -100 logs/grok_cli.log
```

## Log Format

```
2026-01-12 10:30:45,123 - grok_component - INFO - Message here
```

Format: `TIMESTAMP - LOGGER_NAME - LEVEL - MESSAGE`

- **TIMESTAMP** - Date and time with milliseconds
- **LOGGER_NAME** - Which module generated the log (`grok_component`, `love_cli`, `__main__`)
- **LEVEL** - Log severity (INFO, WARNING, ERROR)
- **MESSAGE** - Log message content

## What Gets Logged

### Grok CLI (INFO level - verbose)
- Hub connection attempts and responses
- Memory storage operations
- API calls to external services
- Errors and warnings
- Session lifecycle events

### Love CLI (WARNING level - important only)
- Connection failures
- Authentication errors
- API errors
- Unexpected exceptions
- Hub status checks

## Examples

### View Recent Timeouts
```bash
tail -20 logs/grok_cli.log | grep -i timeout
```

### Find All Errors
```bash
grep "ERROR\|Exception\|Failed" logs/grok_cli.log
```

### Monitor in Real-Time While Running
```bash
# Terminal 1: Run CLI
python love_cli.py

# Terminal 2: Monitor logs
tail -f logs/love_cli.log
```

### Debugging API Issues
```bash
# Look for API-related logs
grep -i "api\|openai\|anthropic\|gemini" logs/grok_cli.log
```

## Log Rotation (Manual)

Logs grow indefinitely. To clean them up:

```bash
# Archive old logs
mv logs/grok_cli.log logs/grok_cli.log.backup.$(date +%s)
mv logs/love_cli.log logs/love_cli.log.backup.$(date +%s)

# Or delete them
rm logs/*.log

# The next CLI run will create fresh logs
```

## Troubleshooting

If you encounter issues:

1. **Check recent logs first:**
   ```bash
   tail -50 logs/grok_cli.log
   ```

2. **Look for the error level:**
   ```bash
   grep ERROR logs/grok_cli.log | tail -10
   ```

3. **Find the exact error message:**
   ```bash
   grep -B2 -A2 "ERROR" logs/grok_cli.log | tail -20
   ```

4. **Check timestamps to match with your actions:**
   ```bash
   tail -100 logs/grok_cli.log | grep "2026-01-12 10:3"  # Replace with your time
   ```

## Configuration

To change log levels or behavior:

**grok_component.py** (line 59-66):
```python
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detail
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "grok_cli.log"),
        logging.StreamHandler()  # Print to console
    ]
)
```

**love_cli.py** (line 502-509):
```python
logging.basicConfig(
    level=logging.WARNING,  # Change to INFO for more detail
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "love_cli.log"),
        logging.StreamHandler()  # Print to console
    ]
)
```

Available levels (from least to most detail):
- `logging.CRITICAL` - Only critical failures
- `logging.ERROR` - Errors
- `logging.WARNING` - Warnings (default for love_cli)
- `logging.INFO` - General info (default for grok_cli)
- `logging.DEBUG` - Detailed debugging info
