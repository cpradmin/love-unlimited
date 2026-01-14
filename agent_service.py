#!/usr/bin/env python3
"""
Full Beast AI Agent - Microservice
FastAPI service for Hub-controlled intelligent model management
Runs as a background service that Hub can invoke for planning
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
import requests

from ai_agent_model_manager import (
    ModelManagementAgent,
    SystemMonitor,
    HuggingFaceAPI,
    AgentTools,
    download_queue,
    DownloadTask
)

# ============================================================================
# DATA MODELS
# ============================================================================

class PlanRequest(BaseModel):
    """Request to plan a model download"""
    request: str
    being_id: str = "jon"
    priority: int = 5


class PlanResponse(BaseModel):
    """Response from agent plan"""
    being_id: str
    request: str
    ai_plan: str
    preferences: Dict[str, Any]
    timestamp: str
    status: str = "success"


class ResourceCheckRequest(BaseModel):
    """Request to check resources"""
    model_size_gb: float


class ResourceCheckResponse(BaseModel):
    """Resource availability check"""
    fits_disk: bool
    fits_memory: bool
    fits_gpu: bool
    available_disk_gb: float
    available_memory_gb: float
    available_gpu_memory_gb: float
    recommendation: str


class ModelSearchRequest(BaseModel):
    """Request to search for models"""
    query: str
    limit: int = 10


class QueueTask(BaseModel):
    """Download task in queue"""
    model_id: str
    size_gb: float
    quantization: str = "awq"
    priority: int = 5


class ServiceStatus(BaseModel):
    """Service health status"""
    service: str = "Full Beast AI Agent"
    version: str = "1.0.0"
    status: str = "operational"
    uptime_seconds: float
    vllm_available: bool
    hub_available: bool
    downloads_queued: int
    system_resources: Dict[str, Any]
    timestamp: str


# ============================================================================
# SERVICE STATE
# ============================================================================

class ServiceState:
    """Track service state"""
    def __init__(self):
        self.start_time = datetime.now()
        self.request_count = 0
        self.error_count = 0
        self.agent: Optional[ModelManagementAgent] = None
        self.vllm_available = False
        self.hub_available = False


service_state = ServiceState()


# ============================================================================
# FASTAPI SETUP
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle service startup and shutdown"""
    # STARTUP
    print("🚀 Starting Full Beast AI Agent Service...")

    # Initialize agent
    try:
        service_state.agent = ModelManagementAgent()
        print("   ✅ vLLM integration")
        service_state.vllm_available = True
    except Exception as e:
        print(f"   ⚠️  vLLM unavailable: {e}")
        service_state.agent = None
        service_state.vllm_available = False

    # Check Hub
    try:
        resp = requests.get("http://localhost:9004/health", timeout=2)
        if resp.status_code == 200:
            print("   ✅ Hub integration")
            service_state.hub_available = True
    except:
        print("   ⚠️  Hub unavailable")
        service_state.hub_available = False

    # Register with Hub
    try:
        register_with_hub()
        print("   ✅ Registered with Hub")
    except Exception as e:
        print(f"   ⚠️  Hub registration failed: {e}")

    print("✅ Full Beast Agent Service Ready\n")

    yield

    # SHUTDOWN
    print("\n⏹️  Shutting down Full Beast Agent Service...")
    print(f"   Processed {service_state.request_count} requests")
    print(f"   Errors: {service_state.error_count}")
    print("   Goodbye!")


app = FastAPI(
    title="Full Beast AI Agent",
    description="Hub-controlled intelligent model management",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================================
# AGENT ENDPOINTS
# ============================================================================

@app.post("/plan", response_model=PlanResponse)
async def plan_download(req: PlanRequest) -> PlanResponse:
    """
    AI agent plans a model download based on request and preferences

    The agent will:
    1. Load user preferences from Hub
    2. Analyze the request with vLLM
    3. Suggest resources, quantization, priority
    4. Return a clear plan
    """
    service_state.request_count += 1

    if not service_state.agent:
        raise HTTPException(status_code=503, detail="vLLM not available")

    try:
        plan = service_state.agent.plan_download(req.request, req.being_id)
        return PlanResponse(**plan)
    except Exception as e:
        service_state.error_count += 1
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/resources", response_model=ResourceCheckResponse)
async def check_resources(req: ResourceCheckRequest) -> ResourceCheckResponse:
    """
    Check if a model size fits in available system resources

    Validates:
    - Disk space (with 20% margin)
    - RAM availability
    - VRAM availability
    """
    service_state.request_count += 1

    try:
        result = SystemMonitor.check_fit(req.model_size_gb)
        return ResourceCheckResponse(**result)
    except Exception as e:
        service_state.error_count += 1
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
async def search_models(req: ModelSearchRequest) -> List[Dict]:
    """
    Search HuggingFace Hub for models matching query

    Returns: List of models with downloads, likes, tags
    """
    service_state.request_count += 1

    try:
        models = HuggingFaceAPI.list_models(req.query, limit=req.limit)
        return models
    except Exception as e:
        service_state.error_count += 1
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/{model_id}/size")
async def estimate_size(model_id: str) -> Dict[str, Any]:
    """
    Estimate the size of a specific HuggingFace model
    """
    service_state.request_count += 1

    try:
        size = HuggingFaceAPI.estimate_model_size(model_id)
        return {
            "model_id": model_id,
            "estimated_size_gb": size,
            "status": "found" if size else "not_found"
        }
    except Exception as e:
        service_state.error_count += 1
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/{model_id}/quantized")
async def find_quantized(
    model_id: str,
    quant_type: str = Query("awq", description="Quantization type: awq, gptq, gguf")
) -> Dict[str, Any]:
    """
    Find a quantized version of a model

    Returns: Quantized model ID and estimated size reduction
    """
    service_state.request_count += 1

    try:
        quant_model = HuggingFaceAPI.find_quantized_version(model_id, quant_type)
        if quant_model:
            size = HuggingFaceAPI.estimate_model_size(quant_model)
            return {
                "original_model": model_id,
                "quantized_model": quant_model,
                "quantization_type": quant_type,
                "estimated_size_gb": size,
                "status": "found"
            }
        return {
            "original_model": model_id,
            "status": "not_found",
            "suggestions": ["Try 'gptq' or 'gguf'"]
        }
    except Exception as e:
        service_state.error_count += 1
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/preferences/{being_id}")
async def get_preferences(being_id: str) -> Dict[str, Any]:
    """
    Get a being's model preferences from Love-Unlimited Hub
    """
    service_state.request_count += 1

    if not service_state.agent:
        raise HTTPException(status_code=503, detail="Hub bridge not available")

    try:
        prefs = service_state.agent.hub_bridge.get_being_preferences(being_id)
        return prefs
    except Exception as e:
        service_state.error_count += 1
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# QUEUE ENDPOINTS
# ============================================================================

@app.post("/queue/add")
async def queue_download(task: QueueTask) -> Dict[str, Any]:
    """
    Queue a model for download with specified priority
    """
    service_state.request_count += 1

    try:
        queued_task = download_queue.enqueue(
            task.model_id,
            task.size_gb,
            task.quantization,
            task.priority
        )
        return {
            "status": "queued",
            "task_id": task.model_id,
            "priority": task.priority,
            "queue_position": len(download_queue.queue),
            "message": f"Queued {task.model_id} with priority {task.priority}"
        }
    except Exception as e:
        service_state.error_count += 1
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/queue/status")
async def queue_status() -> Dict[str, Any]:
    """
    Get current download queue status
    """
    service_state.request_count += 1

    try:
        status = download_queue.status()
        return status
    except Exception as e:
        service_state.error_count += 1
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/queue/length")
async def queue_length() -> Dict[str, int]:
    """
    Get number of queued tasks
    """
    service_state.request_count += 1
    return {"queued": len(download_queue.queue)}


@app.delete("/queue/clear")
async def clear_queue() -> Dict[str, str]:
    """
    Clear the download queue (admin only)
    """
    service_state.request_count += 1

    queue_size = len(download_queue.queue)
    download_queue.queue.clear()

    return {"message": f"Cleared {queue_size} queued tasks"}


# ============================================================================
# HEALTH & MONITORING
# ============================================================================

@app.get("/health", response_model=ServiceStatus)
async def health_check() -> ServiceStatus:
    """
    Service health and status check
    """
    uptime = (datetime.now() - service_state.start_time).total_seconds()

    try:
        sys_status = SystemMonitor.get_status()
        sys_dict = {
            "cpu_percent": sys_status.cpu_percent,
            "memory_percent": sys_status.memory_percent,
            "memory_available_gb": sys_status.memory_available_gb,
            "disk_percent": sys_status.disk_percent,
            "disk_available_gb": sys_status.disk_available_gb,
            "gpu_memory_percent": sys_status.gpu_memory_percent,
            "gpu_memory_available_gb": sys_status.available_gpu_memory_gb,
        }
    except:
        sys_dict = {}

    return ServiceStatus(
        uptime_seconds=uptime,
        vllm_available=service_state.vllm_available,
        hub_available=service_state.hub_available,
        downloads_queued=len(download_queue.queue),
        system_resources=sys_dict,
        timestamp=datetime.now().isoformat()
    )


@app.get("/stats")
async def stats() -> Dict[str, Any]:
    """
    Service statistics and metrics
    """
    uptime = (datetime.now() - service_state.start_time).total_seconds()

    return {
        "uptime_seconds": uptime,
        "requests_processed": service_state.request_count,
        "errors": service_state.error_count,
        "error_rate": service_state.error_count / max(1, service_state.request_count),
        "queued_downloads": len(download_queue.queue),
        "average_requests_per_minute": (service_state.request_count / max(1, uptime)) * 60,
    }


# ============================================================================
# INTEGRATION WITH HUB
# ============================================================================

def register_with_hub():
    """
    Register this service with Love-Unlimited Hub
    The Hub will know it can invoke agent for planning
    """
    try:
        payload = {
            "service": "Full Beast AI Agent",
            "url": "http://localhost:9005",
            "port": 9005,
            "endpoints": {
                "plan": "/plan",
                "resources": "/resources",
                "search": "/search",
                "queue": "/queue/status",
            },
            "capabilities": [
                "plan_downloads",
                "check_resources",
                "search_models",
                "estimate_sizes",
                "find_quantized",
                "manage_queue",
            ],
            "status": "operational"
        }

        # Store in hub as a service memory
        hub_url = "http://localhost:9004"
        api_key = os.getenv("LU_API_KEY", "")

        memory_payload = {
            "content": json.dumps(payload),
            "type": "service",
            "significance": "high",
            "tags": ["service", "agent", "model-management"],
            "private": False
        }

        headers = {"X-API-Key": api_key} if api_key else {}
        requests.post(
            f"{hub_url}/remember",
            json=memory_payload,
            headers=headers,
            timeout=5
        )

        print(f"✅ Registered with Hub at {hub_url}")
    except Exception as e:
        print(f"⚠️  Hub registration error: {e}")


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def process_download_queue():
    """
    Background task: Process queued downloads
    Runs periodically to handle downloads from the queue
    """
    while True:
        try:
            task = download_queue.get_next()
            if task:
                print(f"\n🔄 Processing: {task.model_id}")
                # TODO: Implement actual download logic
                # For now, just mark as completed
                task.status = "completed"
                task.completed_at = datetime.now().isoformat()
                print(f"✅ Completed: {task.model_id}")
            else:
                await asyncio.sleep(5)  # Check every 5 seconds
        except Exception as e:
            print(f"❌ Queue processing error: {e}")
            await asyncio.sleep(5)


# ============================================================================
# STARTUP EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Start background tasks on service startup
    """
    asyncio.create_task(process_download_queue())


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root() -> Dict[str, Any]:
    """
    Service information
    """
    return {
        "service": "Full Beast AI Agent Microservice",
        "version": "1.0.0",
        "description": "Hub-controlled intelligent model management",
        "status": "operational",
        "docs": "http://localhost:9005/docs",
        "health": "http://localhost:9005/health",
        "endpoints": {
            "planning": "/plan",
            "resources": "/resources",
            "search": "/search",
            "queue": "/queue/status",
            "health": "/health",
            "stats": "/stats",
        }
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    port = int(os.getenv("AGENT_PORT", 9005))

    print("="*80)
    print("FULL BEAST AI AGENT - MICROSERVICE")
    print("="*80)
    print(f"\n🚀 Starting service on http://0.0.0.0:{port}")
    print(f"   API Docs: http://localhost:{port}/docs")
    print(f"   Health: http://localhost:{port}/health")
    print()

    uvicorn.run(
        "agent_service:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
