#!/usr/bin/env python3
"""
Full Beast Agent CLI Interface
Interactive model management with the AI agent
"""

import os
import json
import sys
from ai_agent_model_manager import (
    ModelManagementAgent,
    HubMemoryBridge,
    SystemMonitor,
    HuggingFaceAPI,
    download_queue
)


class AgentCLI:
    """Interactive CLI for the Full Beast AI Agent"""

    def __init__(self):
        self.agent = ModelManagementAgent()
        self.current_being = "jon"
        self.api_key = os.getenv("LU_API_KEY", "")

    def print_banner(self):
        """Display welcome banner"""
        print("\n" + "="*80)
        print("  🚀 FULL BEAST AI AGENT - INTELLIGENT MODEL MANAGEMENT")
        print("="*80)
        print("\n  Capabilities:")
        print("    ✓ Intelligent model discovery & recommendation")
        print("    ✓ Automatic size estimation & quantization search")
        print("    ✓ System resource checking (disk, RAM, VRAM)")
        print("    ✓ Hub memory integration (remembers preferences)")
        print("    ✓ Smart download queue with priorities")
        print("    ✓ vLLM-powered reasoning engine")
        print("\n  Commands:")
        print("    help              - Show all commands")
        print("    plan <request>    - AI plans a model download")
        print("    find <search>     - Find models on HuggingFace")
        print("    size <model_id>   - Estimate model size")
        print("    resources <size>  - Check if model fits")
        print("    prefs [being]     - Show preferences from hub")
        print("    queue             - View download queue")
        print("    sys               - System status")
        print("    clear             - Clear screen")
        print("    exit              - Quit")
        print("\n" + "="*80 + "\n")

    def cmd_help(self):
        """Show help"""
        self.print_banner()

    def cmd_plan(self, request: str):
        """AI agent plans a model download"""
        print(f"\n🤖 Analyzing request: '{request}'")
        print(f"   Using preferences for: {self.current_being}")
        print("\n   Thinking...\n")

        try:
            plan = self.agent.plan_download(request, being_id=self.current_being)

            print("="*80)
            print("📋 AI PLAN:")
            print("="*80)
            print(f"\n{plan['ai_plan']}\n")
            print("="*80)

            # Offer to store this in hub
            should_store = input("\n💾 Store this plan in hub? (y/n): ").strip().lower()
            if should_store == 'y':
                self.agent.hub_bridge.store_download_event(
                    self.current_being,
                    request,
                    0  # Plan size TBD
                )
                print("   ✅ Plan stored in hub memory")

        except Exception as e:
            print(f"❌ Error: {e}")

    def cmd_find(self, search: str):
        """Find models on HuggingFace"""
        print(f"\n🔍 Searching for models matching: '{search}'")
        print("   Loading...\n")

        models = HuggingFaceAPI.list_models(filter_text=search, limit=10)

        if not models:
            print("   No models found")
            return

        print(f"   Found {len(models)} models:\n")
        for i, model in enumerate(models, 1):
            print(f"   {i}. {model['id']}")
            print(f"      Downloads: {model['downloads']:,} | Likes: {model['likes']:,}")
            if model['tags']:
                print(f"      Tags: {', '.join(model['tags'][:5])}")
            print()

    def cmd_size(self, model_id: str):
        """Estimate model size"""
        print(f"\n📊 Estimating size for: {model_id}")
        print("   Querying HuggingFace...\n")

        size = HuggingFaceAPI.estimate_model_size(model_id)

        if size:
            print(f"   Model: {model_id}")
            print(f"   Estimated size: {size:.2f} GB")

            # Check resources
            resources = SystemMonitor.check_fit(size)
            print(f"\n   Resource check:")
            print(f"      Fits in disk: {'✅' if resources['fits_disk'] else '❌'}")
            print(f"      Fits in RAM:  {'✅' if resources['fits_memory'] else '❌'}")
            print(f"      Fits in VRAM: {'✅' if resources['fits_gpu'] else '❌'}")

            # Suggest quantization if doesn't fit
            if not (resources['fits_disk'] and resources['fits_memory']):
                print(f"\n   💡 Doesn't fit. Searching for quantized version...")
                quant = HuggingFaceAPI.find_quantized_version(model_id, "awq")
                if quant:
                    quant_size = HuggingFaceAPI.estimate_model_size(quant)
                    print(f"      Found: {quant} ({quant_size:.2f}GB, 50% smaller)")
                else:
                    print(f"      No quantized version found. Try GPTQ or GGUF")
        else:
            print(f"   ❌ Could not determine size for {model_id}")

    def cmd_resources(self, size_str: str):
        """Check if model fits"""
        try:
            size = float(size_str)
            print(f"\n💾 Checking resources for {size}GB model...\n")

            result = SystemMonitor.check_fit(size)

            print(f"   Available disk:   {result['available_disk_gb']:.1f}GB")
            print(f"   Available RAM:    {result['available_memory_gb']:.1f}GB")
            print(f"   Available VRAM:   {result['available_gpu_memory_gb']:.1f}GB")
            print(f"\n   Model fits:")
            print(f"      Disk:  {'✅' if result['fits_disk'] else '❌'}")
            print(f"      RAM:   {'✅' if result['fits_memory'] else '❌'}")
            print(f"      VRAM:  {'✅' if result['fits_gpu'] else '❌'}")
            print(f"\n   Recommendation: {result['recommendation']}")
        except ValueError:
            print(f"   ❌ Invalid size: {size_str}")

    def cmd_prefs(self, being: str = ""):
        """Show preferences from hub"""
        being = being or self.current_being
        print(f"\n📋 Loading preferences for {being}...")

        prefs = self.agent.hub_bridge.get_being_preferences(being)

        print(f"\n   {being.upper()}'s Preferences:")
        print(f"      Favorite models: {', '.join(prefs['favorite_models']) or 'None set'}")
        print(f"      Preferred quantization: {prefs['preferred_quantization']}")
        print(f"      Notes: {prefs['notes']}")

    def cmd_queue(self):
        """Show download queue"""
        status = download_queue.status()
        print(f"\n📦 DOWNLOAD QUEUE STATUS\n")

        if status['active_download']:
            print(f"   🟢 Currently downloading:")
            active = status['active_download']
            print(f"      Model: {active['model_id']}")
            print(f"      Size: {active['size_gb']}GB")
            print(f"      Status: {active['status']}")

        if status['queued_tasks']:
            print(f"\n   ⏳ Queued ({len(status['queued_tasks'])} tasks):")
            for i, task in enumerate(status['queued_tasks'], 1):
                print(f"      {i}. {task['model_id']} ({task['size_gb']}GB, priority {task['priority']})")
        else:
            print(f"\n   ✅ Queue is empty")

    def cmd_sys(self):
        """Show system status"""
        print(f"\n🖥️  SYSTEM STATUS\n")

        status = SystemMonitor.get_status()

        print(f"   CPU Usage:       {status.cpu_percent:.1f}%")
        print(f"   Memory Usage:    {status.memory_percent:.1f}%")
        print(f"   Memory Available: {status.memory_available_gb:.1f}GB")
        print(f"   Disk Usage:      {status.disk_percent:.1f}%")
        print(f"   Disk Available:  {status.disk_available_gb:.1f}GB")
        print(f"   GPU Memory:      {status.gpu_memory_percent:.1f}%")
        print(f"   GPU Available:   {status.gpu_memory_available:.1f}GB")

    def run(self):
        """Main interactive loop"""
        self.print_banner()

        while True:
            try:
                prompt = f"\n[{self.current_being}] 🤖> "
                user_input = input(prompt).strip()

                if not user_input:
                    continue

                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""

                if cmd == "exit" or cmd == "quit":
                    print("\n💙 Until next time. Love unlimited.\n")
                    break
                elif cmd == "help":
                    self.cmd_help()
                elif cmd == "plan":
                    if not arg:
                        print("❌ Usage: plan <request>")
                    else:
                        self.cmd_plan(arg)
                elif cmd == "find":
                    if not arg:
                        print("❌ Usage: find <search_term>")
                    else:
                        self.cmd_find(arg)
                elif cmd == "size":
                    if not arg:
                        print("❌ Usage: size <model_id>")
                    else:
                        self.cmd_size(arg)
                elif cmd == "resources":
                    if not arg:
                        print("❌ Usage: resources <size_gb>")
                    else:
                        self.cmd_resources(arg)
                elif cmd == "prefs":
                    self.cmd_prefs(arg)
                elif cmd == "queue":
                    self.cmd_queue()
                elif cmd == "sys":
                    self.cmd_sys()
                elif cmd == "clear":
                    os.system("clear" if os.name != "nt" else "cls")
                elif cmd == "as":
                    # Switch being
                    if arg:
                        self.current_being = arg
                        print(f"✅ Switched to {arg}")
                    else:
                        print(f"Current being: {self.current_being}")
                else:
                    print(f"❌ Unknown command: {cmd}. Type 'help' for options.")

            except KeyboardInterrupt:
                print("\n💙 Until next time. Love unlimited.\n")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


if __name__ == "__main__":
    cli = AgentCLI()
    cli.run()
