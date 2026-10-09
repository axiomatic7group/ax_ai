from apscheduler.executors.pool import ThreadPoolExecutor
from django.core.management.base import BaseCommand, CommandError
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler


from django.conf import settings
from django.utils import timezone

import sys
from pm.models import *
from pm.mechanisms import apscheduler_functions
import pandas as pd

def heartbeat_task():
    print("Checking DB for new jobs..."+ timezone.now().strftime("%Y-%m-%d %H:%M:%S"))



class Command(BaseCommand):
    def handle(self, *args, **options):
        db_conf = settings.DATABASES['default']
        db_url = f"sqlite:///{db_conf['NAME']}"

        jobstores = {'default': SQLAlchemyJobStore(url=db_url)}
        executors = {'default': ThreadPoolExecutor(max_workers=20)} # Only 20 jobs can run at once
        scheduler = BlockingScheduler(executors=executors, jobstores=jobstores, job_defaults={'misfire_grace_time': 900})
        
        scheduler.add_job(heartbeat_task, 'interval', seconds=30, replace_existing=True, id="hearbeat")

        self.stdout.write("Scheduler started...")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            pass

            


        