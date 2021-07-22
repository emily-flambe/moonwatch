from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.options import Options
import os
import time as t

CHROMEDRIVER_PATH = os.environ.get('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
GOOGLE_CHROME_BIN = os.environ.get('GOOGLE_CHROME_BIN', '/usr/bin/google-chrome')

options = Options()
options.binary_location = GOOGLE_CHROME_BIN
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.headless = True

driver = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH , chrome_options=options)
print("WOW the driver works")
url = f'https://www.google.com/search?q=GME+stock'
driver.get(url)
print("got the URL. Waiting 2 seconds...")
t.sleep(2)
print("OK grabbing a screenshot now")
driver.save_screenshot(f"GME_google_screenshot.png")
print("Closing the webdriver")
driver.close()
print("I think we did it!")