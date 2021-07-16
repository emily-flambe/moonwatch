import os
import json
import time
import bs4
import requests
import logging
import pandas as pd
import gspread
import gspread_dataframe as gd
from gspread_dataframe import set_with_dataframe
from datetime import date,datetime
from bs4 import BeautifulSoup
from urllib.request import urlopen
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
    
# 1. Define the actuator
executors = {
    "default":ThreadPoolExecutor(max_workers=10)
}

# Functions setup
def getStomnkPriceDataframe(ticker):
    
    # Get current price of stomnk
    url = f'https://finance.yahoo.com/quote/{ticker}?p={ticker}&.tsrc=fin-srch'
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    price = soup.find('div',{'class': 'My(6px) Pos(r) smartphone_Mt(6px)'}).find('span').text
    
    output_dict = dict()
    output_dict['Date']=date.today()
    output_dict['Timestamp']=datetime.now(tz=None)    
    output_dict['Ticker']=ticker
    output_dict['Price']=price
    
    new_data_df = pd.DataFrame(output_dict, index=[0])
    
    return new_data_df

def createSlackMessage(new_data_df):
    timestamp = new_data_df['Timestamp'][0]
    ticker = new_data_df['Ticker'][0]
    price = new_data_df['Price'][0]
    message = f":rocket: ${price} :gorilla: "
    return message   

def googleSheetAppendDataframe(new_data_df):
    '''
    Returns Google Sheets `worksheet` object
    '''

    KEYFILE = 'service_account_creds.json'
    service_account_creds = os.getenv("SERVICE_ACCOUNT_CREDS")
    worksheet_key = os.getenv("MOONWATCH_WORKSHEET_KEY")
    sheet_index = 0
    
    # Authenticate
    try:
        with open(KEYFILE, "w") as secret_file:
            secret_file.write(service_account_creds)
        gc = gspread.service_account(filename=KEYFILE)
        print("Authentication succeeded, yaaay")
        #os.remove(KEYFILE)

    except:
        print("Google Sheets authentication failed :( :( :(")
        
    # Open the worksheet
    sh = gc.open_by_key(worksheet_key)
    worksheet = sh.get_worksheet(sheet_index)
    
    # Append new data to the Google Sheet
    existing = gd.get_as_dataframe(worksheet)
    updated = existing.append(new_data_df)
    gd.set_with_dataframe(worksheet, updated)
    
    print("Google Sheet updated! In theory, anyway")


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

def getStomnkUpdate(ticker):
    
    # Get fresh data for the ticker
    new_data_df = getStomnkPriceDataframe(ticker)
    
    # Append data to the Google Sheet
    googleSheetAppendDataframe(new_data_df)
    
    # Craft a very helpful message
    message = createSlackMessage(new_data_df)
    
    # Post it to Slack
    post_message_to_slack(message, blocks = None)
    
    print("All done")


def main():

    scheduler = BackgroundScheduler(executors=executors)
    scheduler.add_job(getStomnkUpdate, 'interval', seconds=600, args=["GME"])
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



