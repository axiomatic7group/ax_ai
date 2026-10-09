from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
import subprocess
from decimal import Decimal
from datetime import date, datetime

import plotly.express as px
from plotly.offline import plot

from django.conf import settings
from pathlib import Path
from sqlalchemy import create_engine

import pandas as pd
import json, re, os, sqlite3, requests, glob, markdown
from dateutil.relativedelta import relativedelta
import numpy as np

from .models import *
from .forms import *

from axiom.forms import add_axiom_bot_message_saved_input, add_axiom_bot_message_connection_func
from axiom.models import axiom_bot_message_saved_input, model_personality
from axiom.views import send_task_to_model
from bots.models import model_connection


def form_to_json_schema(form):
    schema = {}
    for name, field in form.fields.items():    
        field_data = {}
        if hasattr(field, 'choices') and field.choices:
            field_data['choices'] = [{'option': str(c[1])} for c in field.choices]
        schema[name] = field_data
    return schema

"""def check_authentication(check_request):
    if not check_request.user.is_authenticated:
        user_auth_form = AuthenticationForm(check_request.GET or None)
        context = {'user_auth_form':user_auth_form}
        return redirect('/admin')"""

def check_authentication(check_request):
    if not check_request.user.is_authenticated:
        return redirect("/login")
    elif not check_request.user.is_staff:
        return redirect("/login")

def get_connection_data(new_data_connection):
### if connection is a datatable
    if new_data_connection.connection_to_datable:
        table_connection = new_data_connection.connection_to_datable
        db_user_connection = table_connection.user_db_connection
        db_connection = db_user_connection.connection_to_db

        if db_connection.database_type == "sqlite":
            test_get_string = f"{db_connection.database_url}"
            conn = sqlite3.connect(test_get_string)
        elif db_connection.database_type == "postges":
            test_get_string = f"postgresql+psycopg2://{db_user_connection.db_username}:{db_user_connection.db_password}@{db_connection.database_url}:{db_connection.database_port}/{db_connection.database_name}"
            conn = create_engine(test_get_string)
        
        try:
            temp_data = pd.read_sql(f"select * from {table_connection.datatable_name};", conn)
            return {'status':'1', 'temp_data':temp_data, "type": "df"}
        
        except:
            return {'status':'0', 'message':f'datatable {table_connection.datatable_name} does not exist.'}
### if connection is an API connection        
    elif new_data_connection.connection_to_api:
        api_connection = new_data_connection.connection_to_api
        test_get_string = api_connection.api_base_url
        if "__input__api_key__" in api_connection.api_headers:
            test_get_headers = json.loads(api_connection.api_headers.replace('__input__api_key__', api_connection.api_key))
        elif "__input___api_password__" in api_connection.api_headers:
            test_get_headers = json.loads(api_connection.api_headers.replace('__input___api_password__', api_connection.api_password).replace('__input___api_username__', api_connection.api_username))
        else:
            test_get_headers = json.loads(api_connection.api_headers)

        if '_api_key__' in test_get_string:
            test_get_string = test_get_string.replace('__input___api_key__', api_connection.api_key)
        if '_api_password__' in test_get_string:
            test_get_string = test_get_string.replace('__input___api_password__', api_connection.api_password)
            test_get_string = test_get_string.replace('__input___api_username__', api_connection.api_username)
        
        test_input_function = new_data_connection.function_extension
        if '__input__' in test_input_function:
            input_labels = re.findall(r'__input__(.*?)__', test_input_function)
            input_schema = json.loads(new_data_connection.function_input_values_schema)
            for input_label in input_schema:
                if input_label in input_labels:
                    test_input_function = test_input_function.replace(f"__input__{input_label}__", input_schema[input_label])
        
        test_get_string = test_get_string.replace('__input__function__', test_input_function)

        try:
### request the data with all passwords/inputs needed
            temp_request = requests.get(test_get_string, headers=test_get_headers).json()
### check if output has "extensions" or cleaning processes needed & check expected output type
            if new_data_connection.function_output_extensions != '':
                temp_data = pd.DataFrame(temp_request[new_data_connection.function_output_extensions])

            else:
                try:
                    temp_data = pd.DataFrame(temp_request)
                except:
                    temp_data = pd.DataFrame([temp_request])
                    
            return {'status':'1', 'temp_data':temp_data}
        except requests.exceptions.RequestException as er:
            return {'status':'0', 'message':f'api function {new_data_connection.connection_function_name} does not work.', 'error':er}

def get_connection_data_w_input(new_data_connection, input_dict):
    if new_data_connection.connection_to_datable:
        table_connection = new_data_connection.connection_to_datable
        db_user_connection = table_connection.user_db_connection
        db_connection = db_user_connection.connection_to_db
        

        if db_connection.database_type == "sqlite":
            test_get_string = f"{db_connection.database_url}"
            conn = sqlite3.connect(test_get_string)
        elif db_connection.database_type == "postges":
            test_get_string = f"postgresql+psycopg2://{db_user_connection.db_username}:{db_user_connection.db_password}@{db_connection.database_url}:{db_connection.database_port}/{db_connection.database_name}"
            conn = create_engine(test_get_string)
        
        try:
            temp_data = pd.read_sql(f"select * from {table_connection.datatable_name};", conn)
            if input_dict == {}:
                temp_data = temp_data

            elif new_data_connection.function_type == "mapping":
                temp_data = temp_data[temp_data[list(input_dict.keys())[0]] == input_dict[list(input_dict.keys())[0]]]
            
            return {'status':'1', 'temp_data':temp_data}
        
        except:
            return {'status':'0', 'message':f'datatable {table_connection.datatable_name} does not exist.'}
        
    elif new_data_connection.connection_to_api:
        api_connection = new_data_connection.connection_to_api
        test_get_string = api_connection.api_base_url
        if "__input__api_key__" in api_connection.api_headers:
            test_get_headers = json.loads(api_connection.api_headers.replace('__input__api_key__', api_connection.api_key))
        elif "__input___api_password__" in api_connection.api_headers:
            test_get_headers = json.loads(api_connection.api_headers.replace('__input___api_password__', api_connection.api_password).replace('__input___api_username__', api_connection.api_username))
        else:
            temp_test = api_connection.api_headers.replace("'", '"')
            try:
                test_get_headers = json.loads(temp_test)
            except:
                test_get_headers = {'none':'none'}

        if '_api_key__' in test_get_string:
            if api_connection.api_key:
                test_get_string = test_get_string.replace('__input___api_key__', api_connection.api_key)
            else:
                test_get_string = test_get_string.replace('__input___api_key__', api_connection._api_key)
        if '_api_password__' in test_get_string:
            test_get_string = test_get_string.replace('__input___api_password__', api_connection.api_password)
            test_get_string = test_get_string.replace('__input___api_username__', api_connection.api_username)
        
        
        test_input_function = new_data_connection.function_extension
        if '__input__' in test_input_function:
            input_labels = re.findall(r'__input__(.*?)__', test_input_function)
            try:
                input_schema = json.loads(input_dict)
            except:
                input_schema = input_dict

            for input_label in input_schema:
                if input_label in test_input_function:
                    if "__input__" not in input_label:
                        new_input_label = f"__input__{input_label}__"
                    else:
                        new_input_label = input_label
                    test_input_function = test_input_function.replace(new_input_label, input_schema[input_label])
        
        test_get_string = test_get_string.replace('__input__function__', test_input_function)

        temp_request = requests.get(test_get_string, headers=test_get_headers)
        if "__json__" in str(new_data_connection.function_output_extensions):
            temp_data = temp_request.json()
        elif new_data_connection.function_output_extensions != '':
            temp_data = pd.DataFrame(temp_request[new_data_connection.function_output_extensions])
        else:
            try:
                temp_data = pd.DataFrame(temp_request.json())
            except:
                temp_data = pd.DataFrame([temp_request.json()])

        return {'status':'1', 'temp_data':temp_data}
        
        """try:
            temp_request = requests.get(test_get_string, headers=test_get_headers).json()
            if "__json__" in str(new_data_connection.function_output_extensions):
                temp_data = temp_request
            elif new_data_connection.function_output_extensions != '':
                temp_data = pd.DataFrame(temp_request[new_data_connection.function_output_extensions])
            else:
                try:
                    temp_data = pd.DataFrame(temp_request)
                except:
                    temp_data = pd.DataFrame([temp_request])

            return {'status':'1', 'temp_data':temp_data}
        except:
            return {'status':'0', 'message':f'api function {new_data_connection.connection_function_name} does not work.'}"""

def get_local_connection_data(local_connection_request):

    if local_function_files.objects.filter(local_function_name=local_connection_request['local_function_name']).exists():
        function_to_run = local_function_files.objects.get(local_function_name=local_connection_request['local_function_name'])
        if function_to_run.local_function_type == "python":
            run_list = ["python", str(function_to_run.local_function_path), str(function_to_run.local_function_name)]
            for i_keys, e_keys in enumerate(local_connection_request.keys()):
                if "__input__" in e_keys:
                    run_list.append(str(local_connection_request[e_keys])) 
            result = subprocess.run(run_list, capture_output=True, text=True)

            return result

        else:
            return function_to_run.local_function_name

def local_file_to_db(request, local_data_files):
    if check_authentication(request) != None:
        return check_authentication(request)
    context = {}
    request_user = User.objects.get(username=request.user)
    request_user = user_info.objects.get(user=request_user)
    
    temp_local_file = local_data_files
    db_table_name = re.sub(r'[^a-zA-Z0-9_]', '', temp_local_file.local_file_name.replace(" ", "_"))
    db_conf = settings.BASE_DIR

    db_url = f"{db_conf}/db.sqlite3"
    if not datatable_connection.objects.filter(datatable_name=db_table_name).exists():
        new_db_conn = database_connection.objects.create(
            date_created=timezone.now(),
            database_type="sqlite",
            database_url=db_url,
            database_port='',)
        new_user_conn = database_user_connection.objects.create(
            user_connection=request_user,
            connection_to_db=new_db_conn,
            db_username='',
            db_password='',)
        new_table_conn = datatable_connection.objects.create(
            user_db_connection=new_user_conn,
            datatable_name=db_table_name,
            databale_type='data',)
        new_con_func = connection_functions.objects.create(
            connection_function_name=db_table_name,
            function_type='data',
            function_extension='x',
            function_input_values_schema='x',
            connection_to_datable = new_table_conn
        )

    conn = sqlite3.connect(db_url)
    
    path_to_file = temp_local_file.local_file_path
    if path_to_file[-1] not in r'/\\':
        path_to_file = path_to_file + "/" + temp_local_file.local_file_name
    else:
        path_to_file = path_to_file + temp_local_file.local_file_name
    
    paths = glob.glob(path_to_file)

    output_df = pd.DataFrame()
    for p in paths:
        path_obj = Path(p)
        if path_obj.is_file():
            if temp_local_file.local_file_type == 'xlsx':
                temp_pd = pd.read_excel(path_obj, header=int(temp_local_file.local_file_header), sheet_name=temp_local_file.local_file_sheet)
                output_df = pd.concat([temp_pd, output_df])
            elif temp_local_file.local_file_type == 'csv':
                temp_pd = pd.read_csv(path_obj, header=int(temp_local_file.local_file_header))
                output_df = pd.concat([temp_pd, output_df])
    if not output_df.empty:
        output_df.to_sql(db_table_name, if_exists='append', con=conn, index=False)
        conn.close()
        return {'status':'1', 'db_table_name': db_table_name}
    else:
        return {'status':'0', 'message': f"could not create table for file {db_table_name}"}

"""
class create_new_user(View):
    def get(self, request):
        create_user_form = UserCreationForm(request.GET or None)
        user_info_form = add_new_users(request.GET or None)

        context = {'create_user_form':create_user_form,
                   'user_info_form': user_info_form,}
        
        return render(request, 'synapse/signup.html', context)
    
    def post(self, request):
        create_user_form = UserCreationForm(request.POST or None)
        user_info_form = add_new_users(request.POST or None)

        if create_user_form.is_valid():
            if user_info_form.is_valid():
                new_user = create_user_form.save(commit=False)
                new_user_info = user_info_form.save(commit=False)
                new_user.email = user_info_form.cleaned_data['user_email']
                new_user.save()
                new_user_info.created_date = timezone.now()
                new_user_info.user = new_user
                new_user_info.save()

        else:
            create_user_form = UserCreationForm(request.POST or None)
            user_info_form = add_new_users(request.POST or None)

        context = {'create_user_form':create_user_form,
                   'user_info_form': user_info_form,}
        
        return render(request, 'synapse/signup.html', context)

    def get_api(self):
        create_user_form = UserCreationForm()
        create_user_json = form_to_json_schema(create_user_form)

        user_info_form = add_new_users()
        user_info_json = form_to_json_schema(user_info_form)

        json_form = {'message': 'These are the forms used to create new users and related info for new users. Next, you will find 2 items, each item being a form and some relevant information. Please make sure your response follows the format provided.',
            'items':[{'name': 'User Creation Form', 
                    'description':'This form is used to create new users. All fields must be filled for the form to be submitted.', 
                    'form':create_user_json,
                    'format':{'User Creation Form':{'username':'newuser_api', 'password1':'very_secure_password', 'password2':'very_secure_password',}}},
                    {'name': 'New User Info Form', 
                    'description':'This form is used to collect relevant information related to new users. All fields must be filled for the form to be submitted.', 
                    'form':user_info_json,
                    'format':{'New User Info Form': { 'first_name':'John', 'last_name':'Smith', 'user_email':'jsmith2@mail.com', 'user_type':'other',}}}]}
        
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        try:
            data = json.loads(request.body.decode('utf-8'))

            user_creation_json = data['User Creation Form']
            user_info_json = data['New User Info Form']
        except:
            data = {'message':'An error has occured, please ensure your request follows the format below.',
                'format':{'User Creation Form':{'username':'newuser_api', 'password1':'very_secure_password', 'password2':'very_secure_password',},
                'New User Info Form':{'first_name':'John', 'last_name':'Smith', 'user_email':'jsmith2@mail.com', 'user_type':'other',}}}
            return JsonResponse(data)
        
        create_user_form = UserCreationForm(user_creation_json)
        user_info_form = add_new_users(user_info_json)

        if create_user_form.is_valid():
            if user_info_form.is_valid():
                new_user = create_user_form.save(commit=False)
                new_user_info = user_info_form.save(commit=False)
                new_user.email = user_info_form.cleaned_data['user_email']
                new_user.save()
                new_user_info.created_date = timezone.now()
                new_user_info.user = new_user
                new_user_info.save()
            
            json_form = {'message':'user created!'}

        else:
            json_form = {}
            for e_error in create_user_form.errors.values():
                print(e_error)
                json_form.update({'error_'+str(len(json_form)+1):e_error})
            for e_error in user_info_form.errors.values():
                print(e_error)
                json_form.update({'error_'+str(len(json_form)+1):e_error})
        
        return JsonResponse(json_form)

class delete_user(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        user_delete_form = AuthenticationForm(request.GET or None)
        context = {'user_delete_form':user_delete_form}
        return render(request, 'synapse/login_delete.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        user_delete_form = AuthenticationForm(data=request.POST or None)

        if user_delete_form.is_valid():
            username = user_delete_form.cleaned_data.get('username')
            password = user_delete_form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                user.delete()
                user_delete_form = AuthenticationForm(request.GET or None)
                context = {'user_delete_form':user_delete_form}
                return render(request, 'synapse/login.html', context)

        context = {'user_delete_form':user_delete_form}
        return render(request, 'synapse/login_delete.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        json_form = {'message':'Trying to delete your account? please provide your username and password. Please make sure your response follows the format provided below.',
                     'format':{'login': {'username':'new_user', 'password':'super_secure_password'}}}
        return JsonResponse(json_form)
       
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        login_data = data['login']
        username = login_data['username']
        password = login_data['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            user.delete()
            data = {'message':'user has been deleted.'}
            print(data)
            return JsonResponse(data)

        else:
            data = {'message':'An error has occured, to delete your account, please ensure your request follows the format below.',
                    'format':{'login': {'username':'new_user', 'password':'super_secure_password'}}}
            return JsonResponse(data)

"""

class manage_database_connection(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_database_connection_form = create_database_connection(request.GET or None)
        context = {'create_database_connection_form':create_database_connection_form}
        return render(request, 'synapse/create_database_connection.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_database_connection_form = create_database_connection(request.POST or None)
        if create_database_connection_form.is_valid():
            new_database_connection = create_database_connection_form.save(commit=False)
            new_database_connection.created_date = timezone.now()
            new_database_connection.save()
            context = {'new_database_connection':new_database_connection}
### update redirect
            return redirect('/synapse/add_database_user_connection/')
        else:
            
            context = {'create_database_connection_form':create_database_connection_form}
            return render(request, 'synapse/create_database_connection.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_database_connection_form = create_database_connection()
        create_database_connection_form = form_to_json_schema(create_database_connection_form)
        json_form = {'message':'This form is used to create a new project, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
            'items':[{'name': 'Create Database Connection Form', 
                'description':'This form is used to create Database Connection. All fields must be filled for the form to be submitted.', 
                'form':create_database_connection_form, 
                'format':{'Create Database Connection Form': 
                    {'database_type':'see list in form.', 
                    'database_url':'url connection to db',
                    'database_port':'port to be used for connection; default is 5432.' }}},]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_database_connection_data = data['Create Database Connection Form']
        if all(key in new_database_connection_data for key in ['database_type', 'database_url']):
            create_database_connection_form = create_database_connection(new_database_connection_data)
            if create_database_connection_form.is_valid():
                new_database_connection = create_database_connection_form.save(commit=False)
                new_database_connection.created_date = timezone.now()
                new_database_connection.save()
                data = {'message':'new database connection has been created.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_database_connection_form.errors}
        
        data = {'message':'An error has occured, please ensure your request follows the format below.',
                'format':{'Create Database Connection Form': 
                    {'database_type':'see list in form.', 
                    'database_url':'url connection to db',
                    'database_port':'port to be used for connection; default is 5432.' }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_database_connection(request, database_connection_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if database_connection.objects.filter(id=database_connection_id).exists():
            database_connection_to_delete = database_connection.objects.get(id=database_connection_id)
            database_connection_to_delete.delete()
            
        data = {'message':'database_connection deleted'}
        return redirect('/synapse/')

class manage_database_user_connection(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_database_user_connection_form = create_database_user_connection(request.GET or None, user=request.user)
        context = {'create_database_user_connection_form':create_database_user_connection_form}
        return render(request, 'synapse/create_database_user_connection.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_database_user_connection_form = create_database_user_connection(request.POST or None, user=request.user)
        if create_database_user_connection_form.is_valid():
            new_database_user_connection = create_database_user_connection_form.save(commit=False)
            new_database_user_connection.created_date = timezone.now()
            new_database_user_connection.save()
            context = {'new_database_user_connection':new_database_user_connection}
### update redirect
            return redirect('/synapse/add_datatable_connection/')
        else:
            
            context = {'create_database_user_connection_form':create_database_user_connection_form}
            return render(request, 'synapse/create_database_user_connection.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_database_user_connection_form = create_database_user_connection(user=request.user)
        create_database_user_connection_form = form_to_json_schema(create_database_user_connection_form)
        json_form = {'message':'This form is used to create a new project, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
            'items':[{'name': 'Create database user connection Form', 
                'description':'This form is used to create database user connection. All fields must be filled for the form to be submitted.', 
                'form':create_database_user_connection_form, 
                'format':{'Create database user connection Form': 
                    {'user_connection':'user id', 
                    'connection_to_db':'database_connection id',
                    'db_username':'username for this db connection',
                    'db_password':'password for this db and username',}}},]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_database_user_connection_data = data['Create database user connection Form']
        if all(key in new_database_user_connection_data for key in ['user_connection', 'connection_to_db', 'db_username', 'db_password']):
            try:
                user_connection_user = User.objects.get(username = new_database_user_connection_data['user_connection'])
                user_connection = user_info.objects.get(user = user_connection_user.id)
                new_database_user_connection_data['user_connection'] = user_connection
            except:
                pass

            try:
                connection_to_db = database_connection.objects.get(id = new_database_user_connection_data['connection_to_db'])
                new_database_user_connection_data['connection_to_db'] = connection_to_db
            except:
                pass

            create_database_user_connection_form = create_database_user_connection(new_database_user_connection_data, user=request.user)
            if create_database_user_connection_form.is_valid():
                new_database_user_connection = create_database_user_connection_form.save(commit=False)
                new_database_user_connection.created_date = timezone.now()
                new_database_user_connection.save()
                data = {'message':'new database user connection has been created.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_database_user_connection_form.errors}
        
        data = {'message':'An error has occured, please ensure your request follows the format below.',
                'format':{'Create database user connection Form': 
                    {'user_connection':'user id', 
                    'connection_to_db':'database_connection id',
                    'db_username':'username for this db connection',
                    'db_password':'password for this db and username',}}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_database_user_connection(request, database_user_connection_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if database_user_connection.objects.filter(id=database_user_connection_id).exists():
            database_user_connection_to_delete = database_user_connection.objects.get(id=database_user_connection_id)
            database_user_connection_to_delete.delete()
            
        data = {'message':'database_user_connection deleted'}
        return redirect('/synapse/')



class manage_datatable_connection(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_datatable_connection_form = create_datatable_connection(request.GET or None, user=request.user)
        context = {'create_datatable_connection_form':create_datatable_connection_form}
        return render(request, 'synapse/create_datatable_connection.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_datatable_connection_form = create_datatable_connection(request.POST or None, user=request.user)
        if create_datatable_connection_form.is_valid():
            new_datatable_connection = create_datatable_connection_form.save(commit=False)
            new_datatable_connection.created_date = timezone.now()
            new_datatable_connection.datatable_name = re.sub(r'[^a-zA-Z0-9_]', '', new_datatable_connection.datatable_name.replace(" ", "_"))
            new_datatable_connection.save()

            new_con_func = connection_functions.objects.create(
            connection_function_name=new_datatable_connection.datatable_name,
            function_type='data',
            function_extension='x',
            function_input_values_schema='x',
            connection_to_datable = new_datatable_connection)
            
            test_get_connection = get_connection_data(new_con_func)
            if test_get_connection['status'] == '1':
                temp_data = test_get_connection['temp_data']
                cols_list = temp_data.columns

                list_of_forms = []
                for i_col, e_col in enumerate(cols_list):
                    temp_form = create_datatable_dictionary(prefix=f'{i_col}', initial={
                        'data_connection_function':new_con_func,
                        'data_value_column':e_col,
                        'dictionary_table_key':e_col,}, user=request.user)
                    list_of_forms.append(temp_form)
                    
                context = {'list_of_forms':list_of_forms}
                new_con_func.save()
                return render(request, 'synapse/create_multiple_dictionary_keys.html', context)
            
            context = {'new_datatable_connection':new_datatable_connection}
### update redirect
            return redirect('/synapse/')
        else:
            
            context = {'create_datatable_connection_form':create_datatable_connection_form}
            return render(request, 'synapse/create_datatable_connection.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_datatable_connection_form = create_datatable_connection(user=request.user)
        create_datatable_connection_form = form_to_json_schema(create_datatable_connection_form)
        json_form = {'message':'This form is used to create a new project, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
            'items':[{'name': 'Create datatable connection Form', 
                'description':'This form is used to create datatable connection. All fields must be filled for the form to be submitted.', 
                'form':create_datatable_connection_form, 
                'format':{'Create datatable connection Form': 
                    {'user_db_connection':'database_user_connection id', 
                    'datatable_name':'table name',
                    'databale_type':'see list in form.' }}},]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_datatable_connection_data = data['Create datatable connection Form']
        if all(key in new_datatable_connection_data for key in ['user_db_connection', 'datatable_name', 'databale_type']):
            create_datatable_connection_form = create_datatable_connection(new_datatable_connection_data, user=request.user)
            try:
                user_db_connection = database_user_connection.objects.get(id = new_datatable_connection_data['user_db_connection'])
                new_datatable_connection_data['user_db_connection'] = user_db_connection
            except:
                pass

            if create_datatable_connection_form.is_valid():
                new_datatable_connection = create_datatable_connection_form.save(commit=False)
                new_datatable_connection.created_date = timezone.now()
                new_datatable_connection.save()
                
                new_con_func = connection_functions.objects.create(
                connection_function_name=new_datatable_connection.datatable_name,
                function_type='data',
                function_extension='x',
                function_input_values_schema='x',
                connection_to_datable = new_datatable_connection)
                
                test_get_connection = get_connection_data(new_con_func)
                if test_get_connection['status'] == '1':
                    temp_data = test_get_connection['temp_data']
                    cols_list = temp_data.columns

                    list_of_forms = []
                    for i_col, e_col in enumerate(cols_list):
                        temp_form = create_datatable_dictionary(prefix=f'{i_col}', initial={
                            'data_connection_function':new_con_func,
                            'data_value_column':e_col,
                            'dictionary_table_key':e_col,}, user=request.user)
                        list_of_forms.append(temp_form)
                        
                    context = {'list_of_forms':list_of_forms}
                    new_con_func.save()

                data = {'message':'new datatable connection has been created.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_datatable_connection_form.errors}
        
        data = {'message':'An error has occured, please ensure your request follows the format below.',
                'format':{'Create datatable connection Form': 
                    {'user_db_connection':'database_user_connection id', 
                    'datatable_name':'table name',
                    'databale_type':'see list in form.' }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_datatable_connection(request, datatable_connection_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if datatable_connection.objects.filter(id=datatable_connection_id).exists():
            datatable_connection_to_delete = datatable_connection.objects.get(id=datatable_connection_id)
            datatable_connection_to_delete.delete()
            
        data = {'message':'datatable_connection deleted'}
        return redirect('/synapse/')



class manage_api_connection(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_api_connection_form = create_api_connection(request.GET or None, user=request.user)
        context = {'create_api_connection_form':create_api_connection_form}
        return render(request, 'synapse/create_api_connection.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_api_connection_form = create_api_connection(request.POST or None, user=request.user)
        if create_api_connection_form.is_valid():
            new_api_connection = create_api_connection_form.save(commit=False)
            new_api_connection.created_date = timezone.now()
            new_api_connection.save()
            context = {'new_api_connection':new_api_connection}
### update redirect
            return redirect('/synapse/add_connection_functions')
        else:
            
            context = {'create_api_connection_form':create_api_connection_form}
            return render(request, 'synapse/create_api_connection.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_api_connection_form = create_api_connection(user=request.user)
        create_api_connection_form = form_to_json_schema(create_api_connection_form)
        json_form = {'message':'This form is used to create a new project, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
            'items':[{'name': 'Create api connection Form', 
                'description':'This form is used to create api connection. All fields must be filled for the form to be submitted.', 
                'form':create_api_connection_form, 
                'format':{'Create api connection Form': 
                    {'user_connection':'user username', 
                    'api_base_url':'api base url',
                    'api_username':'api usernmae',
                    '_api_password':'api password; only give password or key, not both;',
                    '_api_key':'api key; only give key or password, not both;' }}},]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_api_connection_data = data['Create api connection Form']
        if all(key in new_api_connection_data for key in ['user_connection', 'api_base_url']):
            try:
                user_connection_user = User.objects.get(username = new_api_connection_data['user_connection'])
                user_connection = user_info.objects.get(user = user_connection_user.id)
                new_api_connection_data['user_connection'] = user_connection
            except:
                pass

            create_api_connection_form = create_api_connection(new_api_connection_data, user=request.user)
            if create_api_connection_form.is_valid():
                new_api_connection = create_api_connection_form.save(commit=False)
                new_api_connection.created_date = timezone.now()
                new_api_connection.save()
                data = {'message':'new api connection has been created.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_api_connection_form.errors}
        
        data = {'message':'An error has occured, please ensure your request follows the format below.',
                'format':{'Create api connection Form': 
                    {'user_connection':'user username', 
                    'api_base_url':'api base url',
                    'api_username':'api usernmae',
                    '_api_password':'api password; only give password or key, not both;',
                    '_api_key':'api key; only give key or password, not both;' }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_api_connection(request, api_connection_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if api_connection.objects.filter(id=api_connection_id).exists():
            api_connection_to_delete = api_connection.objects.get(id=api_connection_id)
            api_connection_to_delete.delete()
            
        data = {'message':'api_connection deleted'}
        return redirect('/synapse/')



class manage_connection_functions(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_connection_functions_form = create_connection_functions(request.GET or None, user=request.user)
        context = {'create_connection_functions_form':create_connection_functions_form}
        return render(request, 'synapse/create_connection_functions.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_connection_functions_form = create_connection_functions(request.POST or None, user=request.user)
        if create_connection_functions_form.is_valid():
            new_connection_functions = create_connection_functions_form.save(commit=False)
            new_connection_functions.created_date = timezone.now()
            context = {'new_connection_functions':new_connection_functions}

            if new_connection_functions.function_type == "data" or new_connection_functions.function_type == "mapping":
                test_get_connection = get_connection_data(new_connection_functions)
                if test_get_connection['status'] == '1':
                    temp_data = test_get_connection['temp_data']
                    cols_list = temp_data.columns

                    list_of_forms = []
                    for i_col, e_col in enumerate(cols_list):
                        temp_form = create_datatable_dictionary(prefix=f'{i_col}', initial={
                            'data_connection_function':new_connection_functions,
                            'data_value_column':e_col,
                            'dictionary_table_key':e_col,}, user=request.user)
                        list_of_forms.append(temp_form)
                        
                    context['list_of_forms'] = list_of_forms
                    new_connection_functions.save()
                    return render(request, 'synapse/create_multiple_dictionary_keys.html', context)

                else:
                    context = {'create_connection_functions_form':create_connection_functions_form}
                    context['message'] = test_get_connection['message']
                    return render(request, 'synapse/create_connection_functions.html', context)

### update redirect
            else:
                new_connection_functions.save()
                return redirect('/synapse/')
        else:
            context = {'create_connection_functions_form':create_connection_functions_form}
            return render(request, 'synapse/create_connection_functions.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_connection_functions_form = create_connection_functions(user=request.user)
        create_connection_functions_form = form_to_json_schema(create_connection_functions_form)
        json_form = {'message':'This form is used to create a new project, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
            'items':[{'name': 'Create connection functions Form', 
                'description':'This form is used to create connection functions. All fields must be filled for the form to be submitted.', 
                'form':create_connection_functions_form, 
                'format':{'Create connection functions Form': 
                    {'function_type':'see list in form', 
                    'function_extension':'function extension',
                    'function_input_values_schema':'shcema of expected input',
                    'function_output_type':'shcema of expected output', }}},]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_connection_functions_data = data['Create connection functions Form']
        if all(key in new_connection_functions_data for key in ['function_type', 'function_extension', 'function_input_values_schema']):
            try:
                connection_to_datable = datatable_connection.objects.get(id = new_connection_functions_data['connection_to_datable'])
                new_connection_functions_data['connection_to_datable'] = connection_to_datable
            except:
                pass
            try:
                connection_to_api = api_connection.objects.get(id = new_connection_functions_data['connection_to_api'])
                new_connection_functions_data['connection_to_api'] = connection_to_api
            except:
                pass
            

            create_connection_functions_form = create_connection_functions(new_connection_functions_data, user=request.user)
            if create_connection_functions_form.is_valid():
                new_connection_functions = create_connection_functions_form.save(commit=False)
                new_connection_functions.created_date = timezone.now()
                if new_connection_functions.function_type == "data" or new_connection_functions.function_type == "mapping":
                    test_get_connection = get_connection_data(new_connection_functions)
                    if test_get_connection['status'] == '1':
                        new_connection_functions.save()
                        data = {'message':'new data connection functions has been created.'}
                        return JsonResponse(data)
                    else:
                        data = {'message':test_get_connection['message'],
                                'format':{'Create connection functions Form': 
                                    {'function_type':'see list in form', 
                                    'function_extension':'function extension',
                                    'function_input_values_schema':'shcema of expected input',
                                    'function_output_type':'shcema of expected output', }}}
                        return JsonResponse(data)
                else:
                    new_connection_functions.save()
                    data = {'message':'new connection functions has been created.'}
                    return JsonResponse(data)
            else:
                context = {'errors':create_connection_functions_form.errors}
        
        data = {'message':'An error has occured, please ensure your request follows the format below.',
                'format':{'Create connection functions Form': 
                    {'function_type':'see list in form', 
                    'function_extension':'function extension',
                    'function_input_values_schema':'shcema of expected input',
                    'function_output_type':'shcema of expected output', }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_connection_functions(request, connection_functions_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if connection_functions.objects.filter(id=connection_functions_id).exists():
            connection_functions_to_delete = connection_functions.objects.get(id=connection_functions_id)
            connection_functions_to_delete.delete()
            
        data = {'message':'connection_functions deleted'}
        return redirect('/synapse/')

class manage_datatable_groups(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_datatable_groups_form = create_datatable_groups(request.GET or None)
        context = {'create_datatable_groups_form':create_datatable_groups_form}
        return render(request, 'synapse/create_datatable_groups.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_datatable_groups_form = create_datatable_groups(request.POST or None)
        if create_datatable_groups_form.is_valid():
            new_datatable_groups = create_datatable_groups_form.save(commit=False)
            new_datatable_groups.created_date = timezone.now()
            new_datatable_groups.save()
            context = {'new_datatable_groups':new_datatable_groups}
### update redirect
            return redirect('/synapse/add_dictionary_keys')
        else:
            
            context = {'create_datatable_groups_form':create_datatable_groups_form}
            return render(request, 'synapse/create_datatable_groups.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_datatable_groups_form = create_datatable_groups()
        create_datatable_groups_form = form_to_json_schema(create_datatable_groups_form)
        json_form = {'message':'This form is used to create a new project, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
            'items':[{'name': 'Create datatable groups Form', 
                'description':'This form is used to create datatable groups. All fields must be filled for the form to be submitted.', 
                'form':create_datatable_groups_form, 
                'format':{'Create datatable groups Form': 
                    {'datatable_group':'datatable group',}}},]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_datatable_groups_data = data['Create datatable groups Form']
        if all(key in new_datatable_groups_data for key in ['datatable_group',]):
            create_datatable_groups_form = create_datatable_groups(new_datatable_groups_data)
            if create_datatable_groups_form.is_valid():
                new_datatable_groups = create_datatable_groups_form.save(commit=False)
                new_datatable_groups.created_date = timezone.now()
                new_datatable_groups.save()
                data = {'message':'new datatable groups has been created.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_datatable_groups_form.errors}
        
        data = {'message':'An error has occured, please ensure your request follows the format below.',
                'format':{'Create datatable groups Form': 
                    {'datatable_group':'datatable group',}}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_datatable_groups(request, datatable_groups_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if datatable_groups.objects.filter(id=datatable_groups_id).exists():
            datatable_groups_to_delete = datatable_groups.objects.get(id=datatable_groups_id)
            datatable_groups_to_delete.delete()
            
        data = {'message':'datatable_groups deleted'}
        return redirect('/synapse/')

class manage_dictionary_keys(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_dictionary_keys_form = create_dictionary_keys(request.GET or None)
        context = {'create_dictionary_keys_form':create_dictionary_keys_form}
        return render(request, 'synapse/create_dictionary_keys.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_dictionary_keys_form = create_dictionary_keys(request.POST or None)
        if create_dictionary_keys_form.is_valid():
            new_dictionary_keys = create_dictionary_keys_form.save(commit=False)
            new_dictionary_keys.created_date = timezone.now()
            new_dictionary_keys.save()
            context = {'new_dictionary_keys':new_dictionary_keys}
### update redirect
            return redirect('/synapse/')
        else:
            
            context = {'create_dictionary_keys_form':create_dictionary_keys_form}
            return render(request, 'synapse/create_connection_functions.html', context)
    
    def multiple_dictionary_keys(request):
        if check_authentication(request) != None:
            return check_authentication(request)
        request_raw = request.POST
        prefix_list = [key.replace('-data_type', '') for key in request_raw.keys() if 'data_type' in key]
        
        forms = []
        for form_prefix in prefix_list:
            get_data_connection = connection_functions.objects.get(id=request_raw[f'{form_prefix}-data_connection_function'])
            temp_form = create_datatable_dictionary({
                'data_type': request_raw[f'{form_prefix}-data_type'],
                'dictionary_key': request_raw[f'{form_prefix}-dictionary_key'],
                'dictionary_table_key': request_raw[f'{form_prefix}-dictionary_table_key'],
                'data_value_column': request_raw[f'{form_prefix}-data_value_column'],
                'data_connection_function': get_data_connection,}, user=request.user)
            
            if temp_form.is_valid():
                forms.append(temp_form)
        
        if all(form.is_valid() for form in forms):
            for form in forms:
                form.save() 
        
        return redirect('/synapse/')

    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_dictionary_keys_form = create_dictionary_keys()
        create_dictionary_keys_form = form_to_json_schema(create_dictionary_keys_form)
        json_form = {'message':'This form is used to create a new project, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
            'items':[{'name': 'Create dictionary keys Form', 
                'description':'This form is used to create dictionary keys. All fields must be filled for the form to be submitted.', 
                'form':create_dictionary_keys_form, 
                'format':{'Create dictionary keys Form': 
                    {'datatable_group':'datatable_groups id', 
                    'unique_key':'unique dict key',
                    'unique_key_desc':'description of key' }}},]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_dictionary_keys_data = data['Create dictionary keys Form']
        if all(key in new_dictionary_keys_data for key in ['unique_key', 'unique_key_desc']):
            try:
                datatable_group = datatable_groups.objects.get(id = new_dictionary_keys_data['datatable_group'])
                new_dictionary_keys_data['datatable_group'] = datatable_group
            except:
                pass

            create_dictionary_keys_form = create_dictionary_keys(new_dictionary_keys_data)
            if create_dictionary_keys_form.is_valid():
                new_dictionary_keys = create_dictionary_keys_form.save(commit=False)
                new_dictionary_keys.created_date = timezone.now()
                new_dictionary_keys.save()
                data = {'message':'new dictionary keys has been created.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_dictionary_keys_form.errors}
        
        data = {'message':'An error has occured, please ensure your request follows the format below.',
                'format':{'Create dictionary keys Form': 
                    {'datatable_group':'datatable_groups id', 
                    'unique_key':'unique dict key',
                    'unique_key_desc':'description of key' }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_dictionary_keys(request, dictionary_keys_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if dictionary_keys.objects.filter(id=dictionary_keys_id).exists():
            dictionary_keys_to_delete = dictionary_keys.objects.get(id=dictionary_keys_id)
            dictionary_keys_to_delete.delete()
            
        data = {'message':'dictionary_keys deleted'}
        return redirect('/synapse/')

class manage_datatable_dictionary(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_datatable_dictionary_form = create_datatable_dictionary(request.GET or None, user=request.user)
        context = {'create_datatable_dictionary_form':create_datatable_dictionary_form}
        return render(request, 'synapse/create_datatable_dictionary.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_datatable_dictionary_form = create_datatable_dictionary(request.POST or None, user=request.user)
        if create_datatable_dictionary_form.is_valid():
            new_datatable_dictionary = create_datatable_dictionary_form.save(commit=False)
            new_datatable_dictionary.created_date = timezone.now()
            new_datatable_dictionary.save()
            context = {'new_datatable_dictionary':new_datatable_dictionary}
### update redirect
            return redirect('/synapse/')
        else:
            
            context = {'create_datatable_dictionary_form':create_datatable_dictionary_form}
            return render(request, 'synapse/create_datatable_dictionary.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_datatable_dictionary_form = create_datatable_dictionary(user=request.user)
        create_datatable_dictionary_form = form_to_json_schema(create_datatable_dictionary_form)
        json_form = {'message':'This form is used to create a new project, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
            'items':[{'name': 'Create datatable dictionary Form', 
                'description':'This form is used to create datatable dictionary. All fields must be filled for the form to be submitted.', 
                'form':create_datatable_dictionary_form, 
                'format':{'Create datatable dictionary Form': 
                    {'data_dict_grouping':'datatable_groups id', 
                     'data_type':'see list in form', 
                     'dictionary_key':'dictionary_keys id', 
                     'data_value_column':'name of data value column', 
                     'data_connection_function':'connection_functions id',}}},]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_datatable_dictionary_data = data['Create datatable dictionary Form']
        if all(key in new_datatable_dictionary_data for key in ['data_type', 'data_value_column', 'data_connection_function']):
            create_datatable_dictionary_form = create_datatable_dictionary(new_datatable_dictionary_data, user=request.user)
            try:
                data_dict_grouping = datatable_groups.objects.get(id = new_datatable_dictionary_data['data_dict_grouping'])
                new_datatable_dictionary_data['data_dict_grouping'] = data_dict_grouping
            except:
                pass
            try:
                dictionary_key = dictionary_keys.objects.get(id = new_datatable_dictionary_data['dictionary_key'])
                new_datatable_dictionary_data['dictionary_key'] = dictionary_key
            except:
                pass
            try:
                data_connection_function = connection_functions.objects.get(id = new_datatable_dictionary_data['data_connection_function'])
                new_datatable_dictionary_data['data_connection_function'] = data_connection_function
            except:
                pass

            if create_datatable_dictionary_form.is_valid():
                new_datatable_dictionary = create_datatable_dictionary_form.save(commit=False)
                new_datatable_dictionary.created_date = timezone.now()
                new_datatable_dictionary.save()
                data = {'message':'new datatable dictionary has been created.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_datatable_dictionary_form.errors}
        
        data = {'message':'An error has occured, please ensure your request follows the format below.',
                'format':{'Create datatable dictionary Form': 
                    {'data_dict_grouping':'datatable_groups id', 
                     'data_type':'see list in form', 
                     'dictionary_key':'dictionary_keys id', 
                     'data_value_column':'name of data value column', 
                     'data_connection_function':'connection_functions id',}}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_datatable_dictionary(request, datatable_dictionary_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if datatable_dictionary.objects.filter(id=datatable_dictionary_id).exists():
            datatable_dictionary_to_delete = datatable_dictionary.objects.get(id=datatable_dictionary_id)
            datatable_dictionary_to_delete.delete()
            
        data = {'message':'datatable_dictionary deleted'}
        return redirect('/synapse/')



class manage_local_data_files(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_local_data_files_form = create_local_data_files(request.GET or None, user=request.user)
        context = {'create_local_data_files_form':create_local_data_files_form}
        return render(request, 'synapse/create_local_data_files.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_local_data_files_form = create_local_data_files(request.POST or None, user=request.user)
        if create_local_data_files_form.is_valid():
            new_local_data_files = create_local_data_files_form.save(commit=False)
            new_local_data_files.created_date = timezone.now()
            temp_dt = local_file_to_db(request, new_local_data_files)
            context = {}
            if temp_dt['status'] == '1':
                temp_dt_ob = connection_functions.objects.get(connection_function_name=temp_dt['db_table_name'])
                test_get_connection = get_connection_data(temp_dt_ob)
                if test_get_connection['status'] == '1':
                    temp_data = test_get_connection['temp_data']
                    cols_list = temp_data.columns

                    list_of_forms = []
                    for i_col, e_col in enumerate(cols_list):
                        temp_form = create_datatable_dictionary(prefix=f'{i_col}', initial={
                            'data_connection_function':temp_dt_ob,
                            'data_value_column':e_col,
                            'dictionary_table_key':e_col,}, user=request.user)
                        list_of_forms.append(temp_form)
                        
                    context['list_of_forms'] = list_of_forms
                    temp_dt_ob.save()
                    return render(request, 'synapse/create_multiple_dictionary_keys.html', context)

                else:
                    context['create_local_data_files_form']=create_local_data_files_form
                    context['message'] = test_get_connection['message']
                    return render(request, 'synapse/create_local_data_files.html', context)
            else:
                context['create_local_data_files_form']=create_local_data_files_form
                context['message'] = temp_dt['message']
                return render(request, 'synapse/create_local_data_files.html', context)

### update redirect
            #return redirect('/synapse/')
        else:
            
            context = {'create_local_data_files_form':create_local_data_files_form}
            return render(request, 'synapse/create_local_data_files.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_local_data_files_form = create_local_data_files(user=request.user)
        create_local_data_files_form = form_to_json_schema(create_local_data_files_form)
        json_form = {'message':'This form is used to create a new project, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
            'items':[{'name': 'Create local data files Form', 
                'description':'This form is used to create local data files. All fields must be filled for the form to be submitted.', 
                'form':create_local_data_files_form, 
                'format':{'Create local data files Form': 
                    {'local_file_type':'see list in form', 
                    'local_file_path':'path to files',
                    'local_file_path_old':'path to old files',
                    'local_file_name':'file name',
                    'local_file_sheet':'data sheet',
                    'local_file_header':'data header line' }}},]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_local_data_files_data = data['Create local data files Form']
        if all(key in new_local_data_files_data for key in ['local_file_type', 'local_file_path', 'local_file_name',]):
            create_local_data_files_form = create_local_data_files(new_local_data_files_data, user=request.user)
            if create_local_data_files_form.is_valid():
                new_local_data_files = create_local_data_files_form.save(commit=False)
                new_local_data_files.created_date = timezone.now()
                new_local_data_files.save()
                data = {'message':'new local data files has been created.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_local_data_files_form.errors}
        
        data = {'message':'An error has occured, please ensure your request follows the format below.',
                'format':{'Create local data files Form': 
                    {'local_file_type':'see list in form', 
                    'local_file_path':'path to files',
                    'local_file_path_old':'path to old files',
                    'local_file_name':'file name',
                    'local_file_sheet':'data sheet',
                    'local_file_header':'data header line' }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_local_data_files(request, local_data_files_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if local_data_files.objects.filter(id=local_data_files_id).exists():
            local_data_files_to_delete = local_data_files.objects.get(id=local_data_files_id)
            local_data_files_to_delete.delete()
            
        data = {'message':'local_data_files deleted'}
        return redirect('/synapse/')



class manage_local_function_files(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_local_function_files_form = create_local_function_files(request.GET or None, user=request.user)
        context = {'create_local_function_files_form':create_local_function_files_form}
        return render(request, 'synapse/create_local_function_files.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_local_function_files_form = create_local_function_files(request.POST or None, user=request.user)
        if create_local_function_files_form.is_valid():
            new_local_function_files = create_local_function_files_form.save(commit=False)
            new_local_function_files.created_date = timezone.now()
            new_local_function_files.save()
            context = {'new_local_function_files':new_local_function_files}
### update redirect
            return redirect('/synapse/')
        else:
            
            context = {'create_local_function_files_form':create_local_function_files_form}
            return render(request, 'synapse/create_local_function_files.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_local_function_files_form = create_local_function_files(user=request.user)
        create_local_function_files_form = form_to_json_schema(create_local_function_files_form)
        json_form = {'message':'This form is used to create a new project, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
            'items':[{'name': 'Create local function files Form', 
                'description':'This form is used to create local function files. All fields must be filled for the form to be submitted.', 
                'form':create_local_function_files_form, 
                'format':{'Create local function files Form': 
                    {'local_function_type':'see list in form', 
                    'local_function_path':'path to function file',
                    'local_function_name':'function name',
                    'function_input_values_schema':'expected input values and schema'}}},]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_local_function_files_data = data['Create local function files Form']
        if all(key in new_local_function_files_data for key in ['local_function_type', 'local_function_path', 'local_function_name']):
            create_local_function_files_form = create_local_function_files(new_local_function_files_data, user=request.user)
            if create_local_function_files_form.is_valid():
                new_local_function_files = create_local_function_files_form.save(commit=False)
                new_local_function_files.created_date = timezone.now()
                new_local_function_files.save()
                data = {'message':'new local function files has been created.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_local_function_files_form.errors}
        
        data = {'message':'An error has occured, please ensure your request follows the format below.',
                'format':{'Create local function files Form': 
                    {'local_function_type':'see list in form', 
                    'local_function_path':'path to function file',
                    'local_function_name':'function name',
                    'function_input_values_schema':'expected input values and schema'}}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_local_function_files(request, local_function_files_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if local_function_files.objects.filter(id=local_function_files_id).exists():
            local_function_files_to_delete = local_function_files.objects.get(id=local_function_files_id)
            local_function_files_to_delete.delete()
            
        data = {'message':'local_function_files deleted'}
        return redirect('/synapse/')



class manage_connection_function_saved_inputs(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_connection_function_saved_inputs_form = create_connection_function_saved_inputs(request.GET or None, user=request.user)
        context = {'create_connection_function_saved_inputs_form':create_connection_function_saved_inputs_form}
        return render(request, 'synapse/create_connection_function_saved_inputs.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_connection_function_saved_inputs_form = create_connection_function_saved_inputs(request.POST or None, user=request.user)
        if create_connection_function_saved_inputs_form.is_valid():
            new_connection_function_saved_inputs = create_connection_function_saved_inputs_form.save(commit=False)
            new_connection_function_saved_inputs.created_date = timezone.now()
            new_connection_function_saved_inputs.save()
            context = {'new_connection_function_saved_inputs':new_connection_function_saved_inputs}
### update redirect
            #return redirect('/synapse/add_input_value_to_connections_function')
            create_input_value_to_connections_function_form = create_input_value_to_connections_function(initial={'input_value':new_connection_function_saved_inputs}, user=request.user)
            context = {'create_input_value_to_connections_function_form':create_input_value_to_connections_function_form}
            return render(request, 'synapse/create_input_value_to_connections_function.html', context)
        else:
            
            context = {'create_connection_function_saved_inputs_form':create_connection_function_saved_inputs_form}
            return render(request, 'synapse/create_connection_function_saved_inputs.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_connection_function_saved_inputs_form = create_connection_function_saved_inputs(user=request.user)
        create_connection_function_saved_inputs_form = form_to_json_schema(create_connection_function_saved_inputs_form)
        json_form = {'message':'This form is used to create a new project, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
            'items':[{'name': 'Create connection function saved inputs Form', 
                'description':'This form is used to create connection function saved inputs. All fields must be filled for the form to be submitted.', 
                'form':create_connection_function_saved_inputs_form, 
                'format':{'Create connection function saved inputs Form': 
                    {'local_function_type':'see list in form', 
                    'local_function_path':'path to function file',
                    'local_function_name':'function name',
                    'function_input_values_schema':'expected input values and schema'}}},]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_connection_function_saved_inputs_data = data['Create connection function saved inputs Form']
        if all(key in new_connection_function_saved_inputs_data for key in ['local_function_type', 'local_function_path', 'local_function_name']):
            create_connection_function_saved_inputs_form = create_connection_function_saved_inputs(new_connection_function_saved_inputs_data, user=request.user)
            if create_connection_function_saved_inputs_form.is_valid():
                new_connection_function_saved_inputs = create_connection_function_saved_inputs_form.save(commit=False)
                new_connection_function_saved_inputs.created_date = timezone.now()
                new_connection_function_saved_inputs.save()
                data = {'message':'new connection function saved inputs has been created.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_connection_function_saved_inputs_form.errors}
        
        data = {'message':'An error has occured, please ensure your request follows the format below.',
                'format':{'Create connection function saved inputs Form': 
                    {'local_function_type':'see list in form', 
                    'local_function_path':'path to function file',
                    'local_function_name':'function name',
                    'function_input_values_schema':'expected input values and schema'}}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_connection_function_saved_inputs(request, connection_function_saved_inputs_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if connection_function_saved_inputs.objects.filter(id=connection_function_saved_inputs_id).exists():
            connection_function_saved_inputs_to_delete = connection_function_saved_inputs.objects.get(id=connection_function_saved_inputs_id)
            connection_function_saved_inputs_to_delete.delete()
            
        data = {'message':'connection_function_saved_inputs deleted'}
        return redirect('/synapse/')


class manage_input_value_to_connections_function(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_input_value_to_connections_function_form = create_input_value_to_connections_function(request.GET or None, user=request.user)
        context = {'create_input_value_to_connections_function_form':create_input_value_to_connections_function_form}
        return render(request, 'synapse/create_input_value_to_connections_function.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_input_value_to_connections_function_form = create_input_value_to_connections_function(request.POST or None, user=request.user)
        if create_input_value_to_connections_function_form.is_valid():
            new_input_value_to_connections_function = create_input_value_to_connections_function_form.save(commit=False)
            new_input_value_to_connections_function.created_date = timezone.now()
            new_input_value_to_connections_function.save()
            context = {'new_input_value_to_connections_function':new_input_value_to_connections_function}
### update redirect
            return redirect('/synapse/')
        else:
            
            context = {'create_input_value_to_connections_function_form':create_input_value_to_connections_function_form}
            return render(request, 'synapse/create_input_value_to_connections_function.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_input_value_to_connections_function_form = create_input_value_to_connections_function(user=request.user)
        create_input_value_to_connections_function_form = form_to_json_schema(create_input_value_to_connections_function_form)
        json_form = {'message':'This form is used to create a new project, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
            'items':[{'name': 'Create input value to connections function Form', 
                'description':'This form is used to create input value to connections function. All fields must be filled for the form to be submitted.', 
                'form':create_input_value_to_connections_function_form, 
                'format':{'Create input value to connections function Form': 
                    {'local_function_type':'see list in form', 
                    'local_function_path':'path to function file',
                    'local_function_name':'function name',
                    'function_input_values_schema':'expected input values and schema'}}},]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_input_value_to_connections_function_data = data['Create input value to connections function Form']
        if all(key in new_input_value_to_connections_function_data for key in ['local_function_type', 'local_function_path', 'local_function_name']):
            create_input_value_to_connections_function_form = create_input_value_to_connections_function(new_input_value_to_connections_function_data, user=request.user)
            if create_input_value_to_connections_function_form.is_valid():
                new_input_value_to_connections_function = create_input_value_to_connections_function_form.save(commit=False)
                new_input_value_to_connections_function.created_date = timezone.now()
                new_input_value_to_connections_function.save()
                data = {'message':'new input value to connections function has been created.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_input_value_to_connections_function_form.errors}
        
        data = {'message':'An error has occured, please ensure your request follows the format below.',
                'format':{'Create input value to connections function Form': 
                    {'local_function_type':'see list in form', 
                    'local_function_path':'path to function file',
                    'local_function_name':'function name',
                    'function_input_values_schema':'expected input values and schema'}}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_input_value_to_connections_function(request, input_value_to_connections_function_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if input_value_to_connections_function.objects.filter(id=input_value_to_connections_function_id).exists():
            input_value_to_connections_function_to_delete = input_value_to_connections_function.objects.get(id=input_value_to_connections_function_id)
            input_value_to_connections_function_to_delete.delete()
            
        data = {'message':'input_value_to_connections_function deleted'}
        return redirect('/synapse/')


class DjangoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def to_json_string(data):
    return json.dumps(data, cls=DjangoJSONEncoder)

def safe_json_loads(val):
    try:
        return json.loads(val)
    except (ValueError, TypeError):
        dict_output = {str(val)}
        return  {}

class function_management_dashboard(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)
        context = {}
        temp_personality = model_personality.objects.get(id=7)
        context['add_axiom_bot_message_saved_input'] = add_axiom_bot_message_saved_input(initial={"bot_personality":temp_personality, "chat_user":request.user})
        context['add_axiom_bot_message_connection_func'] = add_axiom_bot_message_connection_func(initial={"bot_personality":temp_personality, "chat_user":request.user})
        request_user = User.objects.get(username=request.user)
        request_user = user_info.objects.get(user=request_user)

### get all connections
        user_database_connections = database_user_connection.objects.filter(user_connection=request_user)
        user_datatables = datatable_connection.objects.filter(user_db_connection__in=user_database_connections)
        user_api_connection = api_connection.objects.filter(user_connection=request_user)
        user_api_functions = connection_functions.objects.filter(connection_to_api__in=user_api_connection)
        user_datatable_functions = connection_functions.objects.filter(connection_to_datable__in=user_datatables)
        user_local_function = local_function_files.objects.all()
### bring them all together
        function_df = pd.DataFrame()
        if user_api_functions:
            user_api_functions_df = pd.DataFrame(user_api_functions.values())


            user_api_functions_df['function_type'] = 'api_function'
            function_df = pd.concat([user_api_functions_df, function_df])
        if user_datatable_functions:
            user_datatable_functions_df = pd.DataFrame(user_datatable_functions.values())


            user_datatable_functions_df['function_type'] = 'datatable_functions'
            function_df = pd.concat([user_datatable_functions_df, function_df])
        if user_local_function:
            user_local_function_df = pd.DataFrame(user_local_function.values())


            user_local_function_df['function_type'] = 'datatable_functions'
            function_df = pd.concat([user_local_function_df, function_df])
        
        if not function_df.empty:
            function_df['function_input_values_schema'] = function_df['function_input_values_schema'].str.replace("'", '"')
            function_df = function_df.replace({np.nan: None})
            function_df['function_input_values_schema'] = function_df['function_input_values_schema'].apply(safe_json_loads)

        function_list = []
        for index, function_row in function_df.iterrows():
            funtc_row_dict = {}
            funtc_row_dict['info'] = function_row

            if datatable_dictionary.objects.filter(data_connection_function=int(function_row['id'])).exists():
                temp_table_dict = datatable_dictionary.objects.filter(data_connection_function=int(function_row['id']))
                funtc_row_dict['table_dict'] = list(temp_table_dict.values())

                if connection_function_saved_inputs.objects.filter(input_mapping__in = temp_table_dict.values_list('dictionary_key_id', flat=True)):
                    temp_saved_input = connection_function_saved_inputs.objects.filter(input_mapping__in = temp_table_dict.values_list('dictionary_key_id', flat=True))
                    funtc_row_dict['saved_input'] = list(temp_saved_input.values())

            function_list.append(funtc_row_dict)
        context['function_list'] = function_list

        data_dictionary = datatable_groups.objects.all()
        data_dictionary_list = []
        for dt_group in data_dictionary:
            dt_group_dict = {}
            dt_group_dict['info'] = model_to_dict(dt_group)

            if dictionary_keys.objects.filter(datatable_group=dt_group.id).exists():
                temp_dict_keys = dictionary_keys.objects.filter(datatable_group=dt_group.id)
                dict_key_list = []
                for dict_key in temp_dict_keys:
                    dict_key_dict = {}
                    dict_key_dict['info'] = model_to_dict(dict_key)
                    temp_saved_input = connection_function_saved_inputs.objects.filter(input_mapping = int(dict_key.id))
                    dict_key_dict['saved_inputs'] = list(temp_saved_input.values())
                    dict_key_list.append(dict_key_dict)

            dt_group_dict['dict_key'] = dict_key_list
            data_dictionary_list.append(dt_group_dict)
        context['data_dictionary_list'] = data_dictionary_list

        """all_users_functions = user_api_functions | user_datatable_functions
        user_datable_keys_dict = datatable_dictionary.objects.filter(data_connection_function__in=all_users_functions)
        user_datable_keys_dict_df = pd.DataFrame(user_datable_keys_dict.values()).fillna(0)
        user_dict_keys = dictionary_keys.objects.select_related('datatable_group').all()
        if user_dict_keys.exists():
            user_dict_keys_df = pd.DataFrame(user_dict_keys.values('id', 'unique_key', 'unique_key_desc', 'datatable_group__datatable_group'))
            context['dictionary_keys'] = user_dict_keys_df.to_dict('records')
        else:
            user_dict_keys_df = pd.DataFrame(user_dict_keys.values('id', 'unique_key', 'unique_key_desc', 'datatable_group__datatable_group'))

        try:
            user_datable_keys_dict_df['dictionary_key_id'] = user_datable_keys_dict_df['dictionary_key_id'].astype(int)
            output_user_dict_key = pd.merge(user_datable_keys_dict_df, user_dict_keys_df, left_on='dictionary_key_id', right_on='id', how='left').fillna(0)
            output_user_dict_key = pd.merge(output_user_dict_key, pd.DataFrame(all_users_functions.values()), left_on='data_connection_function_id', right_on='id', how='left').fillna(0)
            for i in output_user_dict_key.columns:
                if '_id' in i:
                    output_user_dict_key[i] = output_user_dict_key[i].astype(int)
            context['output_user_dict_key'] = output_user_dict_key.to_dict('records')
        except:
            output_user_dict_key = pd.DataFrame()

        user_saved_inputs_connections = input_value_to_connections_function.objects.filter(input_connection_function__in=all_users_functions)
        user_saved_inputs = connection_function_saved_inputs.objects.filter(user_connection=request_user)

        user_saved_inputs_connections_df = pd.DataFrame(user_saved_inputs_connections.values())
        user_saved_inputs_df = pd.DataFrame(user_saved_inputs.values())

        try:
            output_user_saved_inputs = pd.merge(user_saved_inputs_connections_df, user_saved_inputs_df, left_on='input_value_id', right_on='id', how='left').fillna(0)
            output_user_saved_inputs = pd.merge(output_user_saved_inputs, pd.DataFrame(all_users_functions.values()), left_on='input_connection_function_id', right_on='id', how='left').fillna(0)

            for i in output_user_saved_inputs.columns:
                if '_id' in i:
                    output_user_saved_inputs[i] = output_user_saved_inputs[i].astype(int)

            output_user_saved_inputs['input_value'] = output_user_saved_inputs['input_value'].str.replace("'", '"')
            output_user_saved_inputs['input_value'] = output_user_saved_inputs['input_value'].apply(safe_json_loads)

            context['output_user_saved_inputs'] = output_user_saved_inputs.to_dict('records')
        except:
            output_user_saved_inputs = pd.DataFrame()
        
        function_df = pd.DataFrame()
        if user_api_functions:
            user_api_functions_df = pd.DataFrame(user_api_functions.values())
            user_api_functions_df['function_type'] = 'api_function'
            function_df = pd.concat([user_api_functions_df, function_df])
        if user_datatable_functions:
            user_datatable_functions_df = pd.DataFrame(user_datatable_functions.values())
            user_datatable_functions_df['function_type'] = 'datatable_functions'
            function_df = pd.concat([user_datatable_functions_df, function_df])
        if user_local_function:
            user_local_function_df = pd.DataFrame(user_local_function.values())
            user_local_function_df['function_type'] = 'datatable_functions'
            function_df = pd.concat([user_local_function_df, function_df])
        
        if not function_df.empty:
            function_df['function_input_values_schema'] = function_df['function_input_values_schema'].str.replace("'", '"')
            function_df = function_df.replace({np.nan: None})
            function_df['function_input_values_schema'] = function_df['function_input_values_schema'].apply(safe_json_loads)"""

        #print(function_df['function_input_values_schema'])
        context['function_df'] = function_df.to_dict('records')
        context['create_connection_functions_form'] = create_connection_functions(request.GET or None, user=request.user)
        context['create_local_function_files_form'] = create_local_function_files(request.GET or None, user=request.user)

        return render(request, 'synapse/function_management_dashboard copy.html', context)

    

    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)
        context = {}
        temp_personality = model_personality.objects.get(id=7)
        context['add_axiom_bot_message_saved_input'] = add_axiom_bot_message_saved_input(initial={"bot_personality":temp_personality, "chat_user":request.user})
        context['add_axiom_bot_message_connection_func'] = add_axiom_bot_message_connection_func(initial={"bot_personality":temp_personality, "chat_user":request.user})
        request_user = User.objects.get(username=request.user)
        request_user = user_info.objects.get(user=request_user)
        rq=request.POST

        temp_message_form_func = add_axiom_bot_message_connection_func(request.POST or None)
        context['add_axiom_bot_message_connection_func'] = temp_message_form_func
        temp_message_form = add_axiom_bot_message_saved_input(request.POST or None)
        context['add_axiom_bot_message_saved_input'] = temp_message_form
        if temp_message_form_func.is_valid():
            new_func_message_to_submit = temp_message_form_func.save(commit=False)
            temp_conn_func = new_func_message_to_submit.bot_function
            
            temp_model_connection  = model_connection.objects.get(id=2)
            temp_personality = model_personality.objects.get(id=8)
###  change personality
            user_prompt = "\\\\System Context: You are being observed on your performance. "\
            "Your objective is to check if the prompt provides enough information for you to fillout the input values in the form provide." \
            "The form will be a dictionary with keys and sample values, you will need to replace each template value with information from the prompt;" \
            "Remember, the form will come prefiled with an sample, you must replace that/those values with those from the user prompt as the response." \
            "Do not include anything but the newly completed form with the prompt information as the response." \
            "If the form does not have the necessary information to replace the each template value with information from the prompt," \
            "When necessary only, ask for the information you would need to replace the each template value with information from the prompt" \
            f"\\\\Form: {temp_conn_func.function_input_values_schema}"\
            f"\\\\ User Prompt: {new_func_message_to_submit.user_prompt}"
            
            temp_task = send_task_to_model(promt_message = user_prompt, user_request = request, 
                            personality = temp_personality, run_tempereature=temp_personality.personality_temp, top_p=temp_personality.personality_top_p,
                            chat_summary = "", chat_tool = new_func_message_to_submit.bot_tool, model_base = temp_model_connection.model_base, #model_con
                            model_name = temp_model_connection.model_name, model_api_key = temp_model_connection.model_api_key,) #model_con

            if temp_task.status == 0:
                context['task_response'] = markdown.markdown(temp_task.response)
            else:
                try:
                    temp_func_input = json.loads(temp_task.response)
                    output_dict = {}
                    for i in temp_func_input.keys():
                        output_dict[i] = temp_func_input[i]
                    
                    temp_output = get_connection_data_w_input(temp_conn_func, output_dict)
                    temp_summary = { "System Context": "This is the data that the user is asking you questions about; When answering user prompt questions use this information.",
                        temp_task.response: temp_output}

                    temp_task_2 = send_task_to_model(promt_message = new_func_message_to_submit.user_prompt, user_request = request, 
                            personality = temp_personality, run_tempereature=temp_personality.personality_temp, top_p=temp_personality.personality_top_p,
                            chat_summary = temp_summary, chat_tool = new_func_message_to_submit.bot_tool, model_base = temp_model_connection.model_base, #model_con
                            model_name = temp_model_connection.model_name, model_api_key = temp_model_connection.model_api_key,) #model_con
                    
                    context['task_response'] = markdown.markdown(temp_task_2.response)
                except:
                    context['task_response'] = markdown.markdown(temp_task.response)

        elif temp_message_form.is_valid():
            new_message_to_submit = temp_message_form.save(commit=False)
            temp_saved_input = new_message_to_submit.bot_saved_input
            temp_saved_input_func = input_value_to_connections_function.objects.filter(input_value=temp_saved_input)
            relevant_data = []
            for i_input_func, e_input_func in enumerate(temp_saved_input_func):
                function_to_run = e_input_func.input_connection_function
                temp_input_json = json.loads(temp_saved_input.input_value)
                if e_input_func.input_connection_function.function_type == "mapping":
                    output_dict = temp_input_json
                else:
                    output_dict = {f"__input__{list(temp_input_json.keys())[0]}__":temp_input_json[list(temp_input_json.keys())[0]]}
                
                temp_output_val = get_connection_data_w_input(function_to_run, output_dict)
                relevant_data.append({e_input_func.input_connection_function.connection_function_name: temp_output_val})
            
            temp_model_connection  = model_connection.objects.get(id=2)
            temp_personality = model_personality.objects.get(id=7)
            temp_task = send_task_to_model(promt_message = new_message_to_submit.user_prompt, user_request = request, 
                            personality = temp_personality, run_tempereature=temp_personality.personality_temp, top_p=temp_personality.personality_top_p,
                            chat_summary = relevant_data, chat_tool = new_message_to_submit.bot_tool, model_base = temp_model_connection.model_base, #model_con
                            model_name = temp_model_connection.model_name, model_api_key = temp_model_connection.model_api_key,)
            
            context['task_response'] = markdown.markdown(temp_task.response)

        else:
            if 'function_name' in rq.keys():
                        
                function_to_run = connection_functions.objects.get(connection_function_name=rq['function_name'])
                output_dict = {}
                for i in rq.keys():
                    if function_to_run.function_type == "mapping":
                        if i != 'csrfmiddlewaretoken' and i != "function_name":
                            output_dict[i.replace("__input__", "").replace("__", "")] = rq[i]
                    else:
                        if i in function_to_run.function_extension:
                            output_dict[i] = rq[i]

                temp_output = get_connection_data_w_input(function_to_run, output_dict)
                try:
                    temp_output['temp_data'] = temp_output['temp_data'].to_html()
                except:
                    temp_output['temp_data'] = temp_output['temp_data']

                context['temp_output'] = temp_output
                
            elif 'local_function_name' in rq.keys():
                if local_function_files.objects.filter(local_function_name=rq['local_function_name']).exists():
                    function_to_run = get_local_connection_data(rq)
                    context['temp_output'] = function_to_run.stdout


### get all connections
        user_database_connections = database_user_connection.objects.filter(user_connection=request_user)
        user_datatables = datatable_connection.objects.filter(user_db_connection__in=user_database_connections)
        user_api_connection = api_connection.objects.filter(user_connection=request_user)
        user_api_functions = connection_functions.objects.filter(connection_to_api__in=user_api_connection)
        user_datatable_functions = connection_functions.objects.filter(connection_to_datable__in=user_datatables)
        user_local_function = local_function_files.objects.all()
### bring them all together
        function_df = pd.DataFrame()
        if user_api_functions:
            user_api_functions_df = pd.DataFrame(user_api_functions.values())


            user_api_functions_df['function_type'] = 'api_function'
            function_df = pd.concat([user_api_functions_df, function_df])
        if user_datatable_functions:
            user_datatable_functions_df = pd.DataFrame(user_datatable_functions.values())


            user_datatable_functions_df['function_type'] = 'datatable_functions'
            function_df = pd.concat([user_datatable_functions_df, function_df])
        if user_local_function:
            user_local_function_df = pd.DataFrame(user_local_function.values())


            user_local_function_df['function_type'] = 'datatable_functions'
            function_df = pd.concat([user_local_function_df, function_df])
        
        if not function_df.empty:
            function_df['function_input_values_schema'] = function_df['function_input_values_schema'].str.replace("'", '"')
            function_df = function_df.replace({np.nan: None})
            function_df['function_input_values_schema'] = function_df['function_input_values_schema'].apply(safe_json_loads)

        function_list = []
        for index, function_row in function_df.iterrows():
            funtc_row_dict = {}
            funtc_row_dict['info'] = function_row

            if datatable_dictionary.objects.filter(data_connection_function=int(function_row['id'])).exists():
                temp_table_dict = datatable_dictionary.objects.filter(data_connection_function=int(function_row['id']))
                funtc_row_dict['table_dict'] = list(temp_table_dict.values())

                if connection_function_saved_inputs.objects.filter(input_mapping__in = temp_table_dict.values_list('dictionary_key_id', flat=True)):
                    temp_saved_input = connection_function_saved_inputs.objects.filter(input_mapping__in = temp_table_dict.values_list('dictionary_key_id', flat=True))
                    funtc_row_dict['saved_input'] = list(temp_saved_input.values())

            function_list.append(funtc_row_dict)
        context['function_list'] = function_list

        data_dictionary = datatable_groups.objects.all()
        data_dictionary_list = []
        for dt_group in data_dictionary:
            dt_group_dict = {}
            dt_group_dict['info'] = model_to_dict(dt_group)

            if dictionary_keys.objects.filter(datatable_group=dt_group.id).exists():
                temp_dict_keys = dictionary_keys.objects.filter(datatable_group=dt_group.id)
                dict_key_list = []
                for dict_key in temp_dict_keys:
                    dict_key_dict = {}
                    dict_key_dict['info'] = model_to_dict(dict_key)
                    temp_saved_input = connection_function_saved_inputs.objects.filter(input_mapping = int(dict_key.id))
                    dict_key_dict['saved_inputs'] = list(temp_saved_input.values())
                    dict_key_list.append(dict_key_dict)

            dt_group_dict['dict_key'] = dict_key_list
            data_dictionary_list.append(dt_group_dict)
        context['data_dictionary_list'] = data_dictionary_list
        
        context['function_df'] = function_df.to_dict('records')
        context['create_connection_functions_form'] = create_connection_functions(request.GET or None, user=request.user)
        context['create_local_function_files_form'] = create_local_function_files(request.GET or None, user=request.user)

        return render(request, 'synapse/function_management_dashboard copy.html', context)    