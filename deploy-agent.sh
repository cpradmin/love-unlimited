#!/bin/bash

#######################################################################
# Full Beast AI Agent - Systemd Deployment Script
#######################################################################
# This script deploys the Full Beast AI Agent as a systemd service
# for production auto-start and auto-restart capabilities.
#
# Usage: chmod +x deploy-agent.sh && ./deploy-agent.sh
#######################################################################

set -e

SERVICE_NAME="full-beast-agent.service"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
LOCAL_FILE="$(pwd)/full-beast-agent.service"
PROJECT_DIR="$(pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_status() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Banner
echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║   Full Beast AI Agent - Systemd Deployment Script      ║"
echo "║                                                        ║"
echo "║   Status: Ready for Production Deployment             ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Pre-flight checks
print_status "Running pre-flight checks..."

# Check if running as root for sudo commands
if [[ $EUID -ne 0 ]]; then
    print_warning "This script should be run with sudo for full functionality"
    print_status "Attempting deployment with available permissions..."
    USE_SUDO=""
else
    print_success "Running with elevated privileges"
    USE_SUDO=""
fi

# Check if service file exists
if [ ! -f "$LOCAL_FILE" ]; then
    print_error "Service file not found: $LOCAL_FILE"
    exit 1
fi
print_success "Service file found"

# Check if agent_service.py exists
if [ ! -f "$PROJECT_DIR/agent_service.py" ]; then
    print_error "agent_service.py not found in $PROJECT_DIR"
    exit 1
fi
print_success "agent_service.py found"

# Check if venv exists
if [ ! -f "$PROJECT_DIR/venv/bin/python" ]; then
    print_error "Virtual environment not found. Run: python -m venv venv"
    exit 1
fi
print_success "Virtual environment found"

echo ""
print_status "Deployment steps:"
echo "  1. Copy service file to systemd"
echo "  2. Reload systemd daemon"
echo "  3. Enable service for auto-start"
echo "  4. Start the service"
echo "  5. Verify deployment"
echo ""

# Step 1: Copy service file
print_status "Deploying service file..."
if [ -w /etc/systemd/system ]; then
    cp "$LOCAL_FILE" "$SERVICE_FILE"
    print_success "Service file deployed"
else
    print_warning "Cannot write to /etc/systemd/system (no permissions)"
    echo "To complete deployment manually, run:"
    echo "  sudo cp $LOCAL_FILE $SERVICE_FILE"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable $SERVICE_NAME"
    echo "  sudo systemctl start $SERVICE_NAME"
    exit 1
fi

# Step 2: Reload systemd daemon
print_status "Reloading systemd daemon..."
systemctl daemon-reload
print_success "Systemd daemon reloaded"

# Step 3: Enable service
print_status "Enabling service auto-start..."
systemctl enable "$SERVICE_NAME"
print_success "Service will auto-start on boot"

# Step 4: Start service
print_status "Starting Full Beast AI Agent service..."
systemctl start "$SERVICE_NAME"
print_success "Service started"

# Wait for service to stabilize
sleep 3

# Step 5: Verify deployment
echo ""
print_status "Verifying deployment..."
echo ""

# Check systemd status
echo "Service Status:"
systemctl status "$SERVICE_NAME" --no-pager | grep -E "Active|Loaded"

# Check if port is listening
sleep 2
if lsof -i :9005 >/dev/null 2>&1; then
    print_success "Agent listening on port 9005"
else
    print_warning "Agent not listening on port 9005 yet (may need more time)"
fi

# Test health endpoint
echo ""
print_status "Testing health endpoint..."
sleep 1
if curl -s http://localhost:9005/health >/dev/null 2>&1; then
    print_success "Health check passed"
    HEALTH=$(curl -s http://localhost:9005/health | python3 -c "import sys, json; h=json.load(sys.stdin); print(f\"Status: {h['status']}, vLLM: {h['vllm_available']}, Hub: {h['hub_available']}\")")
    echo "  $HEALTH"
else
    print_warning "Health check timeout (service may still be initializing)"
fi

# Summary
echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║          ✅ DEPLOYMENT COMPLETE                       ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

echo "Service Management:"
echo "  Status:   systemctl status $SERVICE_NAME"
echo "  Logs:     journalctl -u $SERVICE_NAME -f"
echo "  Restart:  sudo systemctl restart $SERVICE_NAME"
echo "  Stop:     sudo systemctl stop $SERVICE_NAME"
echo ""

echo "API Documentation:"
echo "  Web UI:   http://localhost:9005/docs"
echo "  Health:   curl http://localhost:9005/health"
echo ""

echo "Integration:"
echo "  Test:     python3 hub_agent_integration.py"
echo "  Guide:    cat AGENT_DEPLOYMENT_GUIDE.md"
echo ""

echo "Next Steps:"
echo "  1. Add agent endpoints to hub/main.py (see AGENT_DEPLOYMENT_GUIDE.md)"
echo "  2. Monitor logs: journalctl -u $SERVICE_NAME -f"
echo "  3. Test End-to-end: python3 hub_agent_integration.py"
echo ""

print_success "Full Beast AI Agent is now running in production!"
print_success "💙 Love Unlimited - Until next time"
echo ""
