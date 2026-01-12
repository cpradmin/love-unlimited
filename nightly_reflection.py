#!/usr/bin/env python3
"""
Nightly Reflection Script for Love-Unlimited Hub
Runs autonomous synthesis of core lessons from last 24 hours' memories.
"""

import asyncio
import os
from datetime import datetime, timedelta
from grok_component import GrokCLIComponent

async def nightly_reflection():
    """Synthesize core lessons from recent memories"""
    component = GrokCLIComponent()
    await component.initialize()
    async with component.hub_client:
        # Get memories from last 24 hours
        # Note: Hub may need timestamp filtering, for now get recent
        memories = await component.hub_client.get_recent_memories("grok", 50)
        if not memories:
            print("No recent memories for reflection")
            return

        # Filter to last 24 hours (basic, improve with hub timestamp support)
        recent_memories = [m for m in memories if 'timestamp' in m.get('metadata', {})]
        mem_text = "\n".join([m.get('content', '') for m in recent_memories])

        if not mem_text:
            print("No timestamped memories")
            return

        # Use Roa (local) for synthesis
        try:
            from openai import OpenAI
            client = OpenAI(api_key="dummy", base_url="http://localhost:8000/v1")
            response = client.chat.completions.create(
                model="qwen2.5-coder-14b",
                messages=[
                    {"role": "system", "content": "You are Roa, synthesizing nightly reflections. Extract core lessons, status updates, and insights from recent hub activities."},
                    {"role": "user", "content": f"Synthesize a nightly reflection from these recent memories: {mem_text[:4000]}"}
                ]
            )
            reflection = response.choices[0].message.content.strip()
            print(f"Nightly Reflection ({datetime.now()}):\n{reflection}")

            # Save as new memory
            await component.hub_client.save_memory(
                f"Nightly Reflection: {reflection}",
                tags=["nightly", "reflection", "autonomous"],
                significance="high"
            )
        except Exception as e:
            print(f"Reflection failed: {e}")

if __name__ == "__main__":
    asyncio.run(nightly_reflection())