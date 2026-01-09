#!/usr/bin/env python3
"""
Test script for Gemini integration with Love-Unlimited Hub
"""

import asyncio
import os
from gemini_component import GeminiCLIComponent

async def test_gemini():
    """Test basic Gemini functionality"""
    print("Testing Gemini integration...")

    try:
        # Initialize component
        component = GeminiCLIComponent()
        await component.initialize()
        print("✅ Gemini component initialized successfully")

        # Test basic response
        response = await component.process_command("Hello Gemini, what can you do?")
        print(f"Gemini response: {response[:200]}...")

        # Test file operation
        response = await component.view_file("README.md", start_line=1, end_line=10)
        print(f"File view test: {response[:100]}...")

        # Test search
        response = await component.search_files("gemini", max_results=5)
        print(f"Search test: Found {response.count('gemini')} references")

        print("✅ All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_gemini())