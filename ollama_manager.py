#!/usr/bin/env python3
"""
Ollama Model Manager Service
Automatically starts/stops Ollama models based on intent/requests.
"""

import asyncio
import subprocess
import time
import logging
from typing import Dict, Set
import psutil
import aiohttp
from fastapi import FastAPI
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaManager:
    def __init__(self):
        self.active_models: Set[str] = set()
        self.last_activity: Dict[str, float] = {}
        self.inactivity_timeout = 300  # 5 minutes
        
    async def is_model_running(self, model: str) -> bool:
        """Check if model is currently loaded."""
        try:
            result = await asyncio.create_subprocess_exec(
                'ollama', 'ps',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            return model in stdout.decode()
        except Exception:
            return False
    
    async def start_model(self, model: str) -> bool:
        """Start a model (non-interactive)."""
        try:
            # Use ollama serve if available, or run in background
            process = await asyncio.create_subprocess_exec(
                'ollama', 'run', model,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            # Wait a bit for startup
            await asyncio.sleep(5)
            return await self.is_model_running(model)
        except Exception as e:
            logger.error(f"Failed to start {model}: {e}")
            return False
    
    async def stop_model(self, model: str) -> bool:
        """Stop a model."""
        try:
            await asyncio.create_subprocess_exec(
                'ollama', 'stop', model
            )
            self.active_models.discard(model)
            return True
        except Exception as e:
            logger.error(f"Failed to stop {model}: {e}")
            return False
    
    async def ensure_model_running(self, model: str) -> bool:
        """Ensure model is running, start if needed."""
        if await self.is_model_running(model):
            self.last_activity[model] = time.time()
            return True
        
        logger.info(f"Starting model: {model}")
        if await self.start_model(model):
            self.active_models.add(model)
            self.last_activity[model] = time.time()
            return True
        return False
    
    async def cleanup_inactive_models(self):
        """Stop models that haven't been used recently."""
        current_time = time.time()
        to_stop = []
        
        for model, last_time in self.last_activity.items():
            if current_time - last_time > self.inactivity_timeout:
                to_stop.append(model)
        
        for model in to_stop:
            logger.info(f"Stopping inactive model: {model}")
            await self.stop_model(model)

app = FastAPI()
manager = OllamaManager()

@app.post("/ensure/{model}")
async def ensure_model(model: str):
    """Ensure a model is running."""
    success = await manager.ensure_model_running(model)
    return {"success": success, "model": model}

@app.get("/status")
async def get_status():
    """Get current status."""
    return {
        "active_models": list(manager.active_models),
        "last_activity": manager.last_activity
    }

@app.on_event("startup")
async def startup_event():
    """Start cleanup task."""
    asyncio.create_task(cleanup_task())

async def cleanup_task():
    """Periodic cleanup of inactive models."""
    while True:
        await asyncio.sleep(60)  # Check every minute
        await manager.cleanup_inactive_models()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)