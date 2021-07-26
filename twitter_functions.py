import itertools
import json
import os
import pandas as pd
import tweepy
from datetime import date, datetime, timedelta, time

import moonwatch_utils as moon

# dict for mapping emojis to unicode characters, to make my life easier
# https://unicode.org/emoji/charts/full-emoji-list.html
emoji = {
    "rocket":"\U0001F680", #need to use wide escape for 1F unicode. Don't ask me what THAT means though
    "blush":"\u263A",
    "joy":"\U0001F602",
    "gorilla":"\U0001F98D",
    "banana":"\U0001F34C",
    "gem":"\U0001F48E",
    "raised_hands":"\U0001F64C",
    "huffy":"\U0001F624"
}

def test_function():
    print("yaaaay")

def twitterAuthenticate():
    
    '''
    Returns an API object to do Twittering
    
    Input: none BAYBEE
    Output: returns API object
    '''
    # get twitter auth creds
    CONSUMER_KEY = os.environ["TWITTER_CONSUMER_KEY"]
    CONSUMER_SECRET = os.environ["TWITTER_CONSUMER_SECRET"]
    ACCESS_TOKEN = os.environ["TWITTER_ACCESS_TOKEN"]
    ACCESS_TOKEN_SECRET = os.environ["TWITTER_ACCESS_TOKEN_SECRET"]
    
    # Authenticate to Twitter
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    
    # Create API object
    api = tweepy.API(auth)
    
    return api

def convertTweetResponseToDictList(tweetResponse):
    output_list = []
    for i in range(len(tweetResponse)):
        tweet_object = tweetResponse[i]
        json_str = json.dumps(tweet_object._json)
        tweet_json = json.loads(json_str)
        output_list.append(tweet_json)
    return output_list

def tweetMostRecentPrice(ticker):

    # Authenticate Twitter
    api = twitterAuthenticate()

    # Get most recent price from the google sheet (function in moonwatch_utils module)
    price = moon.getMostRecentPriceFromSheet(ticker)
    emoji_for_tweet = emoji['rocket']

    # Craft the tweet, filling in emoji unicode from dict (top of this file)
    message = f"""$GME ${price} {emoji_for_tweet} #GME #wow #moon #HODL #Apestrong """

    # Send the tweet (if during trading hours)

    if moon.checkIfTradingHours():
        response = api.update_status(status=message)
        if response.text:
            print(f"Successfully tweeted: {message}")
        else: 
            print("Something went wrong :()") 

    else:
        print("We are outside trading hours... dont tweet, it will scare the children")

def retweetMostRecent(screen_name):
    '''
    Retweets most recent tweet by screen_name, provided it has been retweeted at least 200 times
    '''

    api = twitterAuthenticate()
    tweets = api.user_timeline(screen_name=screen_name,
                               count=1,
                               include_rts = False,
                               tweet_mode = 'extended'
                               )
    most_recent_tweet = tweets[0]
    json_str = json.dumps(most_recent_tweet._json)
    tweet_json = json.loads(json_str)

    # Only retweet if there have already been at least 200 retweets
    if tweet_json['retweet_count']<50:
        print("Not enough retweets - BORING.")
        return
    else:
        print("Retweeting!! LFG")
        try:
            tweet_id = tweet_json['id']
            api.retweet(tweet_id)
            print("Retweet successful")
        except:
            print("Retweet failed (probably already retweeted it, dummy)")


def retweetHighEngagementTweet(query):
    '''
    This function runs periodically to look for a high-engagement tweet containing the search query.
    It will retweet the top result that we have not already retweeted.
    '''

    print(f"Executing retweetHighEngagementTweet('{query}')...")

    # Authenticate Twitter
    api = twitterAuthenticate()

    # Get list of all my tweets
    tweets = api.user_timeline(screen_name='MoonWatch_',count=1000,include_rts = True,tweet_mode = 'compat')
    my_tweet_list = convertTweetResponseToDictList(tweets)
    my_tweet_ids = [x['id'] for x in my_tweet_list]
    
    # Get recent tweets with hashtag #GME
    GME_tweets_list = []
    for page in tweepy.Cursor(api.search, q=query, count=1).pages():
        tweets_in_this_page = convertTweetResponseToDictList(page)
        GME_tweets_list.append(tweets_in_this_page)
        
    GME_tweets_list = list(itertools.chain.from_iterable(GME_tweets_list))     
    
    # Use stricter limits for retweeting during business hours
    if moon.checkIfTradingHours():
        minimum_engagement = 100
    else:
        minimum_engagement = 10        

    # Get the set of tweets that have high enough engagement for us to want to retweet
    high_engagement_tweets = [x for x in GME_tweets_list 
                              if x['in_reply_to_status_id'] == None
                              and x['favorite_count'] > minimum_engagement
                              and x['retweet_count'] > minimum_engagement 
                              and 'retweeted_status' not in x.keys()
                              and x not in my_tweet_ids]
    
    # If there are any recent tweets with high enough engagement, retweet the one with the most "likes"
    if len(high_engagement_tweets)>0:
        # From the resulting dataframe, isolate the tweet id of the most retweeted high-engagement tweet
        top_tweet = pd.DataFrame(high_engagement_tweets).sort_values('retweet_count',ascending=False).reset_index().loc[0:0]
        tweet_id_to_retweet = top_tweet['id'][0]

        user_id = my_tweet_list[0]['user']['id']

        try:
            api.retweet(tweet_id_to_retweet)
            print(f"Successfully retweeted a high-engagement tweet (id {tweet_id_to_retweet})")
            try: #Follow the account that posted the tweet we are retweeting
                api.create_friendship(user_id)
                print(f"Successfully followed user {user_id}")
            except:
                print("Follow failed (probably already following this account)")
        except:
            print("Retweet failed") 
    else:
        print("No recent tweets are good enough to retweet. Oh well")



def tweetTrendImage(ticker):

    # Authenticate Twitter
    api = twitterAuthenticate()

    if moon.checkIfTradingHours():
        # Use Selenium to save a screenshot
        print("Using Selenium to fetch a screenshot")
        filename = moon.getScreenshot(ticker)

        # Crop the screenshot to show only the cute trend chart
        print(f"Screenshot saved: {filename}. Cropping image and uploading to Twitter...")
        moon.cropImage(filename)
        try:
            media = api.media_upload(filename)
            tweet = f"Your regularly scheduled update {emoji['rocket']}"
            response = api.update_status(status=tweet, media_ids=[media.media_id])
            print("Trend image tweeted successfully")
        except: 
            print("Trend image failed to tweet :(")
    else:
        print("We are outside trading hours - chill")



def tweetEODSummary(ticker):
    '''
    For a given ticker, tweet a summary of the day's trading stats
    This will be scheduled to run at the end of every trading day
    '''

    # Authenticate Twitter
    api = twitterAuthenticate()
    
    # Load the worksheet as a dataframe
    worksheet_key = os.getenv("MOONWATCH_WORKSHEET_KEY")
    sheet_index = int(os.environ['HISTORICAL_DATA_SHEET_INDEX'])
    summary_df = moon.loadGoogleSheetAsDF(worksheet_key, sheet_index)
        
    # Filter summary to selected ticker & today's date
    today = str(date.today())
    today_summary = summary_df[(summary_df['Date']==today) & (summary_df['Ticker']==ticker)].reset_index() #reset index so that [0] always works
    
    # Extract metrics from the summary table
    trading_open = round(today_summary['open'][0],2)
    trading_close = round(today_summary['close'][0],2)
    trading_volume = today_summary['volume'][0]
    trading_volume_rank = today_summary['volume_rank'][0]
    
    trading_intraday_delta = today_summary['Intraday Price Change (Dollars)'][0]
    trading_intraday_delta_pct = today_summary['Intraday Price Change (Percentage)'][0]
    trading_intraday_delta_pct = str(round(trading_intraday_delta_pct*100,1))+"%"
    trading_close_vs_prior_day_pct = today_summary['Closing Price Delta from Prior Day (Percentage)'][0]
    trading_close_vs_prior_day_pct = str(round(trading_close_vs_prior_day_pct*100,1))+"%"
    
    if trading_intraday_delta>0:
        trading_intraday_delta_direction='Up'
    else:
        trading_intraday_delta_direction='Down'
        
    # Craft a beautiful and helpful Slack message
    EOD_summary_message = f'''
    Hello apes! What a day it has been!!!
    
    Today ({today}), $GME opened at ${trading_open} and closed at ${trading_close} ({trading_intraday_delta_direction} {trading_intraday_delta_pct} from open)

    Today's trading volume: {trading_volume} (rank #{trading_volume_rank} across the past year of trading)
    
    Don't forget to #HODL! #GME #MOASS #Apestrong
    '''
    
    # Tweet the EOD summary    
    if moon.checkIfTradingHours():
        response = api.update_status(status=EOD_summary_message)
        if response.text:
            print(f"Successfully tweeted EOD summary")
        else: 
            print("Something went wrong, EOD summary failed to tweet :()") 
    else:
        print("No EOD summary on non-trading days!") 
        return