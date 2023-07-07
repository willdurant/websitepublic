from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from energy.usageUpdater import usageApi


def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        usageApi.import_new_energy_data, CronTrigger.from_crontab("0 0 * * 0")
    )
    scheduler.start()
