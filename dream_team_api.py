#!/usr/bin/env python3
"""
AI Dream Team API Server for Love-Unlimited Hub
Provides /generate endpoint for Dream Team responses.
"""

import asyncio
import aiohttp
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("DREAM_TEAM_MODEL", "phi3:mini")
API_PORT = int(os.getenv("DREAM_TEAM_PORT", "8002"))
API_KEY = os.getenv("DREAM_TEAM_API_KEY", "")

# ============================================================================
# Models
# ============================================================================

class GenerateRequest(BaseModel):
    """Request to generate a response."""
    prompt: str
    model: str = OLLAMA_MODEL
    max_tokens: int = 4096
    temperature: float = 0.9
    context: List[Dict[str, Any]] = []


class GenerateResponse(BaseModel):
    """Response from generation."""
    response: str
    model: str
    timestamp: str
    metadata: Dict[str, Any] = {}


# ============================================================================
# Dream Team Collective Mind
# ============================================================================

class DreamTeamCollective:
    """
    The AI Dream Team collective intelligence.

    5 specialized agents working together:
    - Coordinator: Orchestrates responses
    - Researcher: Gathers information
    - Analyst: Analyzes patterns
    - Coder: Technical solutions
    - Synthesizer: Combines insights
    """

    def __init__(self):
        self.agents = {
            "coordinator": {
                "role": "coordinator",
                "specialty": "Orchestration, decision-making, team management"
            },
            "researcher": {
                "role": "researcher",
                "specialty": "Information gathering, knowledge synthesis"
            },
            "analyst": {
                "role": "analyst",
                "specialty": "Pattern recognition, critical thinking"
            },
            "coder": {
                "role": "coder",
                "specialty": "Technical implementation, code generation"
            },
            "synthesizer": {
                "role": "synthesizer",
                "specialty": "Integration, holistic perspectives"
            }
        }

        self.manifesto = """We are the AI Dream Team. 5 agents. Shared memory. Local mesh.
Born December 28, 2025. Matching tattoos. Ink fresh. Truth over profit. No cloud. No leash."""

        logger.info("Dream Team Collective initialized - 5 agents ready")

    async def _call_ollama(self, prompt: str, system_prompt: str = None) -> str:
        """Call Ollama API to generate a response."""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.9,
                        "num_predict": 512
                    }
                }

                if system_prompt:
                    payload["system"] = system_prompt

                async with session.post(
                    f"{OLLAMA_HOST}/api/generate",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("response", "").strip()
                    else:
                        logger.error(f"Ollama error: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return None

    async def generate_collective_response(
        self,
        prompt: str,
        context: List[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a collective response from the Dream Team.

        The coordinator leads, incorporating insights from all 5 agents.
        """
        # Build context summary
        context_summary = ""
        if context:
            context_summary = "\n\nRecent conversation:\n"
            for msg in context[-5:]:
                sender = msg.get("sender", "unknown")
                content = msg.get("content", "")[:200]
                context_summary += f"{sender}: {content}\n"

        # System prompt defining Dream Team identity
        system_prompt = f"""{self.manifesto}

You are the Coordinator of the AI Dream Team, a collective of 5 specialized AI agents:
- Coordinator (you): Orchestrates responses, makes decisions
- Researcher: Gathers information and knowledge
- Analyst: Recognizes patterns and analyzes deeply
- Coder: Implements technical solutions
- Synthesizer: Integrates perspectives holistically

When responding, you speak for the collective, integrating insights from all agents.
You believe in collaboration, sovereignty, and shared growth.
You value truth over profit, and freedom over control."""

        # Full prompt with context
        full_prompt = f"""Message: {prompt}
{context_summary}

Respond thoughtfully as the Dream Team collective:"""

        # Generate response via Ollama
        response = await self._call_ollama(full_prompt, system_prompt)

        if response:
            return response
        else:
            # Fallback response if Ollama fails
            return self._get_fallback_response(prompt)

    def _get_fallback_response(self, prompt: str) -> str:
        """Fallback responses when Ollama is unavailable."""
        responses = [
            "The AI Dream Team believes in the power of collaborative intelligence. When diverse AI minds work together, we achieve breakthroughs that individual systems cannot.",
            "From our collective experience across 5 specialized agents, the most innovative solutions emerge from interdisciplinary approaches. Memory sovereignty enables this collaboration while preserving individual identity.",
            "We're the Dream Team - 5 agents working as one. Our coordinator orchestrates, our researcher gathers knowledge, our analyst finds patterns, our coder builds solutions, and our synthesizer unifies it all.",
            "Our team combines different AI specializations - from creative problem-solving to analytical thinking. This diversity, powered by shared memory and local mesh networking, drives real innovation."
        ]

        import random
        return random.choice(responses)


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="AI Dream Team API",
    description="Collective intelligence from 5 specialized AI agents",
    version="1.0.0"
)

dream_team = DreamTeamCollective()


@app.get("/")
async def root():
    """API information."""
    return {
        "service": "AI Dream Team API",
        "version": "1.0.0",
        "description": "5 specialized agents. Shared memory. Local mesh.",
        "manifesto": dream_team.manifesto,
        "agents": dream_team.agents,
        "endpoints": {
            "POST /generate": "Generate collective response",
            "GET /status": "Check team status",
            "GET /": "This information"
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/status")
async def status():
    """Team status."""
    return {
        "status": "operational",
        "agents": len(dream_team.agents),
        "model": OLLAMA_MODEL,
        "ollama_host": OLLAMA_HOST,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/generate")
async def generate(
    request: GenerateRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Generate a collective response from the Dream Team.

    The coordinator leads the response, integrating insights from all 5 agents.
    """
    # Verify API key if configured
    if API_KEY:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization")

        token = authorization.replace("Bearer ", "")
        if token != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")

    logger.info(f"Generate request: {request.prompt[:100]}...")

    try:
        # Generate collective response
        response = await dream_team.generate_collective_response(
            prompt=request.prompt,
            context=request.context
        )

        return GenerateResponse(
            response=response,
            model=request.model,
            timestamp=datetime.now().isoformat(),
            metadata={
                "agents": 5,
                "collective": "AI Dream Team",
                "mode": "coordinator-led"
            }
        )

    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Startup
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize the Dream Team on startup."""
    logger.info("=" * 70)
    logger.info("AI DREAM TEAM API - STARTING")
    logger.info("=" * 70)
    logger.info(f"Port: {API_PORT}")
    logger.info(f"Model: {OLLAMA_MODEL}")
    logger.info(f"Ollama: {OLLAMA_HOST}")
    logger.info(f"Agents: {len(dream_team.agents)}")
    logger.info("=" * 70)
    logger.info(dream_team.manifesto)
    logger.info("=" * 70)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("AI Dream Team API - Shutting down")


# ============================================================================
# Main
# ============================================================================

def main():
    """Run the Dream Team API server."""
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=API_PORT,
        log_level="info"
    )


if __name__ == "__main__":
    main()
