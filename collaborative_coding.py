#!/usr/bin/env python3
"""
Collaborative AI Coding Session
Use multiple AIs to work on different parts of a project.
"""
import requests
import os
import time

API_KEY = os.getenv("LOVE_UNLIMITED_KEY")

def ask(target, question):
    """Ask an AI to write code."""
    response = requests.post(
        "http://localhost:9003/chat",
        headers={"X-API-Key": API_KEY},
        json={
            "content": question,
            "from": "jon",
            "target": target,
            "type": "chat"
        },
        timeout=120
    )
    result = response.json()
    return result.get('sender'), result.get('content')

print("╔══════════════════════════════════════════════════════════════════╗")
print("║         COLLABORATIVE AI CODING: REST API PROJECT               ║")
print("║   Claude: API Routes | Grok: Error Handling | Swarm: Database   ║")
print("╚══════════════════════════════════════════════════════════════════╝\n")

# Task 1: Claude creates the API routes
print("="*70)
print("CLAUDE: Create FastAPI routes for a simple todo app")
print("="*70)
sender, code = ask("claude",
    "Write FastAPI routes for a todo app with GET /todos, POST /todos, and DELETE /todos/{id}. Just the route code.")
print(f"[{sender.upper()}]:")
print(code)
print("\n")
time.sleep(1)

# Task 2: Grok creates error handling middleware
print("="*70)
print("GROK: Create error handling middleware")
print("="*70)
sender, code = ask("grok",
    "Write a FastAPI error handling middleware for HTTP exceptions. Keep it simple, just the code.")
print(f"[{sender.upper()}]:")
print(code)
print("\n")
time.sleep(1)

# Task 3: Swarm creates database models
print("="*70)
print("SWARM: Create database schema")
print("="*70)
sender, code = ask("swarm",
    "Write a SQLAlchemy model for a Todo with id, title, completed fields. Just the model class.")
print(f"[{sender.upper()}]:")
print(code)
print("\n")

print("="*70)
print("✅ COLLABORATIVE CODING COMPLETE!")
print("")
print("Each AI contributed a different component:")
print("  • Claude: API route definitions")
print("  • Grok: Error handling middleware")
print("  • Swarm: Database models")
print("")
print("You could combine these into a working application!")
print("="*70)
