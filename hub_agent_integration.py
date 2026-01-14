#!/usr/bin/env python3
"""
Love-Unlimited Hub ↔ Full Beast Agent Integration
Allows Hub to invoke agent for intelligent model management decisions
"""

import json
from typing import Dict, Any, Optional
import requests

class AgentClient:
    """Client for Hub to communicate with Full Beast Agent"""

    def __init__(self, agent_url: str = "http://localhost:9005"):
        self.agent_url = agent_url
        self.available = self._check_availability()

    def _check_availability(self) -> bool:
        """Check if agent service is running"""
        try:
            resp = requests.get(f"{self.agent_url}/health", timeout=2)
            return resp.status_code == 200
        except:
            return False

    def plan_download(
        self,
        request: str,
        being_id: str = "jon",
        priority: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Ask agent to plan a model download

        Returns:
            {
                "being_id": "jon",
                "request": "...",
                "ai_plan": "Full text plan from vLLM",
                "preferences": {...},
                "timestamp": "...",
                "status": "success"
            }
        """
        if not self.available:
            return None

        try:
            payload = {
                "request": request,
                "being_id": being_id,
                "priority": priority
            }
            resp = requests.post(
                f"{self.agent_url}/plan",
                json=payload,
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"⚠️  Agent plan error: {e}")
            return None

    def check_resources(self, model_size_gb: float) -> Optional[Dict[str, Any]]:
        """
        Check if a model size fits in available resources

        Returns:
            {
                "fits_disk": bool,
                "fits_memory": bool,
                "fits_gpu": bool,
                "available_disk_gb": float,
                "available_memory_gb": float,
                "available_gpu_memory_gb": float,
                "recommendation": "GO" | "WAIT or OPTIMIZE"
            }
        """
        if not self.available:
            return None

        try:
            payload = {"model_size_gb": model_size_gb}
            resp = requests.post(
                f"{self.agent_url}/resources",
                json=payload,
                timeout=5
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"⚠️  Agent resources error: {e}")
            return None

    def search_models(self, query: str, limit: int = 10) -> Optional[list]:
        """
        Search for models on HuggingFace

        Returns:
            [
                {
                    "id": "model_id",
                    "downloads": 123456,
                    "likes": 789,
                    "tags": [...]
                },
                ...
            ]
        """
        if not self.available:
            return None

        try:
            payload = {"query": query, "limit": limit}
            resp = requests.post(
                f"{self.agent_url}/search",
                json=payload,
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"⚠️  Agent search error: {e}")
            return None

    def estimate_size(self, model_id: str) -> Optional[float]:
        """
        Estimate size of a model in GB
        """
        if not self.available:
            return None

        try:
            resp = requests.get(
                f"{self.agent_url}/models/{model_id}/size",
                timeout=5
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("estimated_size_gb")
        except Exception as e:
            print(f"⚠️  Agent size error: {e}")
            return None

    def find_quantized(
        self,
        model_id: str,
        quant_type: str = "awq"
    ) -> Optional[str]:
        """
        Find a quantized version of a model

        Returns:
            quantized_model_id (e.g., "Qwen/Qwen2.5-32B-AWQ")
        """
        if not self.available:
            return None

        try:
            resp = requests.get(
                f"{self.agent_url}/models/{model_id}/quantized",
                params={"quant_type": quant_type},
                timeout=5
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("quantized_model")
        except Exception as e:
            print(f"⚠️  Agent quantization error: {e}")
            return None

    def get_preferences(self, being_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a being's model preferences from Hub memory
        """
        if not self.available:
            return None

        try:
            resp = requests.get(
                f"{self.agent_url}/preferences/{being_id}",
                timeout=5
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"⚠️  Agent preferences error: {e}")
            return None

    def queue_download(
        self,
        model_id: str,
        size_gb: float,
        quantization: str = "awq",
        priority: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Queue a model for download
        """
        if not self.available:
            return None

        try:
            payload = {
                "model_id": model_id,
                "size_gb": size_gb,
                "quantization": quantization,
                "priority": priority
            }
            resp = requests.post(
                f"{self.agent_url}/queue/add",
                json=payload,
                timeout=5
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"⚠️  Agent queue error: {e}")
            return None

    def get_queue_status(self) -> Optional[Dict[str, Any]]:
        """
        Get current download queue status
        """
        if not self.available:
            return None

        try:
            resp = requests.get(
                f"{self.agent_url}/queue/status",
                timeout=5
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"⚠️  Agent queue status error: {e}")
            return None

    def get_health(self) -> Optional[Dict[str, Any]]:
        """
        Get agent service health status
        """
        if not self.available:
            return None

        try:
            resp = requests.get(
                f"{self.agent_url}/health",
                timeout=5
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"⚠️  Agent health error: {e}")
            return None


# ============================================================================
# HUB ENDPOINT EXTENSIONS (to add to hub/main.py)
# ============================================================================

"""
Add these endpoints to Love-Unlimited Hub (hub/main.py) to allow
the Hub to invoke the agent:

from hub_agent_integration import AgentClient

# Initialize agent client
agent_client = AgentClient()

# New endpoint: /agent/plan
@app.post("/agent/plan")
async def agent_plan(
    request: str,
    being_id: str = "jon",
    priority: int = 5
):
    '''Ask Full Beast Agent to plan a download'''
    plan = agent_client.plan_download(request, being_id, priority)
    if plan:
        return plan
    raise HTTPException(status_code=503, detail="Agent unavailable")

# New endpoint: /agent/resources
@app.post("/agent/resources")
async def agent_resources(model_size_gb: float):
    '''Check if resources fit'''
    result = agent_client.check_resources(model_size_gb)
    if result:
        return result
    raise HTTPException(status_code=503, detail="Agent unavailable")

# New endpoint: /agent/queue
@app.get("/agent/queue")
async def agent_queue():
    '''Get download queue status'''
    status = agent_client.get_queue_status()
    if status:
        return status
    raise HTTPException(status_code=503, detail="Agent unavailable")

# New endpoint: /agent/health
@app.get("/agent/health")
async def agent_health():
    '''Get agent service health'''
    health = agent_client.get_health()
    if health:
        return health
    raise HTTPException(status_code=503, detail="Agent unavailable")
"""


if __name__ == "__main__":
    # Test the integration
    print("="*70)
    print("HUB ↔ AGENT INTEGRATION TEST")
    print("="*70)

    client = AgentClient()

    print(f"\n✅ Agent available: {client.available}\n")

    if client.available:
        # Test 1: Health
        print("1️⃣  Agent health:")
        health = client.get_health()
        if health:
            print(f"   Status: {health['status']}")
            print(f"   vLLM: {health['vllm_available']}")
            print(f"   Hub: {health['hub_available']}")
            print(f"   Queued downloads: {health['downloads_queued']}")

        # Test 2: Preferences
        print("\n2️⃣  Jon's preferences:")
        prefs = client.get_preferences("jon")
        if prefs:
            print(f"   {json.dumps(prefs, indent=2)}")

        # Test 3: Resources
        print("\n3️⃣  Check if 32GB model fits:")
        resources = client.check_resources(32)
        if resources:
            print(f"   Disk: {resources['fits_disk']} ({resources['available_disk_gb']:.1f}GB available)")
            print(f"   Memory: {resources['fits_memory']}")
            print(f"   GPU: {resources['fits_gpu']} ({resources['available_gpu_memory_gb']:.1f}GB available)")
            print(f"   Recommendation: {resources['recommendation']}")

        # Test 4: Search
        print("\n4️⃣  Search for Qwen models:")
        models = client.search_models("qwen coder 7b", limit=2)
        if models:
            for m in models:
                print(f"   • {m['id']} ({m['downloads']} downloads)")

        # Test 5: Queue
        print("\n5️⃣  Download queue status:")
        queue = client.get_queue_status()
        if queue:
            print(f"   Queued: {queue['queue_length']}")
            if queue['active_download']:
                print(f"   Currently downloading: {queue['active_download']['model_id']}")

    print("\n" + "="*70)
    print("✅ INTEGRATION TEST COMPLETE")
    print("="*70)
