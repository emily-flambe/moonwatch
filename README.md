# MoonWatch
_Everyone asks "wen moon" - nobody asks "how moon"_

MoonWatch is a multi-headed beast that empowers Gameshop shareholders to track our progress towards the [Mother of All Short Squeezes](https://moass.info/). It really only has two heads, one of which is a Slack app and the other a Twitter bot ([@MoonWatch_](https://twitter.com/MoonWatch_)).

Both the Slack app and the Twitter bot are Python apps deployed on Heroku. Turns out you get a lot more free credits if you give them your credit card info! What's the worst that could happen?

## Twitter Bot
### **twitter_bot.py**, which powers [@MoonWatch_](https://twitter.com/MoonWatch_)

- Updates with price every half hour during trading hours

TODO() (fantasies):
- Pretty much everything else the Slack app does (see below)
- Retweet tweets from VIPs (e.g., Gamestop CEO Ryan Cohen) once they have reached a certain level of engagement (e.g., # of retweets), with some daily limit (maybe 5 per day? Don't want to scare the children)

## Slack App 
### **slack_app.py**

Currently this is just a silly app for personal use in the Slack team I use to talk to my friends, but who knows what the future will bring?

As silly as it is, this app does employ a handful of handy parlor tricks:

- **Selenium**, to grab screenshots of stock price trendlines from Google
- **Imgur API**, to upload those screenshots to the great big internet
- **Yahoo! Finance API**, which fetches the realtime price of a stock (via RapidAPI, which gives us 500 free API calls per month, so can't go coo coo crazy here)
- **Google Sheets API**, which stores the realtime prices as they are fetched and also refreshes a tab with a year of price history
- **Slack API**, to send messages to the Slack channel dedicated for use with this app


## Things this app currently does (as of 7/22/21):

- Price updates (with uplifting and emotionally informative emojis) every half hour during trading hours
- Trend chart update at midday and end of trading
- End of trading recap
- A friendly good morning message to start the day right, just like Wheaties(TMTMTM)
