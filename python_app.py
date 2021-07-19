import os
import json
import time
import requests
import pandas as pd
import gspread
import gspread_dataframe as gd
from gspread_dataframe import set_with_dataframe
from datetime import date, datetime, timedelta
from bs4 import BeautifulSoup
from urllib.request import urlopen
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger
    
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

def loadGoogleSheetAsDF(worksheet_key, sheet_index):
    
    # Get data from the worksheet
    gc = authenticateGoogleSheets()
    sh = gc.open_by_key(worksheet_key)
    worksheet = sh.get_worksheet(sheet_index)
    sheet_as_df = gd.get_as_dataframe(worksheet)
    
    return sheet_as_df

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
    
    # Load the worksheet as a dataframe
    sheet_as_df = loadGoogleSheetAsDF(worksheet_key, sheet_index).sort_values(by=['Timestamp'])
    
    # Filter to rows for specific ticker
    sheet_as_df = sheet_as_df[sheet_as_df['Ticker']==ticker]

    # Compare price values in latest row vs. prior row
    previous_price = sheet_as_df.iloc[len(sheet_as_df)-1:len(sheet_as_df)].reset_index()['Price'][0]
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
        message = createSlackMessage(new_data_df,price_change)
        print(f"Slack message: {message}")
        
        if checkIfTradingHours():
            print("Updating Slack!")
            post_message_to_slack(message, blocks = None)

        else:
            print("Outside trading hours. Chill")
    
    # If price has not changed, nothing happens
    else:
        print("Price has not changed - HODL")

    print("All done!")

def updateDailySummaryData():
    
    print("Updating daily summary stats in Google Sheets")
    
    # Get data from the worksheet
    gc = authenticateGoogleSheets()
    sh = gc.open_by_key(worksheet_key)
    worksheet = sh.get_worksheet(sheet_index)
    sheet_as_df = gd.get_as_dataframe(worksheet)
    
    # Calculate daily summary stats for each ticker
    # Max
    max_prices = pd.DataFrame(sheet_as_df.groupby('Date').max()[['Ticker','Price']])
    max_prices = max_prices.rename(columns={"Price":"Max"})
    
    # Min
    min_prices = pd.DataFrame(sheet_as_df.groupby('Date').min()[['Ticker','Price']])
    min_prices = min_prices.rename(columns={"Price":"Min"})
    
    # Avg
    avg_prices = pd.DataFrame(sheet_as_df.groupby(['Date','Ticker']).mean())
    avg_prices = avg_prices.rename(columns={"Price":"Average"})
    
    # Stdev
    stdev_prices = pd.DataFrame(sheet_as_df.groupby(['Date','Ticker']).std())
    stdev_prices = stdev_prices.rename(columns={"Price":"Stdev"})
    
    # Open & closing prices
    # Get market open and closing prices for each date + ticker
    rownums_ascending = sheet_as_df.groupby(['Date','Ticker']).cumcount()
    sheet_as_df['rownum_ascending'] = [x for x in rownums_ascending]
    sheet_as_df = sheet_as_df.sort_values(['Date','Ticker','Timestamp'],ascending=False)
    rownums_descending = sheet_as_df.groupby(['Date','Ticker']).cumcount()
    sheet_as_df['rownum_descending'] = [x for x in rownums_descending]
    open_prices = sheet_as_df[sheet_as_df['rownum_ascending']==0][['Date','Ticker','Price']]
    open_prices = open_prices.rename(columns={"Price":"Opening Price"})
    closing_prices = sheet_as_df[sheet_as_df['rownum_descending']==0][['Date','Ticker','Price']]
    closing_prices = closing_prices.rename(columns={"Price":"Closing Price"})
    
    # Calculate prior day stats for each date + ticker
    # Prior Day Max
    prior_day_maxes = pd.DataFrame(max_prices).reset_index()    
    prior_day_maxes['Date'] = [(datetime.strptime(x, '%m/%d/%Y')+timedelta(days=1)).strftime('%-m/%d/%Y') for x in prior_day_maxes['Date']]
    prior_day_maxes = prior_day_maxes.rename(columns={"Max":"Prior Day Max"})
    
    # Prior Day Min
    prior_day_mins = pd.DataFrame(min_prices).reset_index()    
    prior_day_mins['Date'] = [(datetime.strptime(x, '%m/%d/%Y')+timedelta(days=1)).strftime('%-m/%d/%Y') for x in prior_day_mins['Date']]
    prior_day_mins = prior_day_mins.rename(columns={"Min":"Prior Day Min"})
    
    # Prior Day Avg
    prior_day_avgs = pd.DataFrame(avg_prices).reset_index()    
    prior_day_avgs['Date'] = [(datetime.strptime(x, '%m/%d/%Y')+timedelta(days=1)).strftime('%-m/%d/%Y') for x in prior_day_avgs['Date']]
    prior_day_avgs = prior_day_avgs.rename(columns={"Average":"Prior Day Avg"})
    
    # Prior Day Stdev
    prior_day_stds = pd.DataFrame(stdev_prices).reset_index()    
    prior_day_stds['Date'] = [(datetime.strptime(x, '%m/%d/%Y')+timedelta(days=1)).strftime('%-m/%d/%Y') for x in prior_day_stds['Date']]
    prior_day_stds = prior_day_stds.rename(columns={"Stdev":"Prior Day Stdev"})
    
    # Prior Day Open prices
    prior_day_open_prices = pd.DataFrame(open_prices)
    prior_day_open_prices['Date'] = [(datetime.strptime(x, '%m/%d/%Y')+timedelta(days=1)).strftime('%-m/%d/%Y') for x in prior_day_open_prices['Date']]
    prior_day_open_prices = prior_day_open_prices.rename(columns={"Opening Price":"Prior Day Opening Price"})

    # Prior Day Closing prices
    prior_day_closing_prices = pd.DataFrame(closing_prices)
    prior_day_closing_prices['Date'] = [(datetime.strptime(x, '%m/%d/%Y')+timedelta(days=1)).strftime('%-m/%d/%Y') for x in prior_day_closing_prices['Date']]
    prior_day_closing_prices = prior_day_closing_prices.rename(columns={"Closing Price":"Prior Day Closing Price"})

    # Do a bunch of merges to construct the daily summary dataframe
    daily_summary_df = max_prices.merge(min_prices,how='inner',on=['Date','Ticker'])
    daily_summary_df = daily_summary_df.merge(avg_prices,how='inner',on=['Date','Ticker'])
    daily_summary_df = daily_summary_df.merge(stdev_prices,how='inner',on=['Date','Ticker'])
    daily_summary_df = daily_summary_df.merge(open_prices,how='inner',on=['Date','Ticker'])
    daily_summary_df = daily_summary_df.merge(closing_prices,how='inner',on=['Date','Ticker'])
    daily_summary_df = daily_summary_df.merge(prior_day_maxes,how='inner',on=['Date','Ticker'])
    daily_summary_df = daily_summary_df.merge(prior_day_mins,how='inner',on=['Date','Ticker'])
    daily_summary_df = daily_summary_df.merge(prior_day_avgs,how='inner',on=['Date','Ticker'])
    daily_summary_df = daily_summary_df.merge(prior_day_stds,how='inner',on=['Date','Ticker'])
    daily_summary_df = daily_summary_df.merge(prior_day_open_prices,how='inner',on=['Date','Ticker'])
    daily_summary_df = daily_summary_df.merge(prior_day_closing_prices,how='inner',on=['Date','Ticker'])
    
    # Overwrite daily summary table in Google Sheets with new dataframe
    daily_summary_worksheet = sh.get_worksheet(1)
    gd.set_with_dataframe(daily_summary_worksheet, daily_summary_df)

    print("Successfully updated summary stats in Google Sheets, yay, wow, congrats")

    #TODO(): message helpful summary info to Slack (helpful!!!)

def main():

    scheduler = BackgroundScheduler(executors=executors)
    scheduler.add_job(updateStonkxData, 'interval', seconds=600, args=["GME"])
    scheduler.add_job(updateDailySummaryData, 'interval', seconds=10, args=None)
    #scheduler.add_job(updateDailySummaryData, CronTrigger.from_crontab('0 22 * * *'), args=None)
    scheduler.start()

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(2)

    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown() 

if __name__ == "__main__":
    main()  



