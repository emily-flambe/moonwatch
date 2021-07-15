from flask import Flask

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

app = Flask(__name__)
    
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
    message = f'''Hello APES. (Ook ook) The current price of {ticker} is ${price}... HODL'''        
    
    app.logger.info(message)
    post_message_to_slack(message, blocks = None)


@app.route('/')
def welcome():
    
    return 'Why would I sell?', 200
    
    
@app.route("/scheduler")
def scheduler():
    
    # 2. Create a scheduler
    scheduler = BackgroundScheduler(executors=executors)
    scheduler.add_job(printStomnkPrice, 'interval', hours=1, args=["GME"])
    scheduler.start()
    
    return 'Scheduled some shit.', 200

if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=12345, debug=True)
    app.run()

