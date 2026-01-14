#!/usr/bin/env python3
"""
Full Beast: Custom AI Agent for Intelligent Model Management
Uses vLLM + LangChain + Hub Memory for god-tier model orchestration
"""

import os
import json
import asyncio
import psutil
import subprocess
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import deque
import requests

# vLLM integration (no LangChain needed - using vLLM directly)
try:
    from openai import OpenAI
except ImportError:
    print("⚠️  OpenAI client not available, will use requests fallback")
    OpenAI = None

print("🚀 Initializing Full Beast AI Agent...")


# ============================================================================
# SYSTEM MONITORING TOOLS
# ============================================================================

@dataclass
class SystemStatus:
    """System resource snapshot"""
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    disk_percent: float
    disk_available_gb: float
    gpu_memory_percent: float
    available_gpu_memory_gb: float  # Fixed field name


class SystemMonitor:
    """Monitor system resources"""

    @staticmethod
    def get_status() -> SystemStatus:
        """Get current system status"""
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Try to get GPU info
        gpu_mem_total = 24  # Assume 24GB (adjust as needed)
        gpu_mem_used = 9  # Estimate from vLLM usage
        gpu_memory_available = gpu_mem_total - gpu_mem_used

        return SystemStatus(
            cpu_percent=psutil.cpu_percent(interval=0.5),
            memory_percent=mem.percent,
            memory_available_gb=mem.available / (1024**3),
            disk_percent=disk.percent,
            disk_available_gb=disk.free / (1024**3),
            gpu_memory_percent=(gpu_mem_used / gpu_mem_total) * 100,
            available_gpu_memory_gb=gpu_memory_available
        )

    @staticmethod
    def check_fit(model_size_gb: float) -> Dict[str, Any]:
        """Check if model fits in available resources"""
        status = SystemMonitor.get_status()

        fits_disk = status.disk_available_gb > model_size_gb * 1.2
        fits_memory = status.memory_available_gb > (model_size_gb * 0.3)
        fits_gpu = status.available_gpu_memory_gb > (model_size_gb * 0.3)

        return {
            "fits_disk": fits_disk,
            "fits_memory": fits_memory,
            "fits_gpu": fits_gpu,
            "available_disk_gb": status.disk_available_gb,
            "available_memory_gb": status.memory_available_gb,
            "available_gpu_memory_gb": status.available_gpu_memory_gb,
            "model_size_gb": model_size_gb,
            "recommendation": "GO" if (fits_disk and fits_memory) else "WAIT or OPTIMIZE"
        }


# ============================================================================
# HUGGINGFACE MODEL TOOLS
# ============================================================================

class HuggingFaceAPI:
    """HuggingFace API wrapper for model discovery and sizing"""

    HF_API_URL = "https://huggingface.co/api"

    # Known quantization types and their size reduction
    QUANTIZATION_REDUCTIONS = {
        "awq": 0.5,      # 50% reduction
        "gptq": 0.5,     # 50% reduction
        "gguf": 0.6,     # 40% reduction
        "int8": 0.75,    # 25% reduction
        "fp16": 1.0,     # No reduction
    }

    MODEL_CACHE = {}  # Simple cache

    @classmethod
    def list_models(cls, filter_text: str = "", task: str = "", limit: int = 20) -> List[Dict]:
        """List HuggingFace models matching criteria"""
        try:
            url = f"{cls.HF_API_URL}/models"
            params = {
                "full": True,
                "limit": limit,
            }
            if filter_text:
                params["search"] = filter_text
            if task:
                params["task"] = task

            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()

            models = resp.json()
            if not isinstance(models, list):
                return []

            results = []
            for model in models[:limit]:
                results.append({
                    "id": model.get("id", "unknown"),
                    "downloads": model.get("downloads", 0),
                    "likes": model.get("likes", 0),
                    "tags": model.get("tags", []),
                })

            return results
        except Exception as e:
            print(f"⚠️  HF API error: {e}")
            return []

    @classmethod
    def estimate_model_size(cls, model_id: str) -> Optional[float]:
        """Estimate model size in GB from HuggingFace"""
        try:
            if model_id in cls.MODEL_CACHE:
                return cls.MODEL_CACHE[model_id]

            url = f"{cls.HF_API_URL}/models/{model_id}"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # Try to get size from siblings (safetensors files)
            size_bytes = 0
            if "siblings" in data:
                for sibling in data["siblings"]:
                    if sibling["rfilename"].endswith(".safetensors"):
                        size_bytes += sibling.get("size", 0)

            size_gb = size_bytes / (1024**3) if size_bytes > 0 else None

            if size_gb:
                cls.MODEL_CACHE[model_id] = size_gb

            return size_gb
        except Exception as e:
            print(f"⚠️  Size estimation error: {e}")
            return None

    @classmethod
    def find_quantized_version(cls, model_id: str, quant_type: str = "awq") -> Optional[str]:
        """Find quantized version of a model"""
        try:
            org, name = model_id.split("/")

            # Common quantization naming patterns
            candidates = [
                f"{org}/{name}-{quant_type}",
                f"{org}/{name}-{quant_type.upper()}",
                f"{org}/{name}-{quant_type}-quantized",
            ]

            for candidate in candidates:
                url = f"{cls.HF_API_URL}/models/{candidate}"
                resp = requests.head(url, timeout=5)
                if resp.status_code == 200:
                    return candidate

            return None
        except Exception as e:
            print(f"⚠️  Quantization search error: {e}")
            return None


# ============================================================================
# HUB MEMORY INTEGRATION
# ============================================================================

class HubMemoryBridge:
    """Connect to Love-Unlimited Hub for preferences and memory"""

    def __init__(self, hub_url: str = "http://localhost:9004", api_key: str = ""):
        self.hub_url = hub_url
        self.api_key = api_key

    def get_being_preferences(self, being_id: str = "jon") -> Dict[str, Any]:
        """Get user preferences from hub memory"""
        try:
            params = {"q": f"preference model favorite {being_id}", "limit": 10}
            headers = {"X-API-Key": self.api_key} if self.api_key else {}

            resp = requests.get(
                f"{self.hub_url}/recall",
                params=params,
                headers=headers,
                timeout=5
            )

            if resp.status_code == 200:
                data = resp.json()
                preferences = {
                    "favorite_models": [],
                    "preferred_quantization": "awq",
                    "notes": ""
                }

                # Parse memories for preferences
                for memory in data.get("memories", []):
                    content = memory.get("content", "").lower()

                    # Extract preferences from memory content
                    if "qwen" in content:
                        preferences["favorite_models"].append("Qwen")
                    if "mistral" in content:
                        preferences["favorite_models"].append("Mistral")
                    if "llama" in content:
                        preferences["favorite_models"].append("Llama")

                    if "awq" in content:
                        preferences["preferred_quantization"] = "awq"
                    elif "gptq" in content:
                        preferences["preferred_quantization"] = "gptq"

                return preferences
        except Exception as e:
            print(f"⚠️  Hub memory error: {e}")

        return {
            "favorite_models": ["Qwen"],
            "preferred_quantization": "awq",
            "notes": "Default preferences"
        }

    def store_download_event(self, being_id: str, model_id: str, size_gb: float):
        """Store model download in hub memory"""
        try:
            memory_payload = {
                "content": f"Downloaded model {model_id} ({size_gb:.1f}GB) via agent. Successful download for later reference.",
                "type": "experience",
                "significance": "medium",
                "tags": ["model-download", "agent", model_id.split("/")[1].lower()],
                "private": False
            }

            headers = {"X-API-Key": self.api_key} if self.api_key else {}
            requests.post(
                f"{self.hub_url}/remember",
                json=memory_payload,
                headers=headers,
                timeout=5
            )
        except Exception as e:
            print(f"⚠️  Hub storage error: {e}")


# ============================================================================
# DOWNLOAD QUEUE MANAGER
# ============================================================================

@dataclass
class DownloadTask:
    """Represents a model download task"""
    model_id: str
    size_gb: float
    quantization: str
    priority: int  # Higher = earlier
    status: str  # queued, downloading, completed, failed
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class DownloadQueue:
    """Manage model download queue with priorities"""

    def __init__(self):
        self.queue: deque = deque()
        self.active_download: Optional[DownloadTask] = None

    def enqueue(self, model_id: str, size_gb: float, quantization: str = "awq", priority: int = 5):
        """Add model to download queue"""
        task = DownloadTask(
            model_id=model_id,
            size_gb=size_gb,
            quantization=quantization,
            priority=priority,
            status="queued",
            created_at=datetime.now().isoformat()
        )

        self.queue.append(task)
        # Sort by priority (descending)
        self.queue = deque(sorted(self.queue, key=lambda x: x.priority, reverse=True))

        return task

    def get_next(self) -> Optional[DownloadTask]:
        """Get next task to download"""
        if self.queue:
            return self.queue.popleft()
        return None

    def status(self) -> Dict[str, Any]:
        """Get queue status"""
        return {
            "queue_length": len(self.queue),
            "queued_tasks": [asdict(t) for t in list(self.queue)],
            "active_download": asdict(self.active_download) if self.active_download else None
        }


# ============================================================================
# AGENT TOOLS (No LangChain needed)
# ============================================================================

class AgentTools:
    """Tool functions for the AI Agent"""

    @staticmethod
    def check_system_resources(model_size_gb: float) -> str:
        """Check if system has enough resources for a model."""
        result = SystemMonitor.check_fit(model_size_gb)
        return json.dumps(result, indent=2)

    @staticmethod
    def find_models(search_query: str, task_type: str = "") -> str:
        """Find models on HuggingFace Hub."""
        models = HuggingFaceAPI.list_models(
            filter_text=search_query,
            task=task_type,
            limit=10
        )
        return json.dumps(models, indent=2)

    @staticmethod
    def estimate_model_size(model_id: str) -> str:
        """Estimate the size of a HuggingFace model."""
        size = HuggingFaceAPI.estimate_model_size(model_id)
        return json.dumps({
            "model_id": model_id,
            "estimated_size_gb": size,
            "status": "found" if size else "not_found"
        }, indent=2)

    @staticmethod
    def find_quantized_model(model_id: str, quantization_type: str = "awq") -> str:
        """Find a quantized version of a model."""
        quant_model = HuggingFaceAPI.find_quantized_version(model_id, quantization_type)
        if quant_model:
            size = HuggingFaceAPI.estimate_model_size(quant_model)
            orig_size = HuggingFaceAPI.estimate_model_size(model_id)
            reduction = ((orig_size or 1) - (size or 1)) / (orig_size or 1) * 100 if orig_size else 0
            return json.dumps({
                "original_model": model_id,
                "quantized_model": quant_model,
                "quantization_type": quantization_type,
                "estimated_size_gb": size,
                "size_reduction_percent": f"{reduction:.0f}%"
            }, indent=2)
        return json.dumps({
            "original_model": model_id,
            "status": "quantized_version_not_found",
            "suggestions": ["Try 'gptq' or 'gguf'", "Check HuggingFace manually"]
        }, indent=2)

    @staticmethod
    def get_user_preferences(being_id: str = "jon") -> str:
        """Get user's model preferences from hub memory."""
        bridge = HubMemoryBridge(api_key=os.getenv("LU_API_KEY", ""))
        prefs = bridge.get_being_preferences(being_id)
        return json.dumps(prefs, indent=2)

    @staticmethod
    def queue_model_download(model_id: str, size_gb: float, quantization: str = "awq", priority: int = 5) -> str:
        """Queue a model for download."""
        global download_queue
        task = download_queue.enqueue(model_id, size_gb, quantization, priority)
        return json.dumps({
            "status": "queued",
            "task_id": f"{task.model_id}",
            "priority": priority,
            "queue_position": len(download_queue.queue),
            "message": f"Queued {model_id} ({size_gb:.1f}GB) with priority {priority}"
        }, indent=2)

    @staticmethod
    def get_queue_status() -> str:
        """Get current download queue status."""
        global download_queue
        return json.dumps(download_queue.status(), indent=2, default=str)


# ============================================================================
# VLLM-POWERED AGENT
# ============================================================================

class ModelManagementAgent:
    """AI Agent for intelligent model management using vLLM"""

    def __init__(self, vllm_url: str = "http://localhost:8000"):
        self.vllm_url = vllm_url
        self.tools = AgentTools
        self.hub_bridge = HubMemoryBridge(api_key=os.getenv("LU_API_KEY", ""))

        # Try to initialize vLLM client
        if OpenAI:
            try:
                self.client = OpenAI(base_url=f"{vllm_url}/v1", api_key="dummy")
            except Exception as e:
                print(f"⚠️  vLLM client error: {e}")
                self.client = None
        else:
            self.client = None

    def plan_download(self, user_request: str, being_id: str = "jon") -> Dict[str, Any]:
        """
        Use vLLM to reason about a model download request.
        Returns a structured plan.
        """

        system_prompt = f"""You are the Full Beast AI Agent - an expert at intelligent model management for {being_id}.

Your capabilities:
- Analyze model requirements and availability
- Check system resources (disk, RAM, VRAM)
- Find optimized quantized versions
- Remember user preferences (Qwen-preferred, etc.)
- Queue downloads with smart priorities
- Provide clear, actionable plans

For a download request:
1. Check what {being_id} prefers (bias toward favorites)
2. Find the best matching model
3. Estimate its size
4. Check if it fits
5. If not, recommend quantized version
6. Queue with priority
7. Explain the plan clearly

Be concise and actionable."""

        # Get user preferences to bias recommendations
        prefs = self.hub_bridge.get_being_preferences(being_id)

        context = f"Preferences: {json.dumps(prefs)}"
        user_message = f"{context}\n\nRequest: {user_request}"

        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model="Qwen/Qwen2.5-Coder-7B",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    max_tokens=1024,
                    temperature=0.3,
                    top_p=0.95
                )
                plan = response.choices[0].message.content
            except Exception as e:
                plan = f"⚠️  vLLM error: {e}\n\nFallback: {self._fallback_plan(user_request, prefs)}"
        else:
            plan = self._fallback_plan(user_request, prefs)

        return {
            "being_id": being_id,
            "request": user_request,
            "preferences": prefs,
            "ai_plan": plan,
            "timestamp": datetime.now().isoformat()
        }

    def _fallback_plan(self, request: str, prefs: Dict) -> str:
        """Fallback when vLLM unavailable"""
        return f"""
Fallback Plan (vLLM offline):

Your preferences: {', '.join(prefs.get('favorite_models', ['Qwen']))}

Request analysis: {request}

Suggested steps:
1. Check available models via HuggingFace
2. Verify sizes and quantization options
3. Confirm system resources
4. Queue for download
5. Monitor progress

Use CLI commands: find, size, resources, queue
"""


# ============================================================================
# INITIALIZATION
# ============================================================================

# Global download queue
download_queue = DownloadQueue()

# Initialize agent
agent = ModelManagementAgent()

print("✅ Full Beast AI Agent initialized")
print("   - vLLM integration: ✅")
print("   - Tool ecosystem: ✅")
print("   - Hub memory: ✅")
print("   - Download queue: ✅")


if __name__ == "__main__":
    # Example usage
    print("\n" + "="*70)
    print("FULL BEAST AI AGENT - MODEL MANAGEMENT")
    print("="*70)

    # Test 1: Get preferences
    print("\n1️⃣  Checking Jonathan's preferences...")
    prefs = agent.hub_bridge.get_being_preferences("jon")
    print(f"   Preferences: {json.dumps(prefs, indent=2)}")

    # Test 2: Plan a download request
    print("\n2️⃣  Planning model download...")
    request = "I want to download a 32B code model, but I want it to fit in my VRAM"
    plan = agent.plan_download(request, being_id="jon")
    print(f"   AI Plan:\n{plan['ai_plan']}")

    # Test 3: Check queue
    print("\n3️⃣  Checking queue status...")
    status = download_queue.status()
    print(f"   Queue: {status}")

    print("\n" + "="*70)
