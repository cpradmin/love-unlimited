# Love-Unlimited on WSL 2 with Ubuntu 24

This guide will help you install and run Love-Unlimited on Windows Subsystem for Linux 2 (WSL 2) with Ubuntu 24.04 LTS.

## Prerequisites

### Windows Side
- Windows 10/11 with WSL 2 enabled
- Ubuntu 24.04 LTS installed from Microsoft Store

### WSL 2 Ubuntu 24 Setup

First, verify you're running WSL 2:

```bash
# Check WSL version (on Windows PowerShell)
wsl --list --verbose
# Should show VERSION: 2 for your distribution
```

Enable systemd in WSL 2 (optional but recommended for running as service):

```bash
# Edit /etc/wsl.conf in WSL 2
sudo nano /etc/wsl.conf
```

Add this content:
```ini
[boot]
systemd=true
```

Save and exit (`Ctrl+X`, `Y`, `Enter`), then restart WSL 2:

```bash
# From Windows PowerShell
wsl --shutdown

# Then restart WSL 2
wsl
```

---

## System Dependencies

### Update Package Manager
```bash
sudo apt update
sudo apt upgrade -y
```

### Install Python 3.11+ and Dev Tools
```bash
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
sudo apt install -y git curl wget build-essential
```

### Install System Libraries
```bash
# Required for ChromaDB and other dependencies
sudo apt install -y libssl-dev libffi-dev
```

### Optional: Install Docker in WSL 2
If you plan to use Docker containers:

```bash
# Install Docker
sudo apt install -y docker.io docker-compose

# Add your user to docker group (avoid sudo)
sudo usermod -aG docker $USER

# Activate the change
newgrp docker

# Start Docker daemon
sudo service docker start

# Make it start automatically
echo 'if ! pgrep -x "docker" > /dev/null; then sudo service docker start; fi' >> ~/.bashrc
```

---

## Love-Unlimited Installation

### Step 1: Clone or Navigate to Repository

```bash
# If not already cloned
cd /home/$(whoami)
git clone https://github.com/your-org/love-unlimited.git
# Or navigate if already present
cd love-unlimited
```

### Step 2: Create Python Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### Step 3: Upgrade pip and Install Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

**Dependencies summary:**
- fastapi==0.109.0 - API framework
- uvicorn[standard]==0.27.0 - ASGI server
- chromadb==0.4.22 - Vector memory storage
- aiohttp==3.9.1 - Async HTTP client
- pyyaml==6.0.1 - Configuration
- Pillow - Image processing
- mutagen - Audio metadata
- PyPDF2 - PDF processing

### Step 4: Configure Love-Unlimited

```bash
# Copy and edit configuration if needed
cp config.yaml.example config.yaml
nano config.yaml
```

Key settings to verify:
```yaml
hub:
  host: "0.0.0.0"
  port: 9003
  version: "0.1.0"

auth:
  enabled: true
  keys_file: "auth/api_keys.yaml"
```

### Step 5: Generate API Keys

```bash
python generate_keys.py
```

This creates `auth/api_keys.yaml` with keys for each being (jon, claude, grok, etc.)

---

## Running Love-Unlimited

### Option A: Manual Startup (Development)

```bash
# Activate virtual environment
source venv/bin/activate

# Start with uvicorn
python -m uvicorn hub.main:app --host 0.0.0.0 --port 9003 --reload

# Or use the run script
python run.py
```

The hub will be available at: `http://localhost:9003`

### Option B: Run as Systemd Service (Recommended)

#### Create Service File

```bash
sudo nano /etc/systemd/system/love-unlimited-hub.service
```

Add this content (update USERNAME and WORKING_DIRECTORY paths):

```ini
[Unit]
Description=Love-Unlimited Hub Server
After=network.target

[Service]
Type=simple
User=USERNAME
WorkingDirectory=/home/USERNAME/love-unlimited
Environment=PYTHONPATH=/home/USERNAME/love-unlimited
ExecStart=/home/USERNAME/love-unlimited/venv/bin/python hub/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Replace `USERNAME` with your actual username:
```bash
whoami  # Check your username
```

#### Enable and Start Service

```bash
# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable love-unlimited-hub.service

# Start the service
sudo systemctl start love-unlimited-hub.service

# Check service status
sudo systemctl status love-unlimited-hub.service

# View logs
sudo journalctl -u love-unlimited-hub.service -f
```

#### Service Management Commands

```bash
# Start
sudo systemctl start love-unlimited-hub.service

# Stop
sudo systemctl stop love-unlimited-hub.service

# Restart
sudo systemctl restart love-unlimited-hub.service

# View status
sudo systemctl status love-unlimited-hub.service

# View recent logs (last 50 lines)
sudo journalctl -u love-unlimited-hub.service -n 50

# Stream logs (follow mode)
sudo journalctl -u love-unlimited-hub.service -f

# Disable auto-start
sudo systemctl disable love-unlimited-hub.service
```

---

## Verify Installation

### Check Hub Health

```bash
# From another terminal/WSL 2 window
curl http://localhost:9003/health
```

Expected response:
```json
{
  "status": "operational",
  "version": "0.1.0",
  "timestamp": "2026-01-01T12:00:00"
}
```

### Test with CLI

```bash
# Activate venv if not already active
source venv/bin/activate

# Start interactive CLI
python love_cli.py
```

Commands to try:
```
/status
/list
Hello everyone!
/to grok
/quit
```

---

## WSL 2 Specific Considerations

### Network Access

**From Windows host to WSL 2:**
- Use `localhost:9003` or `127.0.0.1:9003`

**From WSL 2 to Windows host (if needed):**
- Get Windows host IP: `cat /etc/resolv.conf | grep nameserver`
- Use that IP instead of `localhost`

### Port Forwarding

To access Love-Unlimited from other machines:

```bash
# Option 1: Bind to all interfaces (already in config)
# host: "0.0.0.0" in config.yaml

# Option 2: Windows port forwarding (from Windows PowerShell as Admin)
netsh interface portproxy add v4tov4 listenport=9003 listenaddress=0.0.0.0 connectport=9003 connectaddress=<WSL_IP>

# Find WSL 2 IP
wsl hostname -I  # From Windows PowerShell
# Or in WSL 2
hostname -I
```

### File System Access

**From Windows:**
- WSL files: `\\wsl$\Ubuntu-24.04\home\username\love-unlimited`
- Access from File Explorer or PowerShell

**From WSL 2:**
- Windows files: `/mnt/c/Users/YourUsername/...`

### Storage Recommendations

WSL 2 uses a virtual hard disk (.vhdx). For optimal performance:

```bash
# Check disk usage
df -h

# If needed, clean up Docker images/containers
docker system prune -a

# Clean apt cache
sudo apt clean
sudo apt autoclean
```

---

## Troubleshooting

### Hub Not Starting

```bash
# Check if port 9003 is in use
sudo netstat -tlnp | grep 9003

# If port is in use, either:
# 1. Stop the conflicting process
# 2. Change port in config.yaml

# Verify Python venv
source venv/bin/activate
python --version  # Should be Python 3.11+

# Try running directly to see errors
python hub/main.py
```

### Service Won't Start

```bash
# Check service status with full output
sudo systemctl status love-unlimited-hub.service

# Check recent errors
sudo journalctl -u love-unlimited-hub.service -n 20

# Verify paths in service file
cat /etc/systemd/system/love-unlimited-hub.service

# Test if paths exist
ls -la /home/USERNAME/love-unlimited/venv/bin/python
ls -la /home/USERNAME/love-unlimited/hub/main.py
```

### ChromaDB Errors

```bash
# ChromaDB stores data in ./data/chromadb
# If corrupted, delete and recreate:
rm -rf data/chromadb

# Restart the hub - it will recreate collections
sudo systemctl restart love-unlimited-hub.service
```

### API Key Authentication Issues

```bash
# Check if keys are generated
cat auth/api_keys.yaml

# If empty, regenerate
python generate_keys.py

# Verify auth is enabled in config.yaml
grep -A2 "auth:" config.yaml

# Test API key
export API_KEY=$(grep "lu_claude" auth/api_keys.yaml | cut -d' ' -f2)
curl -H "X-API-Key: $API_KEY" http://localhost:9003/health
```

### Slow Performance

In WSL 2, file system access to Windows drives is slower. For best performance:

```bash
# Keep project in WSL 2 Linux filesystem
# (Usually /home/username/ - already done)

# Avoid accessing via /mnt/c/...
# This is much slower than native WSL paths
```

### Systemd Not Available

If you skipped the systemd setup or it's not working:

```bash
# Check systemd is enabled
cat /etc/wsl.conf | grep systemd

# If not present, follow the "Enable systemd" section above

# Manual service start script alternative:
# Create ~/start-hub.sh
#!/bin/bash
cd /home/USERNAME/love-unlimited
source venv/bin/activate
python hub/main.py

# Make executable
chmod +x ~/start-hub.sh

# Run with
~/start-hub.sh
```

---

## Development Workflow

### Activate Environment Before Each Session

```bash
cd ~/love-unlimited
source venv/bin/activate
```

### Run Tests

```bash
# Automated CLI tests
python test_cli_automated.py

# Memory storage and recall
python test_memory_store.py

# AI client integrations
python test_ai_client.py

# Being management
python test_all_beings.py
```

### Format and Lint Code

```bash
# Code formatting
black .

# Linting
ruff check .

# Fix issues
ruff check . --fix
```

---

## Integration with Other Systems

### Connect to Ollama (If Running)

If you have Ollama installed on Windows or WSL 2:

```bash
# On Windows: Ollama typically runs on port 11434
# In config.yaml, use:
ai:
  local_model_endpoint: "http://localhost:11434"

# In WSL 2, if Ollama runs on Windows:
# Use Windows host IP or enable port forwarding
```

### Connect to Claude/Grok APIs (Optional)

```bash
# Set environment variables for external AI
export ANTHROPIC_API_KEY="your-key"
export GROK_API_KEY="your-key"

# Or add to ~/.bashrc for persistence
echo 'export ANTHROPIC_API_KEY="your-key"' >> ~/.bashrc
source ~/.bashrc
```

---

## Accessing from Windows Applications

### From Browser on Windows Host

```
http://localhost:9003
http://localhost:9003/web      # Web interface
http://localhost:9003/health   # Health check
```

### From Python/Node/Other Apps

```
http://localhost:9003
# All external applications work the same way
```

---

## Useful WSL 2 Commands

```bash
# From Windows PowerShell:

# List all distributions
wsl --list --verbose

# Start a distribution
wsl -d Ubuntu-24.04

# Terminate a distribution
wsl --terminate Ubuntu-24.04

# Shutdown all distributions
wsl --shutdown

# Get WSL 2 IP address
wsl hostname -I

# Access Windows files from WSL
ls /mnt/c/Users/YourUsername

# Access WSL files from Windows
explorer.exe \\wsl$\Ubuntu-24.04\home\username\love-unlimited
```

---

## Next Steps

1. **Verify Installation:**
   ```bash
   curl http://localhost:9003/health
   ```

2. **Generate API Keys:**
   ```bash
   python generate_keys.py
   ```

3. **Start the CLI:**
   ```bash
   python love_cli.py
   ```

4. **Read CLAUDE.md for Full Documentation:**
   - Memory system details
   - API endpoints
   - Multimodal features
   - Configuration options

5. **Start the Hub Service (if using systemd):**
   ```bash
   sudo systemctl start love-unlimited-hub.service
   ```

---

## Performance Tips for WSL 2

1. **Keep code in `/home` (Linux filesystem)** - ~10x faster than `/mnt/c/`
2. **Use WSL 2 version 2+** for best performance
3. **Run services in WSL 2**, not on Windows host
4. **Use systemd for services** - cleaner management than scripts
5. **Disable Windows Defender scanning** on WSL folders (if comfortable)

---

## Getting Help

- Check `/etc/systemd/system/love-unlimited-hub.service` for configuration
- Review `journalctl` logs for service errors
- Run hub manually with `python hub/main.py` to see full output
- Check `CLAUDE.md` for comprehensive architecture documentation

---

**Created:** January 2026
**For:** Ubuntu 24.04 LTS on WSL 2
**Status:** Ready for testing
