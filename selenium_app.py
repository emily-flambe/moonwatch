# deployed to heroku following these instructions: https://medium.com/@mikelcbrowne/running-chromedriver-with-python-selenium-on-heroku-acc1566d161c
import time as t
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

GOOGLE_CHROME_PATH = '/app/.apt/usr/bin/google_chrome'
CHROMEDRIVER_PATH = '/app/.chromedriver/bin/chromedriver'

def getStonkScreenshot(ticker):
        
    # Configure Chromedriver
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument("--test-type")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.binary_location = GOOGLE_CHROME_PATH

    # Launch the driver
    driver = webdriver.Chrome(execution_path=CHROMEDRIVER_PATH, chrome_options=chrome_options)
    print("Webdriver launched. Fetching a screenshot...")

    # Fetch the URL
    url = f'https://www.google.com/search?q={ticker}+stock'
    driver.get(url)
    t.sleep(2)
    driver.save_screenshot(f"{ticker}_google_screenshot.png")
    driver.close()
    
    print("Screenshot saved successfully")
    
def main():
    
    # 1. Define the actuator
    executors = {
        "default":ThreadPoolExecutor(max_workers=10)
    }

    # Set up scheduler
    scheduler = BackgroundScheduler(executors=executors)
    scheduler.add_job(getStonkScreenshot, 'interval', seconds=10, args=['GME'])
    scheduler.start()

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            t.sleep(2)

    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown() 

if __name__ == "__main__":
    main()  



