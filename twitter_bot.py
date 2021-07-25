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

    # Uncomment to run tasks manually on re-deploy (aka testing in prod lol)
    # tw.tweetMostRecentPrice('GME')
    # tw.retweetMostRecent('ryancohen')
    tw.retweetHighEngagementTweet('#GME')

    # Set up scheduler tasks
    scheduler = BackgroundScheduler(executors=executors)
    scheduler.add_job(tw.tweetMostRecentPrice, CronTrigger.from_crontab('*/30+1 * * * *'), args=['GME'])
    scheduler.add_job(tw.retweetMostRecent, 'interval', seconds=300, args=['ryancohen'])
    scheduler.add_job(tw.retweetHighEngagementTweet, CronTrigger.from_crontab('*/30+15 * * * *'), args=['#GME'])


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



