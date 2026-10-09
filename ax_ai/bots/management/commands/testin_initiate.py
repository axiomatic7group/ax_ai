import pandas as pd
from bots.models import *
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

import subprocess, requests, os

TEMP_MEDIA_ROOT = os.path.join(settings.BASE_DIR, 'tmp')
os.makedirs(TEMP_MEDIA_ROOT, exist_ok=True)

def initiate_model(model_int_id):
    if model_intiate.objects.filter(id=model_int_id).exists:
        model_to_initiate = pd.DataFrame(model_intiate.objects.filter(id=model_int_id).values())


    else:
        return {"message":"model not found",
                "state":"0"}

    try:
        cmd = [
            "./llama-server", 
            "-hf", model_to_initiate['name_nd_quant'].iloc[0], 
            "--host", "0.0.0.0", 
            "--port", "8080",
            "-ngl", "99",
            "--cache-type-k", "q8_0",
            "--flash-attn", "on",
            "--media-path", TEMP_MEDIA_ROOT,]
        process = subprocess.Popen( cmd, cwd=model_to_initiate['path_to_build'].iloc[0])
        
        return process
        
    except Exception as e:
        print(f"Failed to start server: {e}")
        return None



class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('model_to_initiate', type=int)

    def handle(self, *args, **options):
        model_to_initiate = options['model_to_initiate']
        initiate_model(model_to_initiate)