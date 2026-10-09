from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core import signing


server_type_list = [
    ('llama.cpp', 'llama.cpp'),
    ('vllm', 'vllm'),
]

chat_type_list = [
    ('admin', 'admin'),
    ('support', 'support'),
    ('axiom', 'axiom'),
]

chat_sender_list = [
    ('user', 'user'),
    ('model', 'model'),
]

personality_type_list = [
    ('behavior', 'behavior'),
    ('outcome', 'outcome'),
    ('agent', 'agent'),
    ('other', 'other'),
]

class model_base(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    model_base_name = models.CharField(max_length=100, default="local", unique=True)
    model_base_url = models.CharField(max_length=350, default="http://127.0.0.1:8080")

class model_base_user_connection(models.Model):
    model_base = models.ForeignKey(model_base, on_delete=models.CASCADE, unique=False)
    chat_user = models.ForeignKey(User, on_delete=models.CASCADE, unique=False)
    date_created = models.DateTimeField('date created', default=timezone.now)
    _model_api_key = models.CharField(max_length=150, blank=True, default="")

    @property
    def model_api_key(self):
        if not self._model_api_key:
            return ""
        try:
            return signing.loads(self._model_api_key)
        except signing.BadSignature:
            return ""
        
    @model_api_key.setter
    def model_api_key(self, value):
        self._model_api_key = signing.dumps(value) if value else None


class model_connection(models.Model):
    model_base = models.ForeignKey(model_base, on_delete=models.CASCADE, unique=False, default=2,)

    date_created = models.DateTimeField('date created', default=timezone.now)
    model_name = models.CharField(max_length=100)
    input_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, default=0.00)
    output_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, default=0.00)
    request_limit = models.CharField(max_length=100, blank=True, default="")
    token_limit = models.CharField(max_length=100, blank=True, default="")

class model_intiate(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    model_base_name = models.CharField(max_length=250, default="1")
    name_nd_quant = models.CharField(max_length=150)
    path_to_build = models.CharField(max_length=150)
    server_type = models.CharField(max_length=100, choices=server_type_list, default='llama.cpp')
    number_of_params = models.CharField(max_length=100, blank=True, default="")
    quantization = models.CharField(max_length=100, blank=True, default="")


class model_chats(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    model_connection_name = models.ForeignKey(model_connection, on_delete=models.CASCADE, unique=False)
    chat_user = models.ForeignKey(User, on_delete=models.CASCADE, unique=False)
    chat_type = models.CharField(max_length=100, choices=chat_type_list, default='admin')
    chat_title = models.CharField(max_length=75, default='')

   
class chat_messages(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    message_model_chats = models.ForeignKey(model_chats, on_delete=models.CASCADE, unique=False)
    chat_sender = models.CharField(max_length=100, choices=chat_sender_list)
    chat_meta = models.CharField(max_length=500)
    chat_message = models.TextField()

class chat_message_summarized(models.Model):
    date_summairzed = models.DateTimeField('date created', default=timezone.now)
    chat_message = models.OneToOneField(chat_messages, on_delete=models.CASCADE)
    chat_summarized = models.BooleanField(default=False)

class message_attachment(models.Model):
    datetime_created = models.DateTimeField('date created', default=timezone.now)
    attachemnet_task = models.ForeignKey(chat_messages, on_delete=models.CASCADE)
    attachmnet = models.CharField(max_length=500, default='')

class model_personality(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    personality_name = models.CharField(max_length=75)
    personality_description = models.TextField()
    personality_type = models.CharField(max_length=100, choices=personality_type_list, default='behavior')
    personality_temp = models.DecimalField(default=0.75, max_digits=2, decimal_places=2)
    personality_top_p = models.DecimalField(default=0.9, max_digits=2, decimal_places=2)

class model_chats_plan(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    model_chat = models.OneToOneField(model_chats, on_delete=models.CASCADE)
    chat_plan = models.TextField()
    plan_title = models.CharField(max_length=75)

