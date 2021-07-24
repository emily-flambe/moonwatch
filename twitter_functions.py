import os
import tweepy

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