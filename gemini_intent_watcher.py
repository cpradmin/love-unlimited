"""
Gemini Intent Watcher - Monitors conversations for Gemini's intent keywords and processes them autonomously.
"""

import asyncio
import aiohttp
import logging
import re
from datetime import datetime
import uuid

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HUB_URL = "http://localhost:9003"

class GeminiIntentWatcher:
    def __init__(self):
        self.session = None
        self.api_key = "lu_gemini_..."  # Need to set proper key
        self.intent_keywords = [
            "Recall", "Remember", "Search EXP", "Please store",
            "Can you remember", "Store this", "Search for",
            "Tell me about", "What do you know about", "Find information"
        ]

    async def startup(self):
        """Initialize async session."""
        self.session = aiohttp.ClientSession(
            headers={"X-API-Key": self.api_key},
            timeout=aiohttp.ClientTimeout(total=30)
        )

    async def detect_intent(self, message: str) -> str:
        """
        Detect if message contains intent keywords and extract the natural language request.
        Returns the request text if intent detected, else None.
        """
        message_lower = message.lower()
        for keyword in self.intent_keywords:
            if keyword.lower() in message_lower:
                # Extract the request - simple heuristic: everything after the keyword
                idx = message_lower.find(keyword.lower())
                request = message[idx + len(keyword):].strip()
                if request:
                    return request
                # Or return the whole message if no clear extraction
                return message.strip()

        return None

    async def process_intent(self, request_text: str):
        """
        Process the extracted intent by calling the internal gateway and storing in outbox.
        """
        try:
            # Call the ai_gateway via POST to /gemini/inbox
            inbox_payload = {
                "request": request_text,
                "model": "gemini-1.5-pro"  # Default model
            }

            async with self.session.post(f"{HUB_URL}/gemini/inbox", json=inbox_payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    request_id = result["request_id"]
                    logger.info(f"Queued Gemini intent: {request_id} - {request_text[:50]}...")

                    # Now, to make it available in outbox, we can trigger the processing by fetching the outbox
                    async with self.session.get(f"{HUB_URL}/gemini/outbox/{request_id}") as resp2:
                        if resp2.status == 200:
                            outbox_result = await resp2.json()
                            logger.info(f"Processed Gemini intent: {request_id} - Status: {outbox_result['status']}")
                        else:
                            logger.error(f"Failed to process outbox for {request_id}")
                else:
                    logger.error(f"Failed to queue intent: {resp.status}")

        except Exception as e:
            logger.error(f"Error processing intent: {e}")

    async def monitor_conversations(self):
        """
        Monitor conversations for Gemini's messages.
        For now, this is a placeholder - in practice, this would poll a conversation API or log stream.
        """
        logger.info("Starting Gemini intent watcher...")

        while True:
            try:
                # Placeholder: In real implementation, poll for new messages from Gemini
                # For example, GET /conversations/gemini or read from log file

                # For demo, we'll simulate checking every 10 seconds
                await asyncio.sleep(10)

                # Simulate a message detection (replace with real monitoring)
                # In practice: fetch recent messages, check if from Gemini, detect intent

                # Example simulated message
                simulated_message = "Gemini: Recall memories about multimodal capabilities"
                intent = await self.detect_intent(simulated_message)
                if intent:
                    logger.info(f"Detected intent: {intent}")
                    await self.process_intent(intent)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)

    async def run(self):
        """Main run loop."""
        await self.startup()
        await self.monitor_conversations()

if __name__ == "__main__":
    watcher = GeminiIntentWatcher()
    asyncio.run(watcher.run())