from django.contrib import admin
from django.apps import apps
from .models import *

current_app = apps.get_containing_app_config(__name__)

for mdl in current_app.get_models():
    try:
        admin.site.register(mdl)
    except:
        pass
