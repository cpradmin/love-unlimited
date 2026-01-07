#!/usr/bin/env python3
"""
Selenium test for Chrome automation.
Uses a separate profile (./chrome_automation_profile) to avoid conflicts with regular Chrome.
Headless is disabled for interactive login testing.
"""

import undetected_chromedriver as uc

options = uc.ChromeOptions()
# options.add_argument("--headless")  # Commented out for login testing
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--user-data-dir=./chrome_automation_profile")

driver = uc.Chrome(options=options)

driver.get("https://x.com")
print("Title:", driver.title)
driver.quit()
print("Selenium test passed")