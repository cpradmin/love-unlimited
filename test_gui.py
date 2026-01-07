#!/usr/bin/env python3

import undetected_chromedriver as uc
import time

options = uc.ChromeOptions()
# no headless
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = uc.Chrome(options=options)

driver.get("https://www.google.com")
print("Title:", driver.title)
time.sleep(5)
driver.quit()
print("GUI test done")