#!/usr/bin/env python3

import undetected_chromedriver as uc
import time

options = uc.ChromeOptions()
# GUI mode
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = uc.Chrome(options=options)

driver.get("https://grok.com")
print("Title:", driver.title)
print("URL:", driver.current_url)
print("Page source length:", len(driver.page_source))
# Print some buttons
from selenium.webdriver.common.by import By
buttons = driver.find_elements(By.TAG_NAME, "button")
print("Buttons found:", len(buttons))
for i, b in enumerate(buttons[:5]):
    print(f"Button {i}: {b.text}")

time.sleep(10)
driver.quit()
print("Debug done")