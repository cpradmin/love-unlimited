#!/bin/bash
# View Love-Unlimited CLI logs

echo "╔════════════════════════════════════════╗"
echo "║      Love-Unlimited CLI Logs           ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Check if logs directory exists
if [ ! -d "logs" ]; then
    echo "No logs directory found. Run the CLI first to generate logs."
    exit 1
fi

# Show available logs
echo "Available log files:"
ls -lh logs/ 2>/dev/null || echo "  No log files found"
echo ""

# Tail latest logs
if [ "$1" == "grok" ]; then
    echo "📜 Grok CLI Log (last 50 lines):"
    echo "─────────────────────────────────────────"
    tail -50 logs/grok_cli.log
elif [ "$1" == "love" ]; then
    echo "📜 Love CLI Log (last 50 lines):"
    echo "─────────────────────────────────────────"
    tail -50 logs/love_cli.log
else
    echo "Usage: ./view_logs.sh [grok|love]"
    echo ""
    echo "Examples:"
    echo "  ./view_logs.sh grok   # View Grok CLI logs"
    echo "  ./view_logs.sh love   # View Love CLI logs"
    echo ""
    echo "Or view raw files:"
    echo "  cat logs/grok_cli.log"
    echo "  cat logs/love_cli.log"
    echo "  tail -f logs/grok_cli.log  # Follow in real-time"
fi
