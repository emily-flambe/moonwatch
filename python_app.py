import os
import json
import time
import bs4
import requests
import logging
from bs4 import BeautifulSoup
from urllib.request import urlopen
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
    
# 1. Define the actuator
executors = {
    "default":ThreadPoolExecutor(max_workers=10)
}

# Functions setup
def post_message_to_slack(text, blocks = None):
    
    slack_token = os.getenv('SLACK_TOKEN')
    slack_channel = '#gme_moonwatch'
    slack_icon_emoji = ':see_no_evil:'
    slack_user_name = 'moonwatch'

    return requests.post('https://slack.com/api/chat.postMessage', {
        'token': slack_token,
        'channel': slack_channel,
        'text': text,
        'icon_emoji': slack_icon_emoji,
        'username': slack_user_name,
        'blocks': json.dumps(blocks) if blocks else None
    }).json()    

def printStomnkPrice(ticker):
    
    # Get current price of stomnk
    url = f'https://finance.yahoo.com/quote/{ticker}?p={ticker}&.tsrc=fin-srch'
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    price = soup.find('div',{'class': 'My(6px) Pos(r) smartphone_Mt(6px)'}).find('span').text
    
    # Craft a very helpful message
    message = f''':gorilla: ${price} :rocket:'''        
    
    print(message)
    post_message_to_slack(message, blocks = None)


def main():

    scheduler = BackgroundScheduler(executors=executors)
    scheduler.add_job(printStomnkPrice, 'interval', seconds=15, args=["GME"])
    scheduler.start()

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(2)

    except (KeyboardInterrupt, SystemExit):
        # Not strictly necessary if daemonic mode is enabled but should be done if possible
        scheduler.shutdown() 

if __name__ == "__main__":
    main()  



