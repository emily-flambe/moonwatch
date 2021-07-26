'''
Functions used for Moonwatch Slack app 
(Does not include functions for using Twitter API)
'''

import os
import json
import time as t
import requests
import pandas as pd
import gspread
import gspread_dataframe as gd
from base64 import b64encode
from datetime import date, datetime, timedelta, time
from gspread_dataframe import set_with_dataframe
from PIL import Image
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.options import Options

"""
------------------------------------
VARIABLES AND STUFF
------------------------------------
"""
KEYFILE = 'service_account_creds.json'
service_account_creds = os.getenv("SERVICE_ACCOUNT_CREDS")
worksheet_key = os.getenv("MOONWATCH_WORKSHEET_KEY")


"""
------------------------------------
GENERAL UTILITIES
------------------------------------
"""
def convertEpochToDate(epoch):
    #timestamp_format = "%Y-%m-%d %H:%m:%S"
    date_format = "%Y-%m-%d"
    created_at_datetime = datetime.fromtimestamp(epoch)
    created_at_date = created_at_datetime.strftime(date_format)
    return created_at_date

def checkIfTradingHours():
    '''
    Returns a boolean indicating whether current time is within normal stonk trading hours.
    Not currently being used anywhere but could be useful in the future, so keeping for now
    '''

    current_time = datetime.now().time()
    market_open_time = datetime(2021, 1, 1, 13, 30, 0).time() #trading hours in UTC
    market_close_time = datetime(2021, 1, 1, 20, 2, 0).time()
    
    weekday = datetime.today().strftime('%A')
    if weekday=='Saturday' or weekday=='Sunday':
        return False
    elif current_time>market_close_time or current_time<market_open_time:
        return False
    else:
        return True

"""
------------------------------------
SLACK API
------------------------------------
"""
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

"""
------------------------------------
GOOGLE SHEETS API
------------------------------------
"""
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

def getMostRecentPriceFromSheet(ticker):

    # Get prices dataframe
    # Load the worksheet as a dataframe
    sheet_index = int(os.environ['ALL_PRICES_SHEET_INDEX'])
    all_prices_df = loadGoogleSheetAsDF(worksheet_key, sheet_index).sort_values(by=['Timestamp'])
    all_prices_df = all_prices_df[all_prices_df['Ticker']==ticker]
    most_recent_price_df = all_prices_df.sort_values('Timestamp',ascending=False).reset_index().loc[0:0][['Timestamp','Price']]
    most_recent_price = most_recent_price_df['Price'][0]
    return most_recent_price

"""
------------------------------------
YAHOO! FINANCE API
------------------------------------
"""
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
    price = new_data_df['Price'][0]

    if price_change>0.05:
        message = f":gorilla::rocket::waning_crescent_moon::last_quarter_moon::waning_gibbous_moon::full_moon: ${price}"
    elif price_change>0.01:
        message = f":biden_point::rocket: ${price}"        
    elif price_change>0.005:
        message = f":rocket: ${price}"
    elif price_change>0:
        message = f":banana: ${price}"
    elif price_change<-.01:
        message = f":porg::sweat_drops: ${price}"
    elif price_change<-.005:
        message = f":porg: ${price}"
    else:
        message = f":gorilla: ${price}"

    return message   

def updateStonkxData(ticker):
    '''
    Fetch realtime stock price and post a message in Slack.
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
        sheet_index = int(os.environ['ALL_PRICES_SHEET_INDEX'])
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

def updateHistoricalData(ticker):
    '''
    Update Google sheets tab containing historical data for {ticker}
    TODO(): refactor to process a list of tickers instead of just one
    '''
    
    print(f"Updating historical data for {ticker}...")


    # call API to fetch historical data
    url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/stock/v3/get-historical-data"
    querystring = {"symbol":ticker,"region":"US"}
    headers = {
            'x-rapidapi-key': os.environ['RAPIDAPI_KEY'],
            'x-rapidapi-host': os.environ['RAPIDAPI_HOST']
        }
    response = requests.request("GET", url, headers=headers, params=querystring)
    historical_data_json = json.loads(response.text)
    
    # load response data into a dataframe
    historical_data_df = pd.DataFrame(historical_data_json['prices'])
    historical_data_df = historical_data_df.rename(columns={"date":"timestamp_epoch"})
    historical_data_df['Date'] = [convertEpochToDate(x) for x in historical_data_df['timestamp_epoch']]
    historical_data_df = historical_data_df.drop(['timestamp_epoch'],axis=1)
    historical_data_df['Ticker'] = ticker

    # Add rownums partitioned by ticker. We will use these to get prior day stats
    rownum = historical_data_df.groupby(['Ticker']).cumcount()
    historical_data_df['rownum'] = [x for x in rownum]

    # Create "prior day" dataframe with rownums incremented by 1
    historical_data_df_prior_day = historical_data_df.copy()
    historical_data_df_prior_day = historical_data_df_prior_day.drop(['Date'],axis=1)
    historical_data_df_prior_day.columns = [x+' prior day' for x in historical_data_df_prior_day.columns]
    historical_data_df_prior_day = historical_data_df_prior_day.rename(columns={'Ticker prior day':'Ticker'})
    historical_data_df_prior_day = historical_data_df_prior_day.rename(columns={'rownum prior day':'rownum'})
    historical_data_df_prior_day['rownum']=[x-1 for x in historical_data_df_prior_day['rownum']]
    historical_data_df = historical_data_df.merge(historical_data_df_prior_day,how='inner',on=['Ticker','rownum'])
    historical_data_df = historical_data_df[['Date'
                                            ,'Ticker'
                                            ,'open'
                                            ,'high'
                                            ,'low'
                                            ,'close'
                                            ,'volume'
                                            ,'adjclose'
                                            ,'open prior day'
                                            ,'high prior day'
                                            ,'low prior day'
                                            ,'close prior day'
                                            ,'volume prior day'
                                            ,'adjclose prior day'
                                           ]]

    # Add a few more calculated fields
    historical_data_df['Intraday Price Change (Dollars)'] = historical_data_df['close'] - historical_data_df['open']
    historical_data_df['Intraday Price Change (Percentage)'] = [(historical_data_df['close'][i]/historical_data_df['open'][i])-1 for i in range(len(historical_data_df['close']))] 
    historical_data_df['Closing Price Delta from Prior Day (Dollars)'] = historical_data_df['close'] - historical_data_df['close prior day']
    historical_data_df['Closing Price Delta from Prior Day (Percentage)'] = [(historical_data_df['close'][i]/historical_data_df['close prior day'][i])-1 for i in range(len(historical_data_df['close']))] 

    # update the Google Sheets worksheet
    sheet_index = int(os.environ['HISTORICAL_DATA_SHEET_INDEX'])
    gc = authenticateGoogleSheets()
    sh = gc.open_by_key(worksheet_key)
    historical_data_worksheet = sh.get_worksheet(sheet_index)
    gd.set_with_dataframe(historical_data_worksheet, historical_data_df)
    
    print(f"Historical data for {ticker} updated successfully")

"""
------------------------------------------------------------------------
SELENIUM
------------------------------------------------------------------------
"""
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

"""
------------------------------------------------------------------------
PYTHON IMAGE LIBRARY
------------------------------------------------------------------------
"""
def cropImage(filename):
    # Opens a image in RGB mode
    im = Image.open(filename)
    # Setting the points for cropped image
    left = 185
    top = 350
    right = 830
    bottom = 690
    
    # Cropped image of above dimension
    # (It will not change original image)
    im1 = im.crop((left, top, right, bottom))
    
    # Overwrite the file with the new cropped version
    im1 = im1.save(filename)

"""
------------------------------------------------------------------------
IMGUR API
------------------------------------------------------------------------
"""
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


"""
------------------------------------------------------------------------
CRAFTING BEAUTIFUL MESSAGES TO DELIVER IN SLACK
------------------------------------------------------------------------
"""
def postEODStatusUpdate(ticker):
    '''
    For a given ticker, post a status update to #gme_moonwatch summarizing the day's trading stats
    This will be scheduled to run at the end of every trading day
    '''
    
    # Load the worksheet as a dataframe

    sheet_index = int(os.environ['HISTORICAL_DATA_SHEET_INDEX'])
    summary_df = loadGoogleSheetAsDF(worksheet_key, sheet_index)
        
    # Filter summary to selected ticker & today's date
    today = str(date.today())
    today_summary = summary_df[(summary_df['Date']==today) & (summary_df['Ticker']==ticker)]
    
    # Extract metrics from the summary table
    trading_open = round(today_summary['open'][0],2)
    trading_close = round(today_summary['close'][0],2)
    trading_high = round(today_summary['high'][0],2)
    trading_low = round(today_summary['low'][0],2)
    trading_volume = today_summary['volume'][0]
    
    trading_intraday_delta = today_summary['Intraday Price Change (Dollars)'][0]
    trading_intraday_delta_pct = today_summary['Intraday Price Change (Percentage)'][0]
    trading_intraday_delta_pct = str(round(trading_intraday_delta_pct*100,1))+"%"
    trading_close_vs_prior_day = today_summary['Closing Price Delta from Prior Day (Dollars)'][0]
    trading_close_vs_prior_day_pct = today_summary['Closing Price Delta from Prior Day (Percentage)'][0]
    trading_close_vs_prior_day_pct = str(round(trading_close_vs_prior_day_pct*100,1))+"%"
    
    if trading_intraday_delta>0:
        trading_intraday_delta_direction='Up'
    else:
        trading_intraday_delta_direction='Down'
        
    if trading_close_vs_prior_day>0:
        trading_close_vs_prior_day_direction='Up'
    else:
        trading_close_vs_prior_day_direction='Down'    
        
    # Craft a beautiful and helpful Slack message
    EOD_summary_message = f'''
    Hello apes! What a day it has been! Here is your summary of our progress towards the :rocket: moon :rocket: today.
    
    Open: ${trading_open}
    Close: ${trading_close} ({trading_intraday_delta_direction} {trading_intraday_delta_pct} from open; {trading_close_vs_prior_day_direction} {trading_close_vs_prior_day_pct} from prior close)
    Today's high: ${trading_high} :rocket:
    Today's low: ${trading_low} :porg::sweat_drops:
    Today's trading volume: {trading_volume} (is that a lot? :thinkintense:)
    
    *The following is not financial advice, I just love the stock:*
    
    Outlook: Bullish
    Recommendation: HODL
    '''
    
    # Update slack!    

    if checkIfTradingHours():
        print("Sending EOD summary message to Slack")
        post_message_to_slack(EOD_summary_message, blocks = None)
    else:
        return

def postGoodMorningMessage():
    '''
    Just a friendly greeting to start the trading day
    '''
    
    greeting_message = f'''
    :city_sunrise: Good morning apes! Let's buckle up and make today the best day it can be!
        
    :gem:
    :gem: :gem:
    :gem: :gem: :gem:
    :gem: :gem: :gem: :gem: :rocket: :banana: :gorilla:
    :gem: :gem: :gem:
    :gem: :gem:
    :gem:
    '''
    
    # Update slack!    
    if checkIfTradingHours():
        print("Sending good morning message to Slack")
        post_message_to_slack(greeting_message, blocks = None)
    else:
        return


def postTrendImage(ticker):

    if checkIfTradingHours():
        # Use Selenium to save a screenshot
        print("Using Selenium to fetch a screenshot")
        filename = getScreenshot(ticker)

        # Crop the screenshot to show only the cute trend chart
        print(f"Screenshot saved: {filename}. Cropping image and uploading to Imgur...")
        cropImage(filename)
        try:
            imgur_url = uploadFileToImgur(filename)
            print(f"Imgur upload success! URL: {imgur_url}. Posting to slack babyyy")
            image_message = f"<{imgur_url}|.>"
            post_message_to_slack(image_message, blocks = None)
        except:
            print(f"Imgur upload failed :(")
    else:
        print("We are outside trading hours - chill")