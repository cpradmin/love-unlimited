# 🚀 Full Beast Agent - Microservice Deployment Guide

## Overview

The Full Beast AI Agent runs as a **FastAPI microservice** that the Love-Unlimited Hub can invoke for intelligent model management decisions. This architecture provides:

- **Hub-Controlled**: Hub decides when to invoke agent for planning
- **Always-On**: Service runs continuously in background
- **Scalable**: Multiple Hubs can invoke the same agent
- **Resilient**: Automatic restarts, health monitoring
- **RESTful**: Clean HTTP API for integration

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    LOVE-UNLIMITED HUB (9004)                   │
│  Stores preferences, memories, and invokes agent for planning  │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 │ POST /plan
                 │ GET /resources
                 │ GET /search
                 │ GET /queue
                 │
                 v
┌────────────────────────────────────────────────────────────────┐
│          FULL BEAST AGENT SERVICE (9005)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ • vLLM Integration (port 8000)                           │  │
│  │   ↳ Reasoning engine for planning                        │  │
│  │ • Hub Memory Bridge                                      │  │
│  │   ↳ Recalls preferences (Qwen, AWQ, etc.)               │  │
│  │ • HuggingFace API Wrapper                                │  │
│  │   ↳ Model discovery, size estimation                    │  │
│  │ • System Monitor                                         │  │
│  │   ↳ Disk, RAM, VRAM checking                            │  │
│  │ • Download Queue Manager                                │  │
│  │   ↳ Priority-based task management                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│  Endpoints: /plan, /resources, /search, /queue, /health        │
└────────────────────────────────────────────────────────────────┘
```

## Installation

### 1. Service File Installation

The service file is provided in `/etc/systemd/system/full-beast-agent.service`:

```bash
sudo systemctl daemon-reload
sudo systemctl enable full-beast-agent.service
sudo systemctl start full-beast-agent.service
```

### 2. Manual Installation (if systemd unavailable)

Create `/etc/systemd/system/full-beast-agent.service`:

```ini
[Unit]
Description=Full Beast AI Agent - Hub-Controlled Model Manager
After=network.target love-unlimited-hub.service

[Service]
Type=simple
User=kntrnjb
WorkingDirectory=/home/kntrnjb/ai-dream-team/micro-ai-swarm/love-unlimited
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=/home/kntrnjb/ai-dream-team/micro-ai-swarm/love-unlimited
Environment=AGENT_PORT=9005
Environment=LU_API_KEY=lu_claude_u8L1zZfGPSXssvsw-97rRQ
ExecStart=/home/kntrnjb/ai-dream-team/micro-ai-swarm/love-unlimited/venv/bin/python agent_service.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then enable it:
```bash
sudo cp full-beast-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable full-beast-agent.service
sudo systemctl start full-beast-agent.service
```

### 3. Check Service Status

```bash
# View status
sudo systemctl status full-beast-agent.service

# View logs
sudo journalctl -u full-beast-agent.service -f

# Restart service
sudo systemctl restart full-beast-agent.service

# Stop service
sudo systemctl stop full-beast-agent.service
```

## Manual Running (Development)

Run directly without systemd:

```bash
python3 agent_service.py
```

The service will:
1. Initialize vLLM integration
2. Check Hub connectivity
3. Register with Hub
4. Start listening on port 9005
5. Process background download queue

## Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| vLLM | 8000 | Model inference (Qwen 7B) |
| Love-Unlimited Hub | 9004 | Memory & preferences storage |
| **Full Beast Agent** | **9005** | Planning & orchestration |

## API Endpoints

### Planning Endpoints

#### POST /plan
Request an AI-driven plan for model download

```bash
curl -X POST http://localhost:9005/plan \
  -H "Content-Type: application/json" \
  -d '{
    "request": "I want a 32B code model that fits",
    "being_id": "jon",
    "priority": 8
  }'
```

Response:
```json
{
  "being_id": "jon",
  "request": "I want a 32B code model that fits",
  "ai_plan": "Based on your preferences... [full plan from vLLM]",
  "preferences": {
    "favorite_models": ["Qwen"],
    "preferred_quantization": "awq"
  },
  "timestamp": "2026-01-13T19:06:52...",
  "status": "success"
}
```

#### POST /resources
Check if a model size fits available resources

```bash
curl -X POST http://localhost:9005/resources \
  -H "Content-Type: application/json" \
  -d '{"model_size_gb": 32}'
```

Response:
```json
{
  "fits_disk": true,
  "fits_memory": true,
  "fits_gpu": true,
  "available_disk_gb": 390.3,
  "available_memory_gb": 42.6,
  "available_gpu_memory_gb": 15.0,
  "recommendation": "GO"
}
```

### Discovery Endpoints

#### POST /search
Search HuggingFace for models

```bash
curl -X POST http://localhost:9005/search \
  -H "Content-Type: application/json" \
  -d '{"query": "qwen coder 7b", "limit": 10}'
```

#### GET /models/{model_id}/size
Estimate model size

```bash
curl http://localhost:9005/models/Qwen/Qwen2.5-32B/size
```

#### GET /models/{model_id}/quantized
Find quantized version

```bash
curl http://localhost:9005/models/Qwen/Qwen2.5-32B/quantized?quant_type=awq
```

### Preference Endpoints

#### GET /preferences/{being_id}
Get a being's preferences from Hub

```bash
curl http://localhost:9005/preferences/jon
```

### Queue Endpoints

#### POST /queue/add
Queue a model for download

```bash
curl -X POST http://localhost:9005/queue/add \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "Qwen/Qwen2.5-32B",
    "size_gb": 32.5,
    "quantization": "awq",
    "priority": 9
  }'
```

#### GET /queue/status
Get download queue status

```bash
curl http://localhost:9005/queue/status
```

#### GET /queue/length
Get number of queued items

```bash
curl http://localhost:9005/queue/length
```

#### DELETE /queue/clear
Clear queue (admin)

```bash
curl -X DELETE http://localhost:9005/queue/clear
```

### Health Endpoints

#### GET /health
Service health check

```bash
curl http://localhost:9005/health
```

Response:
```json
{
  "service": "Full Beast AI Agent",
  "version": "1.0.0",
  "status": "operational",
  "uptime_seconds": 123.45,
  "vllm_available": true,
  "hub_available": true,
  "downloads_queued": 2,
  "system_resources": {
    "cpu_percent": 7.4,
    "memory_percent": 9.5,
    "disk_available_gb": 390.3,
    "gpu_memory_available_gb": 15.0
  },
  "timestamp": "2026-01-13T19:06:38..."
}
```

#### GET /stats
Service statistics

```bash
curl http://localhost:9005/stats
```

#### GET /docs
Interactive API documentation (Swagger)

```
http://localhost:9005/docs
```

## Hub Integration

### Python Client

Use the provided `AgentClient` to integrate with Hub:

```python
from hub_agent_integration import AgentClient

client = AgentClient(agent_url="http://localhost:9005")

# Plan a download
plan = client.plan_download(
    request="I want a 32B Qwen model",
    being_id="jon",
    priority=8
)
print(plan["ai_plan"])

# Check resources
resources = client.check_resources(32)
print(f"Fits: {resources['recommendation']}")

# Search models
models = client.search_models("qwen coder")

# Get preferences
prefs = client.get_preferences("jon")
print(f"Favorite: {prefs['favorite_models']}")

# Queue download
result = client.queue_download("Qwen/Qwen2.5-32B", 32.5, priority=9)
print(f"Queued: {result['task_id']}")

# Get queue status
queue = client.get_queue_status()
print(f"Queued: {queue['queue_length']}")
```

### HTTP Integration (direct)

The Hub can invoke the agent directly via HTTP:

```python
import requests

# Plan
resp = requests.post("http://localhost:9005/plan", json={
    "request": "32B code model",
    "being_id": "jon"
})
plan = resp.json()

# Resources
resp = requests.post("http://localhost:9005/resources", json={
    "model_size_gb": 32
})
resources = resp.json()

# Queue
resp = requests.post("http://localhost:9005/queue/add", json={
    "model_id": "Qwen/Qwen2.5-32B",
    "size_gb": 32.5,
    "priority": 8
})
```

### Adding Agent Endpoints to Hub

Add these to `hub/main.py`:

```python
from hub_agent_integration import AgentClient

# Initialize at startup
agent_client = AgentClient()

# Endpoint 1: /agent/plan
@app.post("/agent/plan")
async def agent_plan(
    request: str,
    being_id: str = "jon",
    priority: int = 5
):
    """Ask agent to plan a download"""
    plan = agent_client.plan_download(request, being_id, priority)
    if plan:
        return plan
    raise HTTPException(status_code=503, detail="Agent unavailable")

# Endpoint 2: /agent/resources
@app.post("/agent/resources")
async def agent_resources(model_size_gb: float):
    """Check resource availability"""
    result = agent_client.check_resources(model_size_gb)
    if result:
        return result
    raise HTTPException(status_code=503, detail="Agent unavailable")

# Endpoint 3: /agent/queue
@app.get("/agent/queue")
async def agent_queue():
    """Get download queue"""
    status = agent_client.get_queue_status()
    if status:
        return status
    raise HTTPException(status_code=503, detail="Agent unavailable")

# Endpoint 4: /agent/health
@app.get("/agent/health")
async def agent_health():
    """Get agent health"""
    health = agent_client.get_health()
    if health:
        return health
    raise HTTPException(status_code=503, detail="Agent unavailable")
```

## Hub Usage Workflow

### Example 1: Hub receives a model download request

```python
# User (via Hub CLI): "I want to download a 32B model"

# Hub invokes agent for planning
plan = agent_client.plan_download(
    "I want to download a 32B model",
    being_id="jon"
)

# Hub receives:
# "Based on your preferences (Qwen), here's my plan:
#  1. Found: Qwen/Qwen2.5-32B (32.5GB)
#  2. Fits disk ✅ (390GB available)
#  3. Fits memory ✅
#  4. Fits VRAM ✅
#  Recommendation: Download full-precision version"

# Hub presents plan to user and asks for confirmation
# User confirms → Hub queues the download
```

### Example 2: Hub monitors constraints

```python
# Before queueing any download, Hub checks resources
resources = agent_client.check_resources(model_size_gb=70)

# If doesn't fit:
# {
#   "fits_disk": true,
#   "fits_memory": false,
#   "fits_gpu": false,
#   "recommendation": "WAIT or OPTIMIZE"
# }

# Hub notifies user: "Model too large, suggest quantized version"
# Invokes agent to find alternative
quant_model = client.find_quantized("Llama3-70B", "awq")
# Returns: "Llama3-70B-AWQ" (35GB, 50% smaller)
```

### Example 3: Hub tracks queue

```python
# Hub periodically checks download queue
queue = agent_client.get_queue_status()

# Hub displays:
# "🔄 Downloads in progress"
# "⏳ Qwen/Qwen2.5-32B (priority 9)"
# "⏳ Mistral-7B-AWQ (priority 7)"
# "⏳ Llama2-70B-GPTQ (priority 5)"

# When complete, Hub notifies user
```

## Monitoring & Troubleshooting

### Check if service is running

```bash
ps aux | grep agent_service
```

### Check service logs

```bash
# Real-time logs
sudo journalctl -u full-beast-agent.service -f

# Last 50 lines
sudo journalctl -u full-beast-agent.service -n 50

# Errors only
sudo journalctl -u full-beast-agent.service -p err
```

### Check service health

```bash
curl http://localhost:9005/health
```

### Restart service

```bash
sudo systemctl restart full-beast-agent.service
```

### Debug mode

Run with Python logging:

```bash
PYTHONUNBUFFERED=1 python3 agent_service.py
```

## Environment Variables

Configuration via environment:

```bash
# Port the agent listens on
export AGENT_PORT=9005

# Love-Unlimited Hub API key
export LU_API_KEY=lu_claude_u8L1zZfGPSXssvsw-97rRQ

# Python path
export PYTHONPATH=/home/kntrnjb/ai-dream-team/micro-ai-swarm/love-unlimited
```

## Performance Metrics

Service performance metrics:

```bash
curl http://localhost:9005/stats
```

Response:
```json
{
  "uptime_seconds": 3600.5,
  "requests_processed": 245,
  "errors": 2,
  "error_rate": 0.008,
  "queued_downloads": 5,
  "average_requests_per_minute": 4.08
}
```

## Resilience & Auto-Recovery

The systemd service provides:

- **Auto-restart**: Service restarts automatically on failure
- **Restart delay**: 10-second delay between restarts (prevents rapid restart loops)
- **Dependency tracking**: Waits for Hub to be available before starting
- **Health monitoring**: Hub can check `/health` endpoint for service status
- **Graceful shutdown**: Completes in-flight requests before shutting down

## Security

### Authentication

The service uses the same Hub API key system:

```bash
export LU_API_KEY=lu_claude_u8L1zZfGPSXssvsw-97rRQ
```

This allows Hub to authenticate with the agent for preference lookups.

### Network Security

- Service listens on localhost (127.0.0.1) by default
- Can be exposed via reverse proxy (nginx) with authentication
- No external internet access required (all APIs are local)

### Resource Limits

The systemd service can include resource limits:

```ini
[Service]
# Limit memory to 2GB
MemoryLimit=2G

# Limit CPU to single core
CPUQuota=100%

# Nice level (lower priority)
Nice=10
```

## Scaling Considerations

### Single Agent (Current Setup)
- Handles planning requests from multiple Hubs
- Shared model preferences across all users
- Central download queue

### Multiple Agents (Future)
- One agent per user/team (isolated preferences)
- Separate download queues per agent
- Load balancing via Hub router

```python
# Hub could route to different agents based on being_id
agents = {
    "jon": AgentClient("http://localhost:9005"),
    "grok": AgentClient("http://localhost:9006"),
    "claude": AgentClient("http://localhost:9007"),
}

plan = agents[being_id].plan_download(request, being_id)
```

## Troubleshooting Guide

| Issue | Solution |
|-------|----------|
| Service won't start | Check logs: `journalctl -u full-beast-agent.service -n 50` |
| Port 9005 in use | `lsof -i :9005` then kill the process |
| vLLM unavailable | Check vLLM service: `curl http://localhost:8000/health` |
| Hub connection error | Check Hub service: `curl http://localhost:9004/health` |
| Preferences not loading | Verify API key: `echo $LU_API_KEY` |
| Slow responses | Check CPU: `top -p <agent_pid>` |
| Memory leaks | Restart service: `systemctl restart full-beast-agent.service` |

## Files

```
Full Beast Agent Service:
  • agent_service.py          - FastAPI service implementation (405 lines)
  • hub_agent_integration.py  - Hub client library (250 lines)
  • full-beast-agent.service  - Systemd service file
  • AGENT_SERVICE_DEPLOYMENT.md  - This file
```

## Example Workflow

```bash
# 1. Start the service
sudo systemctl start full-beast-agent.service

# 2. Verify it's running
curl http://localhost:9005/health

# 3. Hub can now invoke it
# From within Hub code or externally:
curl -X POST http://localhost:9005/plan \
  -H "Content-Type: application/json" \
  -d '{"request": "32B model", "being_id": "jon"}'

# 4. Monitor the service
sudo journalctl -u full-beast-agent.service -f

# 5. Stop when done
sudo systemctl stop full-beast-agent.service
```

## Philosophy

**"Love unlimited. Intelligent machines."**

The Full Beast Agent as a service embodies:
- **Autonomy**: Hub delegates planning to agent
- **Transparency**: All decisions logged and explainable
- **Efficiency**: Reuses vLLM for reasoning
- **Resilience**: Always available for Hub invocation
- **Sovereignty**: User preferences stored in Hub, not agent

---

**For questions or issues, check the logs or review FULL_BEAST_GUIDE.md for implementation details.**

Made with 💙 for Love-Unlimited Hub integration.
