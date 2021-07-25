import itertools
import json
import os
import pandas as pd
import tweepy

import moonwatch_utils as moon

# dict for mapping emojis to unicode characters, to make my life easier
# https://unicode.org/emoji/charts/full-emoji-list.html
emoji = {
    "rocket":"\U0001F680", #need to use wide escape for 1F unicode. Don't ask me what THAT means though
    "blush":"\u263A",
    "joy":"\U0001F602"
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

def tweetMessage(message):
    '''    
    input: message content to send in tweet
    output: posts the tweet
    '''
    
    # Authenticate Twitter API
    api = twitterAuthenticate()
    
    # Post tweet
    print("Tweeting!")
    try:
        response = api.update_status(status=message)
        if response.text:
            print("Tweet successful")
        else: 
            print("Something went wrong :()")   
    except:
        print("Tweet failed, it's probably fine, there are better things to worry about")


def tweetMostRecentPrice(ticker):

    # Get most recent price from the google sheet (function in moonwatch_utils module)
    price = moon.getMostRecentPriceFromSheet(ticker)

    # Craft the tweet, filling in emoji unicode from dict (top of this file)
    message = f"""$GME ${price} {emoji['rocket']} #GME #wow #moon #HODL #Apestrong """

    # Send the tweet (if during trading hours)

    if moon.checkIfTradingHours():
        tweetMessage(message)
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

    # Authenticate
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
    
    # Get the set of tweets that have high enough engagement for us to want to retweet
    high_engagement_tweets = [x for x in GME_tweets_list 
                              if x['in_reply_to_status_id'] == None
                              and x['favorite_count']>10
                              and x['retweet_count']>10 
                              and 'retweeted_status' not in x.keys()
                              and x not in my_tweet_ids]
    
    # If there are any recent tweets with high enough engagement, retweet the one with the most "likes"
    if len(high_engagement_tweets)>0:
        # From the resulting dataframe, isolate the tweet id of the most retweeted high-engagement tweet
        top_tweet = pd.DataFrame(high_engagement_tweets).sort_values('retweet_count',ascending=False).reset_index().loc[0:0]
        tweet_id_to_retweet = top_tweet['id'][0]
        try:
            api.retweet(tweet_id_to_retweet)
            print(f"Successfully retweeted a high-engagement tweet (id {tweet_id_to_retweet})")
        except:
            print("Retweet failed") 
    else:
        print("No recent tweets are good enough to retweet. Oh well")

"""
def tweetImage(message,image_url):
    '''    
    input: message content to send in tweet
    output: posts the tweet
    '''
    
    api = twitterAuthenticate()
    
    # Upload image to Twitter
    print(f"uploading {image_url} to Twitterspace")
    image_url
    
    media = api.media_upload(tweet_image_path)
    
    # Post tweet with image
    print("Tweeting!")
    response = api.update_status(status=tweet, media_ids=[media.media_id])
    if response.text:
        print("Tweet successful")
    else: 
        print("Something went wrong :()")   

"""