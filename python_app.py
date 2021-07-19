import os
import json
import time as t
import requests
import pandas as pd
import gspread
import gspread_dataframe as gd
from gspread_dataframe import set_with_dataframe
from datetime import date, datetime, timedelta, time
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

# Functions setup

def convertEpochToDate(epoch):
    #timestamp_format = "%Y-%m-%d %H:%m:%S"
    date_format = "%Y-%m-%d"
    created_at_datetime = datetime.datetime.fromtimestamp(epoch)
    created_at_date = created_at_datetime.strftime(date_format)
    return created_at_date

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

    current_time = datetime.now().time()
    market_open_time = datetime(2021, 1, 1, 13, 30, 0).time() #trading hours in UTC
    market_close_time = datetime(2021, 1, 1, 21, 0, 0).time()
    
    weekday = datetime.today().strftime('%A')
    if weekday=='Saturday' or weekday=='Sunday':
        return False
    elif current_time>market_close_time or current_time<market_open_time:
        return False
    else:
        return True


def getStockPrice(ticker):
    '''
    Returns current stock price for this ticker.
    This uses my free trial account with rapidAPI.com, which is limited to 500 free calls per month.
    So we will only check every half hour, and only during trading hours.
    '''
    
    url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/stock/v2/get-summary"

    querystring = {"symbol":ticker,"region":"US"}

    headers = {
            'x-rapidapi-key': os.environ['RAPIDAPI_KEY'],
            'x-rapidapi-host': os.environ['RAPIDAPI_HOST']
        }
    
    response = requests.request("GET", url, headers=headers, params=querystring)
    response_json = json.loads(response.text)
    price = response_json['price']['regularMarketPrice']['fmt']
    print(f"The current price of {ticker} is {price}")
    
    return price

def getStomnkPriceDataframe(ticker):
    '''
    1. Fetches current stock price of ticker using getStockPrice(ticker)
    2. Returns a dataframe containing the result along with current timestamp
    '''

    if checkIfTradingHours():
        price = getStockPrice(ticker)
        output_dict = dict()
        output_dict['Date']=date.today()
        output_dict['Timestamp']=datetime.now(tz=None)    
        output_dict['Ticker']=ticker
        output_dict['Price']=price
        new_data_df = pd.DataFrame(output_dict, index=[0])
    
        return new_data_df

    # If outside of trading hours, do not run! We only get 500 free API calls per month lol. MONEY PLEASE???
    else:
        print("Outside trading hours. Chill")
        return None

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
    

    if not checkIfTradingHours():
        print("We are outside trading hours. Chill")
        return
    
    else:
        # Get df with updated stonk data
        new_data_df = getStomnkPriceDataframe(ticker)

        # We will only add this to the Google Sheet if the price has changed. 
        # Fetch data from the existing sheet and compare our new dataframe with the most recent row in the Gsheet

        # Load the worksheet as a dataframe
        sheet_index = 0
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

            # get worksheet object
            gc = authenticateGoogleSheets()
            sh = gc.open_by_key(worksheet_key)
            worksheet = sh.get_worksheet(sheet_index)

            # update worksheet with updated dataframe
            gd.set_with_dataframe(worksheet, updated_df)

            # Post to Slack, but only during trading hours
            message = createSlackMessage(new_data_df,price_change)
            print(f"Slack message: {message}")
            post_message_to_slack(message, blocks = None)

        # If price has not changed, nothing happens
        else:
            print("Price has not changed - HODL")

        print("All done!")

def updateDailySummaryData():
    '''
    Update the daily summary stats in the google sheet (one row per date + ticker)
    '''
    
    print("Updating daily summary stats in Google Sheets")
    
    # Get data from the Google Sheet
    sheet_index = 0
    price_data_df = loadGoogleSheetAsDF(worksheet_key, sheet_index)
    
    # Calculate daily summary stats for each ticker
    # Max
    max_prices = pd.DataFrame(price_data_df.groupby('Date').max()[['Ticker','Price']])
    max_prices = max_prices.rename(columns={"Price":"Max"}).reset_index()
    
    # Min
    min_prices = pd.DataFrame(price_data_df.groupby('Date').min()[['Ticker','Price']])
    min_prices = min_prices.rename(columns={"Price":"Min"}).reset_index()
    
    # Avg
    avg_prices = pd.DataFrame(price_data_df.groupby(['Date','Ticker']).mean())
    avg_prices = avg_prices.rename(columns={"Price":"Average"}).reset_index()
    
    # Stdev
    stdev_prices = pd.DataFrame(price_data_df.groupby(['Date','Ticker']).std())
    stdev_prices = stdev_prices.rename(columns={"Price":"Stdev"}).reset_index()
    
    # Open & closing prices
    # Get market open and closing prices for each date + ticker
    rownums_ascending = price_data_df.groupby(['Date','Ticker']).cumcount()
    price_data_df['rownum_ascending'] = [x for x in rownums_ascending]
    price_data_df = price_data_df.sort_values(['Date','Ticker','Timestamp'],ascending=False)
    rownums_descending = price_data_df.groupby(['Date','Ticker']).cumcount()
    price_data_df['rownum_descending'] = [x for x in rownums_descending]
    open_prices = price_data_df[price_data_df['rownum_ascending']==0][['Date','Ticker','Price']]
    open_prices = open_prices.rename(columns={"Price":"Opening Price"})
    closing_prices = price_data_df[price_data_df['rownum_descending']==0][['Date','Ticker','Price']]
    closing_prices = closing_prices.rename(columns={"Price":"Closing Price"})
    
    # Calculate prior day stats for each date + ticker
    # Prior Day Max
    prior_day_maxes = max_prices.copy()
    prior_day_maxes['Date'] = [(datetime.strptime(x, '%m/%d/%Y')+timedelta(days=1)).strftime('%-m/%d/%Y') for x in prior_day_maxes['Date']]
    prior_day_maxes = prior_day_maxes.rename(columns={"Max":"Prior Day Max"})
    
    # Prior Day Min
    prior_day_mins = min_prices.copy()
    prior_day_mins['Date'] = [(datetime.strptime(x, '%m/%d/%Y')+timedelta(days=1)).strftime('%-m/%d/%Y') for x in prior_day_mins['Date']]
    prior_day_mins = prior_day_mins.rename(columns={"Min":"Prior Day Min"})
    
    # Prior Day Avg
    prior_day_avgs = avg_prices.copy()
    prior_day_avgs['Date'] = [(datetime.strptime(x, '%m/%d/%Y')+timedelta(days=1)).strftime('%-m/%d/%Y') for x in prior_day_avgs['Date']]
    prior_day_avgs = prior_day_avgs.rename(columns={"Average":"Prior Day Avg"})
    
    # Prior Day Stdev
    prior_day_stds = stdev_prices.copy()
    prior_day_stds['Date'] = [(datetime.strptime(x, '%m/%d/%Y')+timedelta(days=1)).strftime('%-m/%d/%Y') for x in prior_day_stds['Date']]
    prior_day_stds = prior_day_stds.rename(columns={"Stdev":"Prior Day Stdev"})
    
    # Prior Day Open prices
    prior_day_open_prices = open_prices.copy()
    prior_day_open_prices['Date'] = [(datetime.strptime(x, '%m/%d/%Y')+timedelta(days=1)).strftime('%-m/%d/%Y') for x in prior_day_open_prices['Date']]
    prior_day_open_prices = prior_day_open_prices.rename(columns={"Opening Price":"Prior Day Opening Price"})
    
    # Prior Day Closing prices
    prior_day_closing_prices = closing_prices.copy()
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
    print("Daily summary dataframe created. Attempting to update Google Sheets...")
    try:
        summary_sheet_index = 1
        gc = authenticateGoogleSheets()
        sh = gc.open_by_key(worksheet_key)
        daily_summary_worksheet = sh.get_worksheet(summary_sheet_index)
        gd.set_with_dataframe(daily_summary_worksheet, daily_summary_df)
        print("Successfully updated Google Sheets with enfreshened summary stats")
    
    except:
        print("Failed to update Google Sheets :( :( :(")

def updateHistoricalData(ticker):
    '''
    Update Google sheets tab containing historical data for {ticker}
    TODO(): refactor to process a list of tickers instead of just one
    '''
    
    print(f"Updating historical data for {ticker}...")
    url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/stock/v3/get-historical-data"
    
    querystring = {"symbol":ticker,"region":"US"}
    
    headers = {
            'x-rapidapi-key': os.environ['RAPIDAPI_KEY'],
            'x-rapidapi-host': os.environ['RAPIDAPI_HOST']
        }
    
    response = requests.request("GET", url, headers=headers, params=querystring)

    historical_data_json = json.loads(response.text)
    
    # call API to fetch historical data
    historical_data_df = pd.DataFrame(historical_data_json['prices'])
    
    historical_data_df = historical_data_df.rename(columns={"date":"timestamp_epoch"})
    
    historical_data_df['Date'] = [convertEpochToDate(x) for x in historical_data_df['timestamp_epoch']]
    historical_data_df['Ticker'] = ticker
    
    # update the Google Sheets worksheet
    sheet_index=2
    gc = authenticateGoogleSheets()
    sh = gc.open_by_key(worksheet_key)
    historical_data_worksheet = sh.get_worksheet(sheet_index)
    gd.set_with_dataframe(historical_data_worksheet, historical_data_df)
    
    print(f"Historical data for {ticker} updated successfully")

def main():

    scheduler = BackgroundScheduler(executors=executors)
    #scheduler.add_job(updateStonkxData, 'interval', seconds=1800, args=["GME"])
    scheduler.add_job(updateStonkxData, CronTrigger.from_crontab('*/30 * * * *'), args=["GME"])
    scheduler.add_job(updateDailySummaryData, 'interval', seconds=600, args=None)
    scheduler.add_job(updateHistoricalData, 'interval', seconds=60, args=["GME"])
    #scheduler.add_job(updateDailySummaryData, CronTrigger.from_crontab('0 22 * * *'), args=None)
    scheduler.start()

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            t.sleep(2)

    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown() 

if __name__ == "__main__":
    main()  



