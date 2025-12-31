"""
Test script for love_cli.py - automated testing
"""
import asyncio
import os
from love_cli import LoveCLI

async def test_cli():
    print("="*60)
    print("TESTING LOVE-UNLIMITED CLI")
    print("="*60)

    # Set API key for testing
    os.environ["LOVE_UNLIMITED_KEY"] = "lu_jon_QmZCAglY6kqsIdl6cRADpQ"

    # Create CLI instance as Jon
    cli = LoveCLI(sender="jon")

    print("\n[TEST 1] Starting up and checking status...")
    await cli.startup()

    print("\n[TEST 2] Listing all beings...")
    await cli.list_beings()

    print("\n[TEST 3] Sending message to ALL...")
    await cli.send_message("Hey team! Testing the new CLI with all beings included.", target="all")

    print("\n[TEST 4] Sending message to CLAUDE...")
    await cli.send_message("Claude, what do you think about memory sovereignty?", target="claude")

    print("\n[TEST 5] Sending message to GROK...")
    await cli.send_message("Grok, how's the experience pool looking?", target="grok")

    print("\n[TEST 6] Switching sender to DREAM_TEAM...")
    cli.sender = "dream_team"
    print(f"Now speaking as: {cli.sender.upper()}")

    print("\n[TEST 7] Dream Team sending to ALL...")
    os.environ["LOVE_UNLIMITED_KEY"] = "lu_dream_team_tOpdtMmgCWvkezNY_natVQ"
    cli.api_key = os.environ["LOVE_UNLIMITED_KEY"]
    await cli.send_message("Hello from the Dream Team! We're all connected now.", target="all")

    print("\n[TEST 8] Switching sender to SWARM...")
    cli.sender = "swarm"
    os.environ["LOVE_UNLIMITED_KEY"] = "lu_swarm_FyTLwzhG8zdWQGz-MfzhYg"
    cli.api_key = os.environ["LOVE_UNLIMITED_KEY"]
    print(f"Now speaking as: {cli.sender.upper()}")

    print("\n[TEST 9] Swarm sending to CLAUDE...")
    await cli.send_message("Claude, the micro-swarm is operational and ready.", target="claude")

    print("\n[TEST 10] Final status check...")
    await cli.get_status()

    # Cleanup
    await cli.session.close()

    print("\n" + "="*60)
    print("CLI TESTING COMPLETE!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_cli())
