from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from django.utils import timezone
from django.contrib.auth.models import User

from bots.models import model_personality
from synapse.models import user_info, connection_functions, connection_function_saved_inputs, local_function_files

bot_tool_list = [
    ("fast","fast"), 
    ("thinking","thinking"), 
    ("websearch","websearch"),
    ("local_files","local files"),
]

task_comment_type = [
    ('u', 'User'),
    ('a', 'API'),
    ('o', 'Other'),
]

status_for_tasks = [
    ('p2s', 'pending task to start'),
    ('p2f', 'pending task to finish'),
    ('p2r', 'pending task review'),
    ('p2h', 'pending help/input'),
    ('p2o', 'pending other'),
]

task_relationship = [
    ('s2s', 'start to start'),
    ('s2f', 'start to finish'),
    ('f2f', 'finish to finish'),
    ('f2s', 'finish to start'),
    ('o', 'other'),
]

template_run_schedule = [
    ('one_time', 'one-time'),
    ('repeat_day', 'daily'),
    ('repeat_wkly', 'weekly'),
    ('repeat_mthly','monthly'),
    ('repeat_yrly', 'yearly'),
    
    ('repeat_hourly', 'every-hour'),
    ('repeat_6_hourly', 'every-6hours'),
    ('repeat_12_hourly', 'every-12hours'),
]

task_type_list = [
    ('parent', 'Parent'),
    ('copy', 'Copy'),
    ('other', 'Other'),
]

class project_template(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    project_name = models.CharField(max_length=100, primary_key=True, unique=True)
    project_description = models.TextField()
    pm_owner = models.ForeignKey(User, on_delete=models.CASCADE, unique=False)

class axiom_bot_message_task(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    chat_user = models.ForeignKey(User, on_delete=models.CASCADE, unique=False) #owner/user-rights
    bot_personality = models.ForeignKey(model_personality, on_delete=models.CASCADE, unique=False) #bot personality - bots.models
    bot_tool = models.CharField(max_length=100, choices=bot_tool_list, default='fast') #bot tools for message
    user_prompt = models.TextField()
    model_response = models.TextField(blank=True, null=True)

    bot_function = models.ForeignKey(connection_functions, on_delete=models.CASCADE, unique=False, blank=True, null=True) #function to perform - input/output form
    bot_local_function = models.ForeignKey(local_function_files, on_delete=models.CASCADE, unique=False, blank=True, null=True) #function to perform - input/output form
    bot_saved_input = models.ForeignKey(connection_function_saved_inputs, on_delete=models.CASCADE, unique=False, blank=True, null=True) #function to perform - input/output form

    task_project = models.ForeignKey(project_template, on_delete=models.CASCADE, unique=False) #template
    task_project_order = models.PositiveSmallIntegerField()
    fixed_output = models.TextField(blank=True, null=True, default="{\"response\":\"model_response\"}")
    task_type = models.CharField(max_length=100, choices=task_type_list, default='parent')

class axiom_bot_message_saved_input(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    chat_user = models.ForeignKey(User, on_delete=models.CASCADE, unique=False) #owner/user-rights
    bot_personality = models.ForeignKey(model_personality, on_delete=models.CASCADE, unique=False) #bot personality - bots.models
    bot_tool = models.CharField(max_length=100, choices=bot_tool_list, default='fast') #bot tools for message
    user_prompt = models.TextField()
    model_response = models.TextField(blank=True, null=True)

    bot_saved_input = models.ForeignKey(connection_function_saved_inputs, on_delete=models.CASCADE, unique=False, blank=True, null=True) #function to perform - input/output form
    
class axiom_bot_message_connection_func(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    chat_user = models.ForeignKey(User, on_delete=models.CASCADE, unique=False) #owner/user-rights
    bot_personality = models.ForeignKey(model_personality, on_delete=models.CASCADE, unique=False) #bot personality - bots.models
    bot_tool = models.CharField(max_length=100, choices=bot_tool_list, default='fast') #bot tools for message
    user_prompt = models.TextField()
    model_response = models.TextField(blank=True, null=True)

    bot_function = models.ForeignKey(connection_functions, on_delete=models.CASCADE, unique=False, blank=True, null=True) #function to perform - input/output form

class ax_task_comments(models.Model):
    datetime_created = models.DateTimeField('date created', default=timezone.now)
    comment_task = models.ForeignKey(axiom_bot_message_task, on_delete=models.CASCADE)
    comment = models.TextField()
    task_comment_type = models.CharField(max_length=3, choices=task_comment_type, default='o')

class ax_task_attachement(models.Model):
    datetime_created = models.DateTimeField('date created', default=timezone.now)
    attachemnet_task = models.ForeignKey(axiom_bot_message_task, on_delete=models.CASCADE)
    attachemnet = models.CharField(max_length=500, default='')

class ax_task_prerequisite(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    task_relationship = models.CharField(max_length=5, choices=task_relationship, default='n')
    main_task = models.ForeignKey(axiom_bot_message_task, on_delete=models.CASCADE, related_name='main_task')
    second_task = models.ForeignKey(axiom_bot_message_task, on_delete=models.CASCADE, related_name='second_task')

    def clean(self):
        if self.main_task == self.second_task:
            raise ValidationError("tasks cannot be the same.")

class ax_task_status_list(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    task_observed = models.ForeignKey(axiom_bot_message_task, on_delete=models.CASCADE, unique=False)
    status_of_task = models.CharField(max_length=5, choices=status_for_tasks, default='p2h')
    task_message = models.TextField(blank=True, null=True)

class project_template_schedule(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    project_name = models.ForeignKey(project_template, on_delete=models.CASCADE)
    project_run_schedule = models.CharField(max_length=100, choices=template_run_schedule, default='one_time')
    run_date = models.DateTimeField('date created', default=timezone.now)


class internal_document(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    document_name = models.CharField(max_length=100, primary_key=True, unique=True)
    document_object = models.TextField()
    document_personality = models.ForeignKey(model_personality, on_delete=models.CASCADE, unique=False, default=1)
    document_type = models.CharField(max_length=75, default='other', 
            validators=[RegexValidator(regex=r'^[a-zA-Z0-9]*$',
            message='No spaces or special characters.')])

class internal_document_version(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    document_text = models.TextField()
    document_notes = models.TextField()
    document_version = models.PositiveIntegerField()
    internal_document = models.ForeignKey(internal_document, on_delete=models.CASCADE, unique=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['document_version', 'internal_document'], name='unique_doc_version')]
