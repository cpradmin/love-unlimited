import undetected_chromedriver as uc
options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
# optional stealth extras
options.add_argument("--disable-blink-features=AutomationControlled")
driver = uc.Chrome(options=options)

driver.get("https://www.google.com")
print("Title:", driver.title)
driver.quit()
print("Test done")