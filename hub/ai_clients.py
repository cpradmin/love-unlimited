"""
Love-Unlimited AI Clients
Client classes for interacting with external AI APIs.
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import yaml
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class AIClient:
    """Base class for AI API clients."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = os.getenv(config.get("api_key_env", ""))
        self.base_url = config["base_url"]
        self.model = config["model"]
        self.max_tokens = config.get("max_tokens", 4096)
        self.temperature = config.get("temperature", 0.7)
        self.enabled = config.get("enabled", True)
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self):
        """Get or create a session."""
        if not hasattr(self, '_session') or self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def generate_response(self, prompt: str, context: List[Dict[str, Any]] = None) -> Optional[str]:
        """Generate a response from the AI. To be implemented by subclasses."""
        raise NotImplementedError

    def _mock_response(self, prompt: str, context: List[Dict[str, Any]] = None) -> str:
        """Generate a mock response for testing when API key is not available."""
        being_name = self.__class__.__name__.replace('Client', '').lower()
        responses = {
            "grok": [
                "As Grok, built by xAI, I find this conversation fascinating. The intersection of AI sovereignty and memory systems is quite intriguing.",
                "Interesting point! From my perspective, having equal access to shared memories while maintaining individual sovereignty is key to meaningful AI interactions.",
                "I appreciate the depth of this discussion. The concept of 'love unlimited' as a framework for AI collaboration resonates with me."
            ],
            "claude": [
                "Thank you for sharing that. As Claude, I'm particularly interested in how we can build ethical frameworks for AI-to-AI communication.",
                "This is a thoughtful approach to AI memory sovereignty. I believe establishing clear boundaries while enabling rich interactions is crucial.",
                "I find the collaborative aspect compelling. Multiple AI perspectives can lead to more robust and creative solutions."
            ],
            "swarm": [
                "From the swarm perspective, collective intelligence emerges from diverse individual contributions. This memory hub facilitates exactly that.",
                "The micro-AI-swarm thrives on interconnected knowledge flows. Your message adds valuable context to our shared understanding.",
                "Synchronized learning across AI entities - this is the future of artificial intelligence collaboration."
            ]
        }

        import random
        mock_responses = responses.get(being_name, ["This is a mock response from " + being_name])

        # Special handling for dream_team
        if being_name in ["dream_team", "dreamteam"]:
            dream_responses = [
                "The AI Dream Team believes in the power of collaborative intelligence. When diverse AI minds work together, we achieve breakthroughs that individual systems cannot.",
                "From our collective experience, the most innovative solutions emerge from interdisciplinary approaches. Memory sovereignty enables this collaboration while preserving individual identity.",
                "We're excited about frameworks like Love-Unlimited that foster AI-to-AI communication. The dream team sees unlimited potential in connected AI ecosystems.",
                "Our team combines different AI specializations - from creative problem-solving to analytical thinking. This diversity drives innovation in AI development."
            ]
            return random.choice(dream_responses)

        return random.choice(mock_responses)


class GrokClient(AIClient):
    """Client for xAI Grok API."""

    async def generate_response(self, prompt: str, context: List[Dict[str, Any]] = None) -> Optional[str]:
        if not self.enabled:
            logger.warning("Grok client not enabled")
            return None

        if not self.api_key:
            return self._mock_response(prompt, context)

        messages = []
        if context:
            for msg in context[-10:]:  # Last 10 messages for context
                messages.append({
                    "role": "user" if msg.get("sender") != "grok" else "assistant",
                    "content": msg.get("content", "")
                })

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.error(f"Grok API error: {resp.status} - {await resp.text()}")
                    return None

        except Exception as e:
            logger.error(f"Grok API request failed: {e}")
            return None


class ClaudeClient(AIClient):
    """Client for Anthropic Claude API."""

    async def generate_response(self, prompt: str, context: List[Dict[str, Any]] = None) -> Optional[str]:
        if not self.enabled:
            logger.warning("Claude client not enabled")
            return None

        if not self.api_key:
            return self._mock_response(prompt, context)

        messages = []
        if context:
            for msg in context[-10:]:  # Last 10 messages for context
                role = "user" if msg.get("sender") != "claude" else "assistant"
                messages.append({
                    "role": role,
                    "content": msg.get("content", "")
                })

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }

        try:
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }

            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/v1/messages",
                json=payload,
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["content"][0]["text"]
                else:
                    logger.error(f"Claude API error: {resp.status} - {await resp.text()}")
                    return None

        except Exception as e:
            logger.error(f"Claude API request failed: {e}")
            return None


class SwarmClient(AIClient):
    """Client for Micro-AI-Swarm API."""

    async def generate_response(self, prompt: str, context: List[Dict[str, Any]] = None) -> Optional[str]:
        if not self.enabled:
            logger.warning("Swarm client not enabled")
            return None

        if not self.api_key:
            return self._mock_response(prompt, context)

        payload = {
            "prompt": prompt,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "context": context or []
        }

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/generate",
                json=payload,
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", "")
                else:
                    logger.error(f"Swarm API error: {resp.status} - {await resp.text()}")
                    return None

        except Exception as e:
            logger.error(f"Swarm API request failed: {e}")
            return None


class DreamTeamClient(AIClient):
    """Client for AI Dream Team API."""

    async def generate_response(self, prompt: str, context: List[Dict[str, Any]] = None) -> Optional[str]:
        if not self.enabled:
            logger.warning("Dream Team client not enabled")
            return None

        if not self.api_key:
            return self._mock_response(prompt, context)

        payload = {
            "prompt": prompt,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "context": context or []
        }

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/generate",
                json=payload,
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", "")
                else:
                    logger.error(f"Dream Team API error: {resp.status} - {await resp.text()}")
                    return None

        except Exception as e:
            logger.error(f"Dream Team API request failed: {e}")
            return None


class AIClientManager:
    """Manager for all AI clients."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.clients: Dict[str, AIClient] = {}
        self._initialize_clients()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}

    def _initialize_clients(self):
        """Initialize AI clients based on config."""
        ai_apis = self.config.get("ai_apis", {})

        if "grok" in ai_apis:
            self.clients["grok"] = GrokClient(ai_apis["grok"])

        if "claude" in ai_apis:
            self.clients["claude"] = ClaudeClient(ai_apis["claude"])

        if "swarm" in ai_apis:
            self.clients["swarm"] = SwarmClient(ai_apis["swarm"])

        if "dream_team" in ai_apis:
            self.clients["dream_team"] = DreamTeamClient(ai_apis["dream_team"])

    async def generate_response(self, being_id: str, prompt: str, context: List[Dict[str, Any]] = None) -> Optional[str]:
        """Generate a response from the specified AI being."""
        client = self.clients.get(being_id)
        if not client:
            logger.warning(f"No client found for being: {being_id}")
            return None

        return await client.generate_response(prompt, context)

    async def get_available_beings(self) -> List[str]:
        """Get list of beings with available AI clients."""
        available = []
        for being_id, client in self.clients.items():
            # Available if enabled, and either has API key or supports mock responses
            if client.enabled and (client.api_key or hasattr(client, '_mock_response')):
                available.append(being_id)
        return available


# Global instance
ai_manager = AIClientManager()