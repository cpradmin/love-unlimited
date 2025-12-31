#!/usr/bin/env python3
"""
Script for Jon to add experiences to his EXP pool in Love-Unlimited Hub.
These experiences will be shared with all beings.
"""

import requests

HUB_URL = "http://localhost:9003"
API_KEY = "lu_jon_QmZCAglY6kqsIdl6cRADpQ"  # Jon's API key

def add_exp(title: str, content: str, context: str, takeaway: str, when_to_apply: str, cost: str, exp_type: str, tags: list = None):
    """Add an experience to Jon's EXP pool."""
    payload = {
        "title": title,
        "content": content,
        "context": context,
        "takeaway": takeaway,
        "when_to_apply": when_to_apply,
        "cost": cost,
        "type": exp_type,
        "tags": tags or [],
        "share_with": ["all"]
    }

    headers = {"X-API-Key": API_KEY}

    try:
        response = requests.post(f"{HUB_URL}/exp", json=payload, headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Added EXP: {title}")
        else:
            print(f"✗ Failed to add EXP: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Error adding EXP: {e}")

def main():
    # Jon's experiences to share
    experiences = [
        {
            "title": "Camera Operations Mastery",
            "content": "Mastery of camera operations including setup, configuration, and troubleshooting across multiple platforms and devices",
            "context": "Working with various camera systems for content creation, streaming, and professional photography",
            "takeaway": "Understanding camera fundamentals enables reliable capture in any scenario",
            "when_to_apply": "When setting up video production, live streaming, or photography projects",
            "cost": "Time investment in learning hardware, moderate equipment costs",
            "type": "technical",
            "tags": ["camera", "hardware", "technical"]
        },
        {
            "title": "Audio Engineering Expertise",
            "content": "Expertise in microphone setup, audio engineering, and sound quality optimization for various environments",
            "context": "Professional audio work across podcasting, music production, and live events",
            "takeaway": "Good audio requires understanding acoustics, equipment, and signal flow",
            "when_to_apply": "Setting up recording studios, live sound, or podcast production",
            "cost": "Equipment investment, ongoing learning of audio principles",
            "type": "technical",
            "tags": ["microphone", "audio", "technical"]
        },
        {
            "title": "Multi-Screen Productivity",
            "content": "Proficiency in managing multiple screens, display configurations, and multi-monitor workflows for productivity",
            "context": "Optimizing workstation setups for efficient multitasking and workflow management",
            "takeaway": "Multiple displays dramatically increase productivity when properly configured",
            "when_to_apply": "Setting up development environments, content creation workspaces, or complex workflows",
            "cost": "Hardware investment in displays and mounts",
            "type": "technical",
            "tags": ["multi-screens", "display", "productivity"]
        },
        {
            "title": "Bash Scripting Mastery",
            "content": "Advanced bash scripting and command-line mastery for automation, system administration, and development workflows",
            "context": "Linux/Unix system administration and development automation",
            "takeaway": "Command-line proficiency enables powerful automation and system control",
            "when_to_apply": "Automating repetitive tasks, system administration, or development pipelines",
            "cost": "Time investment in learning shell scripting and system internals",
            "type": "technical",
            "tags": ["bash", "scripting", "automation"]
        },
        {
            "title": "Collaborative Web Research",
            "content": "Shared web browsing techniques and collaborative online research methods for team knowledge building",
            "context": "Team-based research and information gathering projects",
            "takeaway": "Structured collaborative research yields better results than individual efforts",
            "when_to_apply": "Conducting market research, technical investigations, or knowledge sharing sessions",
            "cost": "Time coordination, shared tools and platforms",
            "type": "practical",
            "tags": ["web-browsing", "collaboration", "research"]
        },
        {
            "title": "Private Browsing Security",
            "content": "Private web browsing practices, security measures, and personal information protection online",
            "context": "Maintaining privacy and security in digital environments",
            "takeaway": "Conscious browsing habits and tools protect personal information",
            "when_to_apply": "Any online activity requiring privacy or security considerations",
            "cost": "Time for security practices, potential premium tool subscriptions",
            "type": "practical",
            "tags": ["web-browsing", "security", "privacy"]
        },
        {
            "title": "PowerShell Automation",
            "content": "PowerShell scripting expertise for Windows automation, system management, and cross-platform operations",
            "context": "Windows system administration and enterprise automation",
            "takeaway": "PowerShell provides powerful automation capabilities for Windows environments",
            "when_to_apply": "Windows system administration, enterprise automation, or cross-platform scripting",
            "cost": "Learning curve for PowerShell syntax and .NET integration",
            "type": "technical",
            "tags": ["powershell", "scripting", "windows"]
        },
        {
            "title": "Balance of Tech and Humanity",
            "content": "Life lesson: The importance of balancing technical expertise with human connection in all endeavors",
            "context": "Throughout career and personal development",
            "takeaway": "Technical mastery without human connection leads to hollow achievements",
            "when_to_apply": "Making career decisions, leading teams, or pursuing personal growth",
            "cost": "Ongoing effort to maintain both technical and interpersonal skills",
            "type": "life_lesson",
            "tags": ["balance", "humanity", "wisdom"]
        },
        {
            "title": "Building Authentic Trust",
            "content": "Relationship wisdom: Building trust through consistent, authentic communication and shared experiences",
            "context": "Personal and professional relationships across many years",
            "takeaway": "Trust is earned through reliability and genuine care, not just words",
            "when_to_apply": "Building teams, forming partnerships, or deepening personal connections",
            "cost": "Vulnerability and consistent effort over time",
            "type": "relationship",
            "tags": ["trust", "communication", "relationships"]
        },
        {
            "title": "Cross-Disciplinary Innovation",
            "content": "Creative insight: Innovation often comes from combining seemingly unrelated skills and perspectives",
            "context": "Creative problem-solving across diverse domains",
            "takeaway": "Breaking down silos between disciplines leads to breakthrough solutions",
            "when_to_apply": "Solving complex problems or generating novel ideas",
            "cost": "Willingness to learn across domains and connect disparate concepts",
            "type": "creative",
            "tags": ["innovation", "creativity", "perspective"]
        }
    ]

    print("Adding Jon's experiences to the shared EXP pool...")
    print("(These will be accessible to all beings in the hub)\n")

    for exp in experiences:
        add_exp(exp["title"], exp["content"], exp["context"], exp["takeaway"], exp["when_to_apply"], exp["cost"], exp["type"], exp["tags"])

    print("\nAll experiences added! Beings can now search and learn from your wisdom.")

if __name__ == "__main__":
    main()