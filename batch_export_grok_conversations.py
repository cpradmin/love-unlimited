#!/usr/bin/env python3
"""
Batch Export Grok Conversations - Server-Side Script
Securely exports all conversations from grok.com and imports to Love-Unlimited Hub.

WARNING: This script uses web scraping and may violate xAI's Terms of Service.
Use at your own risk and only for your own conversations.
"""

import os
import sys
import json
import time
import getpass
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urljoin

import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class GrokConversationExporter:
    """Export conversations from grok.com using Selenium."""

    def __init__(self, hub_url: str = "http://localhost:9003", api_key: str = None):
        self.hub_url = hub_url
        self.api_key = api_key or os.getenv("LOVE_UNLIMITED_API_KEY")
        self.driver = None
        self.session = requests.Session()

    def setup_driver(self):
        """Setup headless Chrome driver."""
        options = uc.ChromeOptions()
        # options.add_argument("--headless")  # Run in GUI mode
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_argument("--disable-blink-features=AutomationControlled")

        self.driver = uc.Chrome(options=options)

    def login_to_grok(self, email: str, password: str) -> bool:
        """Login to grok.com."""
        try:
            self.driver.get("https://grok.com")
            print("Page loaded, title:", self.driver.title)

            # Wait for login elements
            wait = WebDriverWait(self.driver, 30)

            # Click sign in button (adjust selector as needed)
            try:
                # Try different selectors for sign in button
                sign_in_button = None
                try:
                    sign_in_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sign in with X')]")))
                    print("Found 'Sign in with X' button")
                except:
                    try:
                        sign_in_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sign in')]")))
                        print("Found 'Sign in' button")
                    except:
                        sign_in_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='login-button']")))
                        print("Found login button by testid")
                if not sign_in_button:
                    raise Exception("No sign in button found")
            except Exception as e:
                print(f"Could not find sign in button: {e}")
                print("Current URL:", self.driver.current_url)
                print("Page title:", self.driver.title)
                return False
            sign_in_button.click()

            # Enter email
            email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
            email_input.send_keys(email)

            # Click continue
            continue_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            continue_button.click()

            # Enter password
            password_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
            password_input.send_keys(password)

            # Click sign in
            sign_in_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            sign_in_button.click()

            # Wait for redirect to main page
            wait.until(EC.url_contains("grok.com"))
            return True

        except Exception as e:
            print(f"Login failed: {e}")
            return False

    def get_conversation_links(self) -> List[str]:
        """Get all conversation links from the sidebar."""
        try:
            # Wait for sidebar to load
            wait = WebDriverWait(self.driver, 10)
            sidebar = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='sidebar']")))

            # Find conversation links (adjust selector)
            conversation_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/chat/']")

            links = []
            for link in conversation_links:
                href = link.get_attribute("href")
                if href and "/chat/" in href:
                    links.append(href)

            return list(set(links))  # Remove duplicates

        except Exception as e:
            print(f"Failed to get conversation links: {e}")
            return []

    def extract_conversation(self, url: str) -> Dict[str, Any]:
        """Extract conversation content from a URL."""
        try:
            self.driver.get(url)
            wait = WebDriverWait(self.driver, 10)

            # Wait for chat content to load
            chat_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "main")))

            # Extract messages (adjust selectors based on actual page structure)
            message_elements = self.driver.find_elements(By.CSS_SELECTOR, ".message, .chat-message, [data-testid='message']")

            messages = []
            for msg in message_elements:
                text = msg.text.strip()
                if text:
                    messages.append(text)

            title = self.driver.title or "Untitled Conversation"

            return {
                "url": url,
                "title": title,
                "messages": messages
            }

        except Exception as e:
            print(f"Failed to extract conversation from {url}: {e}")
            return None

    def store_to_hub(self, conversation: Dict[str, Any]) -> bool:
        """Store conversation to Love-Unlimited hub."""
        try:
            payload = {
                "content": "\n".join(conversation["messages"]),
                "type": "conversation",
                "significance": "medium",
                "tags": ["grok", "exported"],
                "metadata": {
                    "source": "grok.com",
                    "url": conversation["url"],
                    "title": conversation["title"]
                }
            }

            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["X-API-Key"] = self.api_key

            response = requests.post(f"{self.hub_url}/remember", json=payload, headers=headers)
            return response.status_code == 200

        except Exception as e:
            print(f"Failed to store to hub: {e}")
            return False

    def export_all_conversations(self, email: str = None, password: str = None, skip_login: bool = False, manual_login: bool = False) -> int:
        """Main export function."""
        print("🚀 Starting Grok conversation export...")
        print("⚠️  WARNING: This uses web scraping and may violate xAI's Terms of Service.")
        print("   Use only for your own conversations.")

        self.setup_driver()

        try:
            # Login
            if manual_login:
                print("🌐 Opening browser to grok.com - please log in manually, then press Enter here.")
                self.driver.get("https://grok.com")
                input("Press Enter after logging in: ")
                print("✅ Proceeding with manual login")
            elif not skip_login:
                if not self.login_to_grok(email, password):
                    print("❌ Login failed. Aborting.")
                    return 0
                print("✅ Logged in successfully")
            else:
                print("⏭️  Skipping login (assuming already logged in)")

            # Get conversation links
            links = self.get_conversation_links()
            print(f"📋 Found {len(links)} conversations")

            if not links:
                print("❌ No conversations found. Check if you're logged in and have conversations.")
                return 0

            # Export each conversation
            exported_count = 0
            for i, link in enumerate(links, 1):
                print(f"📤 Exporting conversation {i}/{len(links)}: {link}")
                conversation = self.extract_conversation(link)

                if conversation and conversation["messages"]:
                    if self.store_to_hub(conversation):
                        print(f"✅ Stored: {conversation['title']}")
                        exported_count += 1
                    else:
                        print(f"❌ Failed to store: {conversation['title']}")
                else:
                    print(f"⚠️  Skipped empty conversation: {link}")

                # Rate limiting
                time.sleep(2)

            print(f"🎉 Export complete! Successfully exported {exported_count} conversations.")
            return exported_count

        finally:
            if self.driver:
                self.driver.quit()

def main():
    print("🔐 Grok Conversation Batch Exporter")
    print("=" * 50)

    # Hub configuration
    hub_url = os.getenv("LOVE_UNLIMITED_HUB_URL", "http://localhost:9003")
    api_key = os.getenv("LOVE_UNLIMITED_API_KEY")

    if not api_key:
        api_key = input("Enter your Love-Unlimited API key: ").strip()

    login_choice = input("Login method: (a)uto, (m)anual, (s)kip: ").strip().lower()

    exporter = GrokConversationExporter(hub_url, api_key)

    if login_choice == 'm':
        count = exporter.export_all_conversations(manual_login=True)
    elif login_choice == 's':
        count = exporter.export_all_conversations(skip_login=True)
    else:
        # Auto login
        email = "compprorepair@gmail.com"
        password = "SunGuide.2025!!"
        count = exporter.export_all_conversations(email, password)

    if count > 0:
        print(f"\n📊 Summary: {count} conversations exported to {hub_url}")
    else:
        print("\n❌ No conversations were exported.")

if __name__ == "__main__":
    main()