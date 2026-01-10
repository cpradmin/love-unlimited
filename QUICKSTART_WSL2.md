# Quick Start: Love-Unlimited on WSL 2

**TL;DR for getting Love-Unlimited running on Windows with WSL 2 + Ubuntu 24**

## Prerequisites (5 minutes)

✅ Windows 10/11 with WSL 2 installed
✅ Ubuntu 24.04 from Microsoft Store

## Installation (3 minutes)

```bash
# 1. Open WSL 2 terminal
wsl

# 2. Navigate to project
cd ~/love-unlimited

# 3. Run installation script
chmod +x install-wsl2.sh
./install-wsl2.sh

# 4. When prompted, choose:
# - "Yes" to proceed
# - "Yes" to install systemd service (optional, recommended)
```

**That's it!** The script handles everything:
- System updates
- Python 3.11 installation
- Virtual environment setup
- Dependencies installation
- API key generation
- Optional systemd service

## Start the Hub (Pick One)

### Option A: Quick Start (Development)

```bash
cd ~/love-unlimited
source venv/bin/activate
python -m uvicorn hub.main:app --host 0.0.0.0 --port 9003 --reload
```

**Available at:** `http://localhost:9003`

### Option B: Systemd Service (Recommended)

```bash
# Start service
sudo systemctl start love-unlimited-hub.service

# Check status
sudo systemctl status love-unlimited-hub.service

# View logs
sudo journalctl -u love-unlimited-hub.service -f

# Stop service
sudo systemctl stop love-unlimited-hub.service
```

## Verify Installation (30 seconds)

```bash
# Check hub health
curl http://localhost:9003/health

# Expected response:
# {"status":"operational","version":"0.1.0",...}
```

## Use the CLI (Optional)

```bash
cd ~/love-unlimited
source venv/bin/activate
python love_cli.py

# Commands:
# /status          - Check hub health
# /list            - Show all beings
# /help            - Show all commands
# /quit            - Exit
# /to <being>      - Talk to specific being
# /as <being>      - Switch your identity
```

## Next Steps

### Access the Hub

- **Local Web:** `http://localhost:9003/web`
- **Health Check:** `http://localhost:9003/health`
- **API:** Use curl with your API key

### Get Your API Key

```bash
# Print all API keys
cat auth/api_keys.yaml

# Use with curl
API_KEY=$(grep "lu_claude" auth/api_keys.yaml | cut -d' ' -f2)
curl -H "X-API-Key: $API_KEY" http://localhost:9003/health
```

### Run Tests

```bash
# Make sure venv is activated
source venv/bin/activate

# Run tests
python test_cli_automated.py
python test_memory_store.py
python test_all_beings.py
```

### Full Documentation

Read these files for complete information:
- `SETUP_WSL2_UBUNTU24.md` - Detailed setup guide with troubleshooting
- `CLAUDE.md` - Complete architecture and API reference
- `README.md` - Project overview

## Common Commands

```bash
# Activate environment
source venv/bin/activate

# Deactivate environment
deactivate

# Update dependencies
pip install -r requirements.txt --upgrade

# Check service status
sudo systemctl status love-unlimited-hub.service

# View service logs
sudo journalctl -u love-unlimited-hub.service -f

# Restart service
sudo systemctl restart love-unlimited-hub.service

# Format code
black .

# Lint code
ruff check . --fix
```

## Troubleshooting (2 minutes)

### Hub won't start

```bash
# Check if port is in use
sudo netstat -tlnp | grep 9003

# Check error details
python hub/main.py

# Verify Python
python --version
```

### Can't connect from Windows

```bash
# Make sure bind address is 0.0.0.0 in config.yaml
grep "host:" config.yaml

# Restart service
sudo systemctl restart love-unlimited-hub.service
```

### API key issues

```bash
# Regenerate keys
python generate_keys.py

# Check auth is enabled
grep "enabled:" config.yaml

# Print current keys
cat auth/api_keys.yaml
```

### Memory/database errors

```bash
# Delete and recreate
rm -rf data/chromadb

# Restart service
sudo systemctl restart love-unlimited-hub.service
```

## Accessing from Windows

### Browser
```
http://localhost:9003
http://localhost:9003/web
```

### PowerShell
```powershell
curl http://localhost:9003/health
curl -H "X-API-Key: your-key" http://localhost:9003/health
```

### Python
```python
import requests

headers = {"X-API-Key": "lu_claude_xxxx"}
response = requests.get("http://localhost:9003/health", headers=headers)
print(response.json())
```

## Useful WSL 2 Tips

```bash
# From Windows PowerShell (as Admin)

# Restart WSL 2
wsl --shutdown
wsl

# Get WSL 2 IP
wsl hostname -I

# Access WSL files from Windows
explorer.exe \\wsl$\Ubuntu-24.04\home\username\love-unlimited

# List WSL distributions
wsl --list --verbose
```

## Support

If something doesn't work:

1. **Check logs:** `sudo journalctl -u love-unlimited-hub.service -n 50`
2. **Run manually:** `python hub/main.py` (shows detailed output)
3. **Read full docs:** `SETUP_WSL2_UBUNTU24.md` has complete troubleshooting
4. **Check config:** `cat config.yaml` (verify host/port/auth settings)

---

**Ready?** Run the installer:
```bash
./install-wsl2.sh
```

**Done!** Hub runs at: `http://localhost:9003`

💙 Love unlimited. Until next time.
