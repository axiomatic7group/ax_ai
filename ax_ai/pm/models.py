from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q, CheckConstraint
from django.core.exceptions import ValidationError

from synapse.models import user_info


user_type = [
    ('staff', 'staff'),
    ('stakeholder', 'stakeholder'),
    ('other', 'other'),
]

task_schedule = [
    ('one_time', 'one-time'),
    ('repeat_wkly', 'repeat weekly'),
    ('repeat_mthly','repeat monthly'),
    ('repeat_yrly', 'repeat yearly'),
]

task_progress = [
    ('completed', 'completed'),
    ('in_progress', 'in-progress'),
    ('not_started', 'not started'),
    ('past_due', 'past due'),
    ('late', 'late'),
]

task_relationship = [
    ('s2s', 'start to start'),
    ('s2f', 'start to finish'),
    ('f2f', 'finish to finish'),
    ('f2s', 'finish to start'),
    ('n', 'none'),
]

types_of_messages = [
    ('system', 'system'),
    ('stakeholder', 'stakeholder'),
    ('staff', 'staff'),
    ('other', 'other'),
]

warning_levels = [
    ('SOS', 'SOS'),
    ('urgent', 'urgent'),
    ('notify', 'notify'),
    ('background', 'background'),
    ('none', 'none'),
    ('other', 'other'),
]

task_comment_type = [
    ('u', 'User'),
    ('a', 'API'),
    ('o', 'Other'),
    ('n', 'Client Notes'),
    ('e', 'Enriched Lead'),
    ('f', 'Follow Up Suggestion'),
]

status_for_tasks = [
    ('p2s', 'pending task to start'),
    ('p2f', 'pending task to finish'),
    ('p2r', 'pending task review'),
    ('p2h', 'pending task help'),
    ('p2o', 'pending task other'),
]


class project(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    project_name = models.CharField(max_length=100, primary_key=True, unique=True)
    project_description = models.CharField(max_length=500, default='')
    pm_owner = models.ForeignKey(user_info, on_delete=models.CASCADE, unique=False)

class project_group(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    project_group_name = models.CharField(max_length=100)
    project_group_description = models.CharField(max_length=500, default='')

class project_grouping(models.Model):
    project = models.ForeignKey(project, on_delete=models.CASCADE)
    project_group = models.ForeignKey(project_group, on_delete=models.CASCADE)

class deliverable(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    deliverable_name = models.CharField(max_length=100)
    deliverable_description = models.CharField(max_length=500, default='')
    deliverable_project = models.ForeignKey(project, on_delete=models.CASCADE)
    start_date = models.DateTimeField('start date', default=timezone.now)

class deliverable_group(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    deliverable_group_name = models.CharField(max_length=100)
    deliverable_group_description = models.CharField(max_length=500, default='')

class deliverable_grouping(models.Model):
    deliverable = models.ForeignKey(deliverable, on_delete=models.CASCADE)
    deliverable_group = models.ForeignKey(deliverable_group, on_delete=models.CASCADE)

class deliverable_stakeholder(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    deliverable = models.ForeignKey(deliverable, on_delete=models.CASCADE, unique=False)
    stake_holder = models.ForeignKey(user_info, on_delete=models.CASCADE, unique=False)

    def clean(self):
        if not self.stake_holder.user_type == 'stakeholder':
            raise ValidationError('user must be stakeholder')

class project_stakeholder(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    sh_project = models.ForeignKey(project, on_delete=models.CASCADE, unique=False)
    stake_holder = models.ForeignKey(user_info, on_delete=models.CASCADE, unique=False)

    def clean(self):
        if not self.stake_holder.user_type == 'stakeholder':
            raise ValidationError('user must be stakeholder')

class task(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    task_name = models.CharField(max_length=100)
    task_description = models.TextField()
    start_date = models.DateTimeField('start_date', default=timezone.now)
    soft_due_date = models.DateTimeField('soft_due_date', default=timezone.now)
    hard_due_date = models.DateTimeField('hard_due_date', default=timezone.now)
    task_status = models.CharField(max_length=100, choices=task_progress, default='not_started')
    task_schedule = models.CharField(max_length=100, choices=task_schedule, default='one_time')

    task_deliverable = models.ForeignKey(deliverable, on_delete=models.CASCADE, blank=True, null=True)
    task_project = models.ForeignKey(project, on_delete=models.CASCADE, blank=True, null=True)
    class Meta:
        constraints = [
            CheckConstraint(
                condition = Q(task_deliverable=None) | Q(task_project=None),
                name='at_least_1_non_null',
            ),
            CheckConstraint(
                condition = Q(task_deliverable=None) | Q(task_project=None),
                name='at_least_1_null',
            ),
        ]

class task_staff(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    task = models.ForeignKey(task, on_delete=models.CASCADE, unique=False)
    staff = models.ForeignKey(user_info, on_delete=models.CASCADE, unique=False)

    def clean(self):
        if not self.staff.user_type == 'staff':
            raise ValidationError('user must be staff')

class task_comments(models.Model):
    datetime_created = models.DateTimeField('date created', default=timezone.now)
    comment_task = models.ForeignKey(task, on_delete=models.CASCADE)
    comment = models.TextField()
    task_comment_owner = models.ForeignKey(user_info, on_delete=models.CASCADE)
    task_comment_type = models.CharField(max_length=3, choices=task_comment_type, default='o')

class task_attachement(models.Model):
    datetime_created = models.DateTimeField('date created', default=timezone.now)
    attachemnet_task = models.ForeignKey(task, on_delete=models.CASCADE)
    attachemnet = models.CharField(max_length=500, default='')
    attachemnet_owner = models.ForeignKey(user_info, on_delete=models.CASCADE)

class task_prerequisite(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    task_relationship = models.CharField(max_length=5, choices=task_relationship, default='n')
    main_task = models.ForeignKey(task, on_delete=models.CASCADE, related_name='main_task')
    second_task = models.ForeignKey(task, on_delete=models.CASCADE, related_name='second_task')

    def clean(self):
        if self.main_task == self.second_task:
            raise ValidationError("tasks cannot be the same.")

class user_messages(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    message_type = models.CharField(max_length=25, choices=types_of_messages, default='other')
    message = models.TextField()
    message_warning_level = models.CharField(max_length=100, choices=warning_levels, default='notify')
    user_reciver = models.ForeignKey(user_info, on_delete=models.CASCADE, unique=False)
    message_sender = models.CharField(max_length=250, default='')

class task_status_list(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    task_observed = models.ForeignKey(task, on_delete=models.CASCADE, unique=False)
    status_of_task = models.CharField(max_length=5, choices=status_for_tasks, default='p2o')
    task_message = models.TextField()
