import json
import os
import requests
import time as t
from base64 import b64encode
from PIL import Image
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.options import Options

def getScreenshot(ticker):
    '''
    Given a specific ticker, opens Google search page and grabs a screenshot
    Returns the filename of the resulting image
    '''

    CHROMEDRIVER_PATH = os.environ.get('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
    GOOGLE_CHROME_BIN = os.environ.get('GOOGLE_CHROME_BIN', '/usr/bin/google-chrome')
    filename = f'{ticker}_screenshot.png'

    options = Options()
    options.binary_location = GOOGLE_CHROME_BIN
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument("--window-size=1920,1080")
    options.headless = True

    driver = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH , chrome_options=options)
    print("WOW the driver works")
    url = f'https://www.google.com/search?q={ticker}+stock'
    driver.get(url)
    print("got the URL. Waiting 2 seconds...")
    t.sleep(2)
    print("OK grabbing a screenshot now")
    driver.save_screenshot(filename)
    print("Closing the webdriver")
    driver.close()

    return filename

def cropImage(filename):
    # Opens a image in RGB mode
    im = Image.open(filename)
    # Setting the points for cropped image
    left = 185
    top = 350
    right = 820
    bottom = 575
    
    # Cropped image of above dimension
    # (It will not change original image)
    im1 = im.crop((left, top, right, bottom))
    
    # Overwrite the file with the new cropped version
    im1 = im1.save(filename)


def uploadFileToImgur(filename):
    '''
    Uploads file to imgur and returns the URL where it has been uploaded
    '''
    
    client_id = os.getenv('IMGUR_CLIENT_ID')
    headers = {"Authorization": f"Client-ID {client_id}"}
    api_key = os.getenv('IMGUR_CLIENT_ID')
    url = "https://api.imgur.com/3/upload.json"
    j1 = requests.post(
        url, 
        headers = headers,
        data = {
            'key': api_key, 
            'image': b64encode(open(f'{filename}', 'rb').read()),
            'type': 'base64',
            'name': filename,
            'title': 'GME stomnks (not financial advice)'
        }
    )
    
    response_json = json.loads(j1.text)
    try:
        url_output = response_json['data']['link']
    except:
        url_output = None

    return url_output

def main():

    ticker = 'GME'

    # Use Selenium to save a screenshot
    print("Using Selenium to fetch a screenshot")
    filename = getScreenshot(ticker)

    # Crop the screenshot to show only the cute trend chart
    print(f"Screenshot saved: {filename}. Cropping image...")
    cropImage(filename)

    # Upload the cropped image to Imgur
    print(f"Image cropped. Uploading {filename} to Imgur...")
    try:
        imgur_url = uploadFileToImgur(filename)
        print(f"Imgur upload success! URL: {imgur_url}")
    except:
        print(f"Imgur upload failed :(")

    # TODO(): message Slack

if __name__ == "__main__":
    main()  