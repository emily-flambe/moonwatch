import os
import json
import time
import requests
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

KEYFILE = 'service_account_creds.json'
service_account_creds = os.getenv("SERVICE_ACCOUNT_CREDS")
worksheet_key = os.getenv("MOONWATCH_WORKSHEET_KEY")
sheet_index = 0

# Functions setup

def authenticateGoogleSheets():
    '''
    Authenticates GCP Service account using credentials JSON stored in environment variable
    Returns gc object
    '''

     # Authenticate Google service account to access Google Sheets
    try:
        with open(KEYFILE, "w") as secret_file:
            secret_file.write(service_account_creds)
        gc = gspread.service_account(filename=KEYFILE)
        print("Authentication succeeded, yaaay")
        os.remove(KEYFILE)

    except:
        print("Google Sheets authentication failed :( :( :(")

    return gc

def checkIfTradingHours():
    '''
    Returns a boolean indicating whether current time is within normal stonk trading hours.
    Not currently being used anywhere but could be useful in the future, so keeping for now
    '''

    current_time = datetime.now()
    weekday = datetime.today().strftime('%A')
    
    if weekday=='Saturday' or weekday=='Sunday':
        return False
    elif current_time>time(16,0) or current_time<time(8,30):
        return False
    else:
        return True

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

def createSlackMessage(new_data_df,price_change):
    timestamp = new_data_df['Timestamp'][0]
    ticker = new_data_df['Ticker'][0]
    price = new_data_df['Price'][0]

    if price_change>0.005:
        message = f":rocket::rocket::rocket: ${price} :rocket::rocket::rocket:"
    elif price_change>0:
        message = f":rocket: ${price}"
    elif price_change<-.005:
        message = f":raised_hands::gem::raised_hands::gem: ${price} :raised_hands::gem::raised_hands::gem:"
    else:
        message = f":gorilla: ${price}"

    return message   

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
  
def updateStonkxData(ticker):
    '''
    This is the main code that runs every 10 minutes.
    1) Scrape current stock price from Yahoo! finance
    2) Check to see whether it's changed from the last scrape
    3a) If price has changed, write a new row to the Google Sheet and send a message to Slack
    3b) If price is same, do nothing
    '''
    
    # Get df with updated stonk data
    new_data_df = getStomnkPriceDataframe(ticker)
    
    # We will only add this to the Google Sheet if the price has changed. 
    # Fetch data from the existing sheet and compare our new dataframe with the most recent row in the Gsheet
    
    # Authenticate
    gc = authenticateGoogleSheets()
    
    # Load the worksheet as a dataframe
    sh = gc.open_by_key(worksheet_key)
    worksheet = sh.get_worksheet(sheet_index)
    sheet_as_df = gd.get_as_dataframe(worksheet).sort_values(by=['Timestamp'])
    
    # Filter to rows for specific ticker
    sheet_as_df = sheet_as_df[sheet_as_df['Ticker']==ticker]

    # Compare price values in latest row vs. prior row
    previous_price = sheet_as_df.iloc[len(sheet_as_df)-2:len(sheet_as_df)-1].reset_index()['Price'][0]
    previous_price = float(previous_price)
    new_price = new_data_df['Price'][0]
    new_price = float(new_price)
    price_change = new_price/previous_price-1

    print(f"new price: {new_price}. Old price: {previous_price}. Price change: {price_change}")
    print(f"Has the price changed? {new_price!=previous_price}")

    # If price has changed, append the new number to the Google Sheet
    if float(new_price)!=previous_price:
        print("Adding new data to spreadsheet")
        updated_df = sheet_as_df.append(new_data_df)
        gd.set_with_dataframe(worksheet, updated_df)
        

        # Post to Slack, but only during trading hours
        if checkIfTradingHours():
            print("Updating Slack!")
            message = createSlackMessage(new_data_df,price_change)
            post_message_to_slack(message, blocks = None)

        else:
            print("Outside trading hours. Chill")
    
    # If price has not changed, nothing happens
    else:
        print("Price has not changed - HODL")

    print("All done!")

def main():

    scheduler = BackgroundScheduler(executors=executors)
    scheduler.add_job(updateStonkxData, 'interval', seconds=600, args=["GME"])
    scheduler.start()

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(2)

    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown() 

if __name__ == "__main__":
    main()  



