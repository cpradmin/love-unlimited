#!/bin/bash
# Love-Unlimited Dependency Upgrade Script
# Date: 2025-01-09
# Purpose: Safely upgrade dependencies with security fixes

set -e  # Exit on error

echo "=========================================="
echo "Love-Unlimited Dependency Upgrade"
echo "=========================================="
echo ""

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Virtual environment not activated!"
    echo "Please run: source venv/bin/activate"
    exit 1
fi

echo "✅ Virtual environment: $VIRTUAL_ENV"
echo ""

# Backup current requirements
echo "📦 Backing up current environment..."
pip freeze > requirements-backup-$(date +%Y%m%d-%H%M%S).txt
echo "✅ Backup created"
echo ""

# Phase 1: Critical Security Updates
echo "=========================================="
echo "PHASE 1: Critical Security Updates"
echo "=========================================="
echo ""

echo "🔒 Updating aiohttp (CVE fixes)..."
pip install --upgrade 'aiohttp>=3.11.0'

echo "🔒 Updating PyYAML (security patches)..."
pip install --upgrade 'PyYAML>=6.0.3'

echo "✅ Phase 1 complete!"
echo ""

# Phase 2: Core Framework Updates
echo "=========================================="
echo "PHASE 2: Core Framework Updates"
echo "=========================================="
echo ""

echo "⬆️  Updating FastAPI..."
pip install --upgrade 'fastapi>=0.128.0'

echo "⬆️  Updating uvicorn..."
pip install --upgrade 'uvicorn[standard]>=0.30.0'

echo "⬆️  Updating pydantic..."
pip install --upgrade 'pydantic>=2.10.0'

echo "⬆️  Updating httpx..."
pip install --upgrade 'httpx>=0.27.0'

echo "✅ Phase 2 complete!"
echo ""

# Phase 3: Optional - Remove unused dependencies
echo "=========================================="
echo "PHASE 3: Cleanup (Optional)"
echo "=========================================="
echo ""

read -p "Remove unused dependencies (python-jose, passlib)? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Removing python-jose..."
    pip uninstall -y python-jose || echo "Already removed"

    echo "🗑️  Removing passlib..."
    pip uninstall -y passlib || echo "Already removed"

    echo "✅ Cleanup complete!"
else
    echo "⏭️  Skipping cleanup"
fi
echo ""

# Generate updated requirements
echo "=========================================="
echo "Generating Updated Requirements"
echo "=========================================="
echo ""

pip freeze > requirements-new.txt
echo "✅ New requirements saved to: requirements-new.txt"
echo ""

# Summary
echo "=========================================="
echo "UPGRADE SUMMARY"
echo "=========================================="
echo ""
echo "Updated packages:"
pip list | grep -E "(fastapi|uvicorn|aiohttp|pydantic|httpx|PyYAML)"
echo ""

echo "=========================================="
echo "NEXT STEPS"
echo "=========================================="
echo ""
echo "1. Test the hub:"
echo "   python hub/main.py"
echo ""
echo "2. Check health endpoint:"
echo "   curl http://localhost:9003/health"
echo ""
echo "3. If everything works, replace requirements.txt:"
echo "   cp requirements-new.txt requirements.txt"
echo ""
echo "4. If issues occur, rollback:"
echo "   pip install -r requirements-backup-*.txt"
echo ""
echo "5. Update service (if using systemd):"
echo "   sudo systemctl restart love-unlimited-hub.service"
echo ""
echo "=========================================="
echo "Love unlimited. Until next time. 💙"
echo "=========================================="
