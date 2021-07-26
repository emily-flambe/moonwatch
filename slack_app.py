import moonwatch_utils as moon
import time as t
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger

executors = {
    "default":ThreadPoolExecutor(max_workers=10)
}

def main():

    # Uncomment to run tasks manually on re-deploy (aka testing in prod lol)
    #postEODStatusUpdate('GME')
    #updateHistoricalData('GME')
    #postTrendImage('GME')
    moon.postGoodMorningMessage()
    moon.updateStonkxData('GME')

    # Set up scheduler tasks
    scheduler = BackgroundScheduler(executors=executors)
    # Price update with uplifting emoji every half hour during trading hours
    scheduler.add_job(moon.updateStonkxData, CronTrigger.from_crontab('*/30 * * * *'), args=["GME"])
    # Update historical data & provide EOD summary after market close
    scheduler.add_job(moon.updateHistoricalData, CronTrigger.from_crontab('2 20 * * *'), args=["GME"])
    scheduler.add_job(moon.postEODStatusUpdate, CronTrigger.from_crontab('5 20 * * *'), args=["GME"])
    # Post full trend and metrics at midday and market close
    scheduler.add_job(moon.postTrendImage, CronTrigger.from_crontab('0 17 * * *'), args=["GME"]) 
    scheduler.add_job(moon.postTrendImage, CronTrigger.from_crontab('5 20 * * *'), args=["GME"]) 
    # GOOD MUORNEEENG!!!
    scheduler.add_job(moon.postGoodMorningMessage, CronTrigger.from_crontab('25 13 * * *'), args=None)

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



