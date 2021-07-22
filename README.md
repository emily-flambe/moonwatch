# MoonWatch
_Everyone asks "wen moon" - nobody asks "how moon"_
 
This is a Python app deployed on Heroku that powers a Slack App called "MoonWatch." Currently this is just a silly app for personal use in the Slack team I use to talk to my friends, but who knows what the future will bring?

As silly as it is, this app does use a handful of handy parlor tricks:

- **Selenium**, to grab screenshots of stock price trendlines from Google
- **Imgur API**, to upload those screenshots to the great big internet
- **Yahoo! Finance API**, which fetches the realtime price of a stock (via RapidAPI, which gives us 500 free API calls per month, so can't go coo coo crazy here)
- **Google Sheets**, which stores the realtime prices as they are fetched and also refreshes a tab with a year of price history
- **Slack API**, to send messages to the Slack channel dedicated for use with this app


## Things this app currently does (as of 7/22/21):

- Price updates (with uplifting and emotionally informative emojis) every half hour during trading hours
- Trend chart update at midday and end of trading
- End of trading recap
- A friendly good morning message to start the day right, just like Wheaties(TMTMTM)
