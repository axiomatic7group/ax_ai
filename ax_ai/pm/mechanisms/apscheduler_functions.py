from django.utils import timezone

import sys
from pm.models import *
import pandas as pd

def send_user_message(message, user_to_recieve_id):
    if User.objects.filter(id=user_to_recieve_id).exists():
        user_to_recieve = User.objects.get(id=user_to_recieve_id)
        user_to_recieve = user_info.objects.get(user=user_to_recieve)
        print("sending ... " + message + " to user " + user_to_recieve.first_name)
        
        obj = user_messages.objects.create(date_created=timezone.now(),
                                        message_type="system",
                                        message=message,
                                        message_warning_level="notify",
                                        user_reciver=user_to_recieve,
                                        message_sender="scheduler")

def check_task_status(task_id):
    if task.objects.filter(id=task_id).exists():
        
        all_tasks = pd.DataFrame(task.objects.filter(id=task_id).values())
        today = timezone.now()
        print("checking status ...")
        for i_task, row_task in all_tasks.iterrows():
            if row_task['task_status'] == 'completed':
                continue
            elif row_task['start_date'] > today:
                if row_task['task_status'] == 'not_started':
                    continue
                else:
                    task_to_change = task.objects.get(id=row_task['id'])
                    task_to_change.task_status = "not_started"
                    task_to_change.save()
            elif row_task['start_date'] <= today and row_task['soft_due_date'] > today:
                if row_task['task_status'] == 'in_progress':
                    continue
                else:
                    task_to_change = task.objects.get(id=row_task['id'])
                    task_to_change.task_status = "in_progress"
                    task_to_change.save()
            
            elif row_task['soft_due_date'] <= today and row_task['hard_due_date'] > today:
                if row_task['task_status'] == 'late':
                    continue
                else:
                    task_to_change = task.objects.get(id=row_task['id'])
                    task_to_change.task_status = "late"
                    task_to_change.save()
            
            elif row_task['hard_due_date'] <= today:
                if row_task['task_status'] == 'past_due':
                    continue
                else:
                    task_to_change = task.objects.get(id=row_task['id'])
                    task_to_change.task_status = "past_due"
                    task_to_change.save()
            else:
                print("no dates", row_task)