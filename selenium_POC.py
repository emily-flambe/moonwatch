import json
import os
import requests
import time as t
from base64 import b64encode
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.options import Options

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
    CHROMEDRIVER_PATH = os.environ.get('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
    GOOGLE_CHROME_BIN = os.environ.get('GOOGLE_CHROME_BIN', '/usr/bin/google-chrome')
    filename = 'GME_google_screenshot.png'

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
    driver.save_screenshot(filename)
    print("Closing the webdriver")
    driver.close()
    print(f"Uploading {filename} to Imgur?")
    try:
        imgur_url = uploadFileToImgur(filename)
        print(f"Imgur upload success! URL: {imgur_url}")
    except:
        print(f"Imgur upload failed :(")

if __name__ == "__main__":
    main()  