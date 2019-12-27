from django_cron import CronJobBase, Schedule
from .views import scraper


class ScraperCronJob(CronJobBase):
    RUN_EVERY_MINS = 2  # every 5 mins
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'league.scraper_cron_job'    # a unique code

    def do(self):
        scraper()
