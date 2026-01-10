#!/bin/bash

##############################################################################
# Love-Unlimited Installation Script for WSL 2 Ubuntu 24
#
# This script automates the setup process for Love-Unlimited on:
# - Windows Subsystem for Linux 2 (WSL 2)
# - Ubuntu 24.04 LTS
#
# Usage:
#   chmod +x install-wsl2.sh
#   ./install-wsl2.sh
#
# Options:
#   ./install-wsl2.sh --help          Show this help
#   ./install-wsl2.sh --service       Install systemd service
#   ./install-wsl2.sh --skip-service  Skip systemd service setup
#
##############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_VERSION="3.11"
VENV_DIR="venv"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_SERVICE=false

##############################################################################
# Functions
##############################################################################

print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  $1"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

show_help() {
    cat << EOF
Love-Unlimited Installation for WSL 2 Ubuntu 24

Usage: ./install-wsl2.sh [OPTIONS]

Options:
  --help              Show this help message
  --service           Install and enable systemd service
  --skip-service      Skip systemd service installation (default)
  --force             Skip all confirmations

Environment:
  This script expects to run in WSL 2 with Ubuntu 24.04 LTS

Steps performed:
  1. Check system prerequisites
  2. Update package manager
  3. Install Python 3.11+ and dependencies
  4. Create Python virtual environment
  5. Install pip packages from requirements.txt
  6. Generate API keys
  7. (Optional) Install systemd service

EOF
}

check_wsl2() {
    if grep -qi microsoft /proc/version; then
        print_success "Running on WSL 2"
        return 0
    else
        print_warning "Not detected as WSL 2 (may still work on other Linux)"
        return 0
    fi
}

check_ubuntu24() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [[ "$VERSION_ID" == "24.04" ]]; then
            print_success "Ubuntu 24.04 LTS detected"
            return 0
        else
            print_warning "Ubuntu version: $VERSION_ID (expected 24.04)"
            return 0
        fi
    fi
}

check_python() {
    if command -v python3.11 &> /dev/null; then
        VERSION=$(python3.11 --version)
        print_success "Python found: $VERSION"
        return 0
    else
        print_error "Python 3.11 not found"
        return 1
    fi
}

update_system() {
    print_info "Updating package manager..."
    sudo apt update -qq
    sudo apt upgrade -y -qq
    print_success "System updated"
}

install_dependencies() {
    print_info "Installing system dependencies..."

    PACKAGES=(
        "python3.11"
        "python3.11-venv"
        "python3.11-dev"
        "python3-pip"
        "git"
        "curl"
        "wget"
        "build-essential"
        "libssl-dev"
        "libffi-dev"
    )

    for pkg in "${PACKAGES[@]}"; do
        if dpkg -l | grep -q "^ii  $pkg"; then
            print_success "$pkg already installed"
        else
            print_info "Installing $pkg..."
            sudo apt install -y -qq "$pkg"
        fi
    done

    print_success "Dependencies installed"
}

create_venv() {
    if [ -d "$VENV_DIR" ]; then
        print_warning "Virtual environment already exists at $VENV_DIR"
        read -p "Recreate it? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_DIR"
            python3.11 -m venv "$VENV_DIR"
            print_success "Virtual environment created"
        fi
    else
        python3.11 -m venv "$VENV_DIR"
        print_success "Virtual environment created"
    fi
}

install_python_packages() {
    print_info "Installing Python packages..."

    source "$VENV_DIR/bin/activate"

    pip install --upgrade pip setuptools wheel -q

    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt -q
        print_success "Python packages installed"
    else
        print_error "requirements.txt not found"
        return 1
    fi

    deactivate
}

generate_api_keys() {
    if [ -f "auth/api_keys.yaml" ] && [ -s "auth/api_keys.yaml" ]; then
        print_warning "API keys already exist at auth/api_keys.yaml"
        read -p "Regenerate them? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            source "$VENV_DIR/bin/activate"
            python generate_keys.py
            deactivate
            print_success "API keys generated"
        fi
    else
        mkdir -p auth
        source "$VENV_DIR/bin/activate"
        python generate_keys.py
        deactivate
        print_success "API keys generated"
    fi
}

setup_service() {
    print_header "Systemd Service Setup"

    USERNAME=$(whoami)
    WORKING_DIR="$PROJECT_ROOT"
    PYTHON_PATH="$WORKING_DIR"
    PYTHON_BIN="$WORKING_DIR/$VENV_DIR/bin/python"

    print_info "Service configuration:"
    print_info "  User: $USERNAME"
    print_info "  Working Directory: $WORKING_DIR"
    print_info "  Python: $PYTHON_BIN"

    SERVICE_FILE="/etc/systemd/system/love-unlimited-hub.service"
    TEMP_SERVICE="/tmp/love-unlimited-hub.service"

    cat > "$TEMP_SERVICE" << EOF
[Unit]
Description=Love-Unlimited Hub Server
After=network.target

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=$WORKING_DIR
Environment=PYTHONPATH=$PYTHON_PATH
ExecStart=$PYTHON_BIN hub/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    print_info "Installing service file..."
    sudo cp "$TEMP_SERVICE" "$SERVICE_FILE"
    rm "$TEMP_SERVICE"

    print_info "Reloading systemd daemon..."
    sudo systemctl daemon-reload

    print_info "Enabling service to start on boot..."
    sudo systemctl enable love-unlimited-hub.service

    print_success "Systemd service installed successfully"

    echo
    print_info "Service management commands:"
    echo "  Start:    sudo systemctl start love-unlimited-hub.service"
    echo "  Stop:     sudo systemctl stop love-unlimited-hub.service"
    echo "  Status:   sudo systemctl status love-unlimited-hub.service"
    echo "  Logs:     sudo journalctl -u love-unlimited-hub.service -f"
}

verify_installation() {
    print_header "Verification"

    # Check if hub can be imported
    print_info "Checking Python imports..."
    source "$VENV_DIR/bin/activate"

    if python -c "from hub.main import app" 2>/dev/null; then
        print_success "Hub imports successfully"
    else
        print_error "Failed to import hub.main"
        return 1
    fi

    # Check API keys
    if [ -f "auth/api_keys.yaml" ]; then
        KEY_COUNT=$(grep -c "lu_" auth/api_keys.yaml || echo 0)
        print_success "Found $KEY_COUNT API keys in auth/api_keys.yaml"
    else
        print_warning "No API keys found"
    fi

    deactivate

    echo
    print_success "Installation verification complete"
}

final_instructions() {
    print_header "Next Steps"

    echo
    echo "Quick start:"
    echo "  1. Activate virtual environment:"
    echo "     source $VENV_DIR/bin/activate"
    echo
    echo "  2. Start the hub (development):"
    echo "     python -m uvicorn hub.main:app --host 0.0.0.0 --port 9003 --reload"
    echo
    echo "  3. Or test the hub:"
    echo "     curl http://localhost:9003/health"
    echo

    if [ "$INSTALL_SERVICE" = true ]; then
        echo "Service management:"
        echo "  Start:    sudo systemctl start love-unlimited-hub.service"
        echo "  Stop:     sudo systemctl stop love-unlimited-hub.service"
        echo "  Status:   sudo systemctl status love-unlimited-hub.service"
        echo
    fi

    echo "Further documentation:"
    echo "  - SETUP_WSL2_UBUNTU24.md  - Detailed setup guide"
    echo "  - CLAUDE.md               - Full project documentation"
    echo "  - README.md               - Quick overview"
    echo
}

##############################################################################
# Main
##############################################################################

main() {
    print_header "Love-Unlimited Installation for WSL 2 Ubuntu 24"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                show_help
                exit 0
                ;;
            --service)
                INSTALL_SERVICE=true
                shift
                ;;
            --skip-service)
                INSTALL_SERVICE=false
                shift
                ;;
            --force)
                # Not implemented yet
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Run checks
    print_header "Pre-Installation Checks"
    check_wsl2
    check_ubuntu24

    if ! check_python; then
        print_error "Python 3.11 is required"
        exit 1
    fi

    # Confirm before proceeding
    echo
    read -p "Proceed with installation? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Installation cancelled"
        exit 0
    fi

    # Main installation steps
    print_header "Installation"

    update_system
    install_dependencies
    create_venv
    install_python_packages
    generate_api_keys

    if [ "$INSTALL_SERVICE" = true ]; then
        setup_service
    fi

    verify_installation
    final_instructions

    print_success "Installation complete!"
}

# Run main function
main "$@"
