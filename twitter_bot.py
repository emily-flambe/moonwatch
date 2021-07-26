import twitter_functions as tw
import time as t
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger


# 1. Define the actuator
executors = {
    "default":ThreadPoolExecutor(max_workers=10)
}

# Functions setup

def main():

    tw.tweetTrendImage('GME')

    # Set up scheduler tasks
    scheduler = BackgroundScheduler(executors=executors)
    
    # Tweet price updates every half hour (trading hours only)
    scheduler.add_job(tw.tweetMostRecentPrice, CronTrigger.from_crontab('1 * * * *'), args=['GME'])
    scheduler.add_job(tw.tweetMostRecentPrice, CronTrigger.from_crontab('31 * * * *'), args=['GME'])

    # Post full trend and metrics at midday and market close
    scheduler.add_job(tw.tweetTrendImage, CronTrigger.from_crontab('0 17 * * *'), args=["GME"]) 
    scheduler.add_job(tw.tweetTrendImage, CronTrigger.from_crontab('5 20 * * *'), args=["GME"]) 

    # Scan for high-engagement tweets every 15 minutes
    scheduler.add_job(tw.retweetHighEngagementTweet, CronTrigger.from_crontab('5 * * * *'), args=['#GME'])
    scheduler.add_job(tw.retweetHighEngagementTweet, CronTrigger.from_crontab('20 * * * *'), args=['#MOASS'])
    scheduler.add_job(tw.retweetHighEngagementTweet, CronTrigger.from_crontab('35 * * * *'), args=['#gme'])
    scheduler.add_job(tw.retweetHighEngagementTweet, CronTrigger.from_crontab('50 * * * *'), args=['#moass'])

    # Let 'er rip
    scheduler.start()

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            t.sleep(2)

    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown() 

if __name__ == "__main__":
    main()  



