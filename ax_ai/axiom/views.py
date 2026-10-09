from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from django.contrib import messages
from django.forms.models import model_to_dict
from collections import defaultdict

from .models import *
from .forms import *
from bots.views import send_task_to_model, summarize_chat
from bots.models import *
from pm.mechanisms import apscheduler_functions
from pm.models import project, task
from synapse.models import connection_function_saved_inputs, input_value_to_connections_function
from .calendar_util import CustomGridCalendar

from quicksand.quicksand import quicksand
import re, os, markdown, json, shutil, subprocess, sys, importlib.util, time
import pandas as pd
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import List, Literal
from pydantic import BaseModel, Field
from itertools import zip_longest

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from django.conf import settings

def check_authentication(check_request):
    if not check_request.user.is_authenticated:
        return redirect("/login")

    
def check_files(request, ax_task):
    UPLOAD_FOLDER = r"axiom/task_attachements"

    print(request.FILES)

    if 'filename' not in request.FILES:
        return {'message':'no file',
                    'state':'0'}
    else:
        file_to_check = request.FILES['filename']
        print(file_to_check)
        file_content = file_to_check.read()
        qs = quicksand(file_content)
        qs.process()

        if not qs.results.get('exploits_found'):
            filename = re.sub(r'[<>:"/\\|?*\n\t\r\x00-\x1F]', '', file_to_check.name)
            with open(os.path.join(UPLOAD_FOLDER, filename), 'wb+') as destination:
                for chunk in file_to_check.chunks():
                    destination.write(chunk)
            
            new_task_attachemen = ax_task_attachement.objects.create(datetime_created=timezone.now(), 
                                                                     attachemnet_task=ax_task,
                                                                     attachemnet=str(os.path.join(UPLOAD_FOLDER, filename)))

            return {'message':'File saved',
                    'file_path': str(os.path.join(UPLOAD_FOLDER, filename)) ,
                    'state':'1'}
        
        
        return {'message':'Malicious file detected.',
                    'state':'0'}

def run_project_task(i_task, list_of_tasks_attach_dict, list_of_tasks_relationship_dict, project_to_build):
### check for task relationships; f2s relationships force output of second_task into task summary of main task
    context_task = {}
    if not i_task['model_response']:
        temp_chat_summary = ""
        temp_rel = [item for item in list_of_tasks_relationship_dict if item.get('main_task_id') == i_task['id']]
        prompt_prev_task = []
        for i_rel in temp_rel:
            if axiom_bot_message_task.objects.filter(id=i_rel['second_task_id']).exists():
                temp_second_task = axiom_bot_message_task.objects.get(id=i_rel['second_task_id'])
    ### add function to get all relevant tasks; add break to not run task if at least one f2s task has no response
                if i_rel['task_relationship'] == 'f2s':
                    if temp_second_task.model_response:
                        if len(temp_second_task.model_response) >= 2 and temp_second_task.model_response.startswith('[') and temp_second_task.model_response.endswith(']'):
                            cleaned_text = temp_second_task.model_response.strip()[1:-1]
                            output_list = [item.strip() for item in cleaned_text.split(",")]
                            
                            for task_item in output_list:
                                new_task_template = model_to_dict(axiom_bot_message_task.objects.get(id=i_task['id']), exclude=['id'])
                                new_task_template['user_prompt'] = task_item.replace("'", "")
                                new_task_template['task_type'] = "copy"
                                fk_fields = ['chat_user', 'bot_personality', 'bot_function', 'bot_saved_input', 'bot_local_function', "task_project"]  
                                for field in fk_fields:
                                    if field in new_task_template:
                                        new_task_template[f"{field}_id"] = new_task_template.pop(field)

                                create_copy_task = axiom_bot_message_task.objects.create(**new_task_template)
                                create_rel_task = []
                                if ax_task_prerequisite.objects.filter(second_task_id=i_task['id']).exists():
                                    temp_rel_list = ax_task_prerequisite.objects.get(second_task_id=i_task['id'])
                                    if temp_rel_list.task_relationship == "f2s":
                                        new_task_template = model_to_dict(axiom_bot_message_task.objects.get(id=temp_rel_list.main_task.id), exclude=['id'])
                                        new_task_template['task_type'] = "copy"
                                        fk_fields = ['chat_user', 'bot_personality', 'bot_function', 'bot_saved_input', 'bot_local_function', "task_project"]  
                                        for field in fk_fields:
                                            if field in new_task_template:
                                                new_task_template[f"{field}_id"] = new_task_template.pop(field)
    
                                        create_copy_of_rel_task = axiom_bot_message_task.objects.create(**new_task_template)
                                        create_task_rel = ax_task_prerequisite.objects.create(task_relationship="f2s", main_task=create_copy_of_rel_task, second_task=create_copy_task)
                                        
                                else:
                                    create_rel_task = None

                            parent_task = axiom_bot_message_task.objects.get(id=i_task['id'])
                            parent_task.model_response = "task copies created"
                            parent_task.save()
                            return run_project(project_to_build)

                        else:
                            print("temp_second_task")
                            prompt_prev_task.append(temp_second_task.model_response)
                    else:
                        return i_task
    
    
        if i_task['bot_function_id'] != None:
### check/add bot functions
            print(i_task['bot_function_id'])
        elif i_task['bot_saved_input_id'] != None:
            if connection_function_saved_inputs.objects.filter(id=i_task['bot_saved_input_id']).exists():
                from synapse.views import get_connection_data_w_input
                temp_saved_input = connection_function_saved_inputs.objects.get(id=i_task['bot_saved_input_id'])

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
                i_task['user_prompt'] = str(i_task['user_prompt']) + f" ///Releavant Information: {relevant_data}"

        elif i_task['bot_local_function_id'] != None:
            if local_function_files.objects.filter(id=i_task['bot_local_function_id']).exists():
                temp_local_function = local_function_files.objects.get(id=i_task['bot_local_function_id'])

                run_list = []
                try:
                    temp_rq = json.loads(str(i_task['user_prompt']).replace("'", '"'))

                    for i_keys, e_keys in enumerate(temp_rq.keys()):
                        run_list.append(str(temp_rq[e_keys]))
                except:
                    run_list = [i_task['user_prompt']]

                file_path = str(temp_local_function.local_function_path)
                
                spec = importlib.util.spec_from_file_location("dynamic_module", file_path)
                dynamic_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(dynamic_module)
                get_cik_fillings = getattr(dynamic_module, str(temp_local_function.local_function_name))
                df = get_cik_fillings(*run_list)

                temp_task_to_edit = axiom_bot_message_task.objects.get(id=i_task['id'])
                temp_task_to_edit.model_response = df
                temp_task_to_edit.save()
                context_task['messages'] = f"ran task - {str(i_task['id'])} "
                return context_task

        i_task['user_prompt'] = f"///User Prompt:{str(i_task['user_prompt'])};" + f"///Relevant Information from previous task:{str(prompt_prev_task)};"
        
        temp_model_personality = model_personality.objects.filter(id=i_task['bot_personality_id']).first() or ""
### change the model used based on user input
        temp_model_connection  = model_connection.objects.get(id=1)

### Check for attachements; add relevant attachements to list for context_task
        if len([item for item in list_of_tasks_attach_dict if item.get('attachemnet_task_id') == i_task['id']]) >= 1:
            temp_attach = [item for item in list_of_tasks_attach_dict if item.get('attachemnet_task_id') == i_task['id']]
            try:
### bring only latest attachement - change this to allow for the option to have latest or all attachements
                temp_user_request_val = temp_attach[0]['attachemnet']
            except:
                temp_user_request_val = ""
        else:
            temp_user_request_val = ""
            
### update task prompt with project description; consider adding other dynamic value options
        if re.search(r"__input__.*__", str(i_task['user_prompt'])):
            if "__input__project_description__" in str(i_task['user_prompt']):
                i_task['user_prompt'] = str(i_task['user_prompt']).replace("__input__project_description__", str(project_to_build.project_description))

### check for a fixed output format


#class ResponseSchema(BaseModel):
#    CompanyName: str = Field(description="The Name of the Company"),
#    CompanyWebsite: str = Field(description="The Website"), 
#    CompanyLinkedIn: str = Field(description="The url to linkedin profile"),
#class StructuredResponse(BaseModel):
#    schema_list: list[ResponseSchema] = Field(description="A list of values found")

        print(len(i_task['user_prompt']), "user_prompt")

        #print("start wait ...")
        #time.sleep(15)
        #print("... end wait")
        if i_task['fixed_output']:
            temp_task = send_task_to_model(
                        promt_message = i_task, user_request = temp_user_request_val, 
                        personality = temp_model_personality, run_tempereature=temp_model_personality.personality_temp, top_p=temp_model_personality.personality_top_p,
                        chat_summary = temp_chat_summary, chat_tool = i_task['bot_tool'], model_base = temp_model_connection.model_base, #model_con
                        model_name = temp_model_connection.model_name, model_api_key = temp_model_connection.model_api_key, strcutured_output=i_task['fixed_output']) #model_con
        else:
            temp_task = send_task_to_model(
                promt_message = i_task, user_request = temp_user_request_val, 
                personality = temp_model_personality, run_tempereature=temp_model_personality.personality_temp, top_p=temp_model_personality.personality_top_p,
                chat_summary = temp_chat_summary, chat_tool = i_task['bot_tool'], model_base = temp_model_connection.model_base, #model_con
                model_name = temp_model_connection.model_name, model_api_key = temp_model_connection.model_api_key,) #model_con
        
        if temp_task.status == "1":
            temp_task_to_edit = axiom_bot_message_task.objects.get(id=i_task['id'])
            temp_task_to_edit.model_response = temp_task
            temp_task_to_edit.save()
            context_task['messages'] = f"ran task - {str(i_task['id'])} "
        else:
            temp_task_message = axiom_bot_message_task.objects.get(id=i_task['id'])
            context_task['messages'] = f"task - {str(i_task['id'])} requires human input!"
            task_form_to_edit = add_axiom_bot_message_task(instance=temp_task_message)
            context_task['help'] = markdown.markdown(str(temp_task.response))
            context_task['task_form_to_edit'] = task_form_to_edit
            context_task['task_form_to_edit_id'] = i_task['id']
        
        return context_task

    else:
        print(i_task['id'])
        return i_task

def add_project_run_to_scheduler(project_template_id, day_count, date_start):
    original_proj_id = project_template_id
    project_template_id = project_template_id.replace("_", " ")

    if project_template.objects.filter(pk=project_template_id).exists():
        db_conf = settings.DATABASES['default']
        db_url = f"sqlite:///{db_conf['NAME']}"
        jobstores = {'default': SQLAlchemyJobStore(url=db_url)}
        scheduler = BackgroundScheduler(jobstores=jobstores)
        scheduler.start(paused=True)
        
        print("adding to store ..." + str(project_template_id))
        project_to_run = project_template.objects.get(pk=project_template_id)

        run_date = date_start
        user_to_notify = project_to_run.pm_owner
        number_of_days = day_count

        project_to_build = project_template.objects.get(pk=original_proj_id)
        scheduler.add_job(func=run_project, trigger='interval', start_date=run_date, id='run_schedule_'+str(original_proj_id),
                        days=number_of_days, replace_existing=True, kwargs={'project_to_build': project_to_build,})
        
        i_message = {"title":"run_project","run_date":run_date, "message":"Your task "+ str(original_proj_id) + " runs today."}
        unique_id = i_message['title'] + "_for_" + str(original_proj_id) + "_to_" + str(user_to_notify.pk)
        scheduler.add_job(apscheduler_functions.send_user_message, 'date', run_date=i_message['run_date'], id=unique_id, 
                        kwargs={'message': i_message['message'], 'user_to_recieve_id': user_to_notify.pk})

def run_project(project_to_build):
    context_run_proj = {'project_to_build':model_to_dict(project_to_build)}
            
    if axiom_bot_message_task.objects.filter(task_project=project_to_build).exists():
        list_of_tasks = axiom_bot_message_task.objects.filter(task_project=project_to_build)
        list_of_tasks_status = ax_task_status_list.objects.filter(task_observed__in=list_of_tasks)
        list_of_tasks_attach = ax_task_attachement.objects.filter(attachemnet_task__in=list_of_tasks).order_by('-datetime_created')
        list_of_tasks_relationship = ax_task_prerequisite.objects.filter(main_task__in=list_of_tasks)

        list_of_tasks_dict = list_of_tasks.values()
        list_of_tasks_status_dict = list_of_tasks_status.values()
        list_of_tasks_attach_dict = list_of_tasks_attach.values()
        list_of_tasks_relationship_dict = list_of_tasks_relationship.values()

        ### Run each task - Add Step to sort by task_project_order and run in that order
        for i_task in list_of_tasks_dict:
            if not i_task['model_response']:
                temp_task_output = run_project_task(i_task, list_of_tasks_attach_dict, list_of_tasks_relationship_dict, project_to_build)
                context_run_proj = context_run_proj | temp_task_output
        
        list_of_tasks = axiom_bot_message_task.objects.filter(task_project=project_to_build)
        list_of_tasks_status = ax_task_status_list.objects.filter(task_observed__in=list_of_tasks)
        list_of_tasks_attach = ax_task_attachement.objects.filter(attachemnet_task__in=list_of_tasks)
        list_of_tasks_relationship = ax_task_prerequisite.objects.filter(main_task__in=list_of_tasks) | ax_task_prerequisite.objects.filter(second_task__in=list_of_tasks)

        task_response = []

        for i_task in list_of_tasks:
            if i_task.model_response:
                if i_task.bot_local_function != None:
                    task_response.append({"id" : i_task.id, "response" : i_task.model_response})
                else:
                    temp_response = re.search(r"response='\s*(.*)'", i_task.model_response)
                    if temp_response:
                        response_value = temp_response.group(1)
                        task_response.append({"id" : i_task.id, "response" : markdown.markdown(response_value.replace(r"\n", "\n"))})

    context_run_proj['list_of_tasks'] = list_of_tasks.values()
    context_run_proj['list_of_tasks_status'] = list_of_tasks_status.values()
    context_run_proj['list_of_tasks_attach'] = list_of_tasks_attach.values()
    context_run_proj['list_of_tasks_relationship'] = list_of_tasks_relationship.values()
    context_run_proj['task_response'] = task_response

    return context_run_proj


class create_project_template(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)
        project_template_form = add_project_template(request.GET or None)
        
        context = {'project_template_form':project_template_form,}
        
        return render(request, 'axiom/new_project_template.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)
        project_template_form = add_project_template(request.POST or None)

        if project_template_form.is_valid():
            new_project_template = project_template_form.save(commit=False)
            new_project_template.created_date = timezone.now()
            new_project_template.save()

        else:
            project_template_form = add_project_template(request.POST or None)

        context = {'project_template_form':project_template_form,}
        return render(request, 'axiom/new_project_template.html', context)

class build_project_template(View):
    def get(self, request, project_template_id):
        if check_authentication(request) != None:
            return check_authentication(request)

        original_proj_id = project_template_id
        project_template_id = project_template_id.replace("_", " ")
        if project_template.objects.filter(pk=project_template_id).exists():
            project_to_build = project_template.objects.get(pk=project_template_id)
            axiom_bot_message_task_form = add_axiom_bot_message_task(request.GET or None, initial={"task_project":project_to_build,"chat_user":request.user})
            
            context = {'axiom_bot_message_task_form':axiom_bot_message_task_form,
                       'project_to_build':model_to_dict(project_to_build)}
            
            if axiom_bot_message_task.objects.filter(task_project=project_to_build).exists():
                list_of_tasks = axiom_bot_message_task.objects.filter(task_project=project_to_build)
                temp_list_of_tasks = []
                for i_ttask, e_task in enumerate(list_of_tasks.values()):
                    if e_task['bot_function_id'] != None:
                        e_task['bot_function'] = connection_functions.objects.get(id=e_task['bot_function_id'])
                    if e_task['bot_personality_id'] != None:
                        e_task['bot_personality'] = model_personality.objects.get(id=e_task['bot_personality_id'])
                    if e_task['bot_saved_input_id'] != None:
                        e_task['bot_saved_input'] = connection_function_saved_inputs.objects.get(id=e_task['bot_saved_input_id'])

                    temp_list_of_tasks.append({"id":e_task['id'], "form":buil_axiom_bot_message_task(initial=e_task)})
                list_of_tasks_status = ax_task_status_list.objects.filter(task_observed__in=list_of_tasks)
                list_of_tasks_relationship = ax_task_prerequisite.objects.filter(main_task__in=list_of_tasks) | ax_task_prerequisite.objects.filter(second_task__in=list_of_tasks)
                context['list_of_tasks'] = list_of_tasks.values()

                context['ax_task_prerequisite_form'] = AddAxTaskPrerequisiteForm(request.GET or None, allowed_relationships=list(list_of_tasks.values_list('id', flat=True)))
                context['list_of_task_relationships'] = list_of_tasks_relationship.values()
                context['temp_list_of_tasks'] = temp_list_of_tasks
                context['project_template_id'] = original_proj_id
            
            return render(request, 'axiom/build_project_template.html', context)
        else:
            return redirect("/axiom/project_template")
    
    def post(self, request, project_template_id):
        if check_authentication(request) != None:
            return check_authentication(request)

        original_proj_id = project_template_id
        project_template_id = project_template_id.replace("_", " ")
        context = {}

        print(request.POST['form_name'])

        if project_template.objects.filter(pk=project_template_id).exists():
            project_to_build = project_template.objects.get(pk=project_template_id)
            
            if request.POST['form_name'] == "task_form_to_edit":
                task_to_edit = axiom_bot_message_task.objects.get(id=request.POST['task_id'])
                edit_task_form = buil_axiom_bot_message_task(request.POST, instance=task_to_edit)
                if edit_task_form.is_valid():
                    edit_task_form.save()
                    print('yes')
                


            elif request.POST['form_name'] == "axiom_bot_message_task_form":
                new_task_form = add_axiom_bot_message_task(request.POST or None)
                if new_task_form.is_valid():
                    new_ax_task = new_task_form.save(commit=False)
                    new_ax_task.date_created = timezone.now()
                    new_ax_task.save()
                    
                    if new_ax_task.bot_tool == "local_files":
                        temp_file_path = check_files(request, new_ax_task)
                        if temp_file_path['state'] == '1':
                            messages.success(request, 'task saved')
                            return redirect(f'/axiom/build_project_template/{original_proj_id}')
                        else:
                            new_ax_task.delete()
                            messages.warning(request, 'task not saved')
                    else:
                        messages.success(request, 'task saved')
                        return redirect(f'/axiom/build_project_template/{original_proj_id}')
                else:
                    messages.warning(request, 'Unclear what has happened')
                    return redirect(f'/axiom/build_project_template/{original_proj_id}')
            
            elif request.POST['form_name'] == "ax_task_prerequisite_form":
                new_task_relationship = add_ax_task_prerequisite(request.POST or None)
                if new_task_relationship.is_valid():
                    new_ax_task_relationship = new_task_relationship.save(commit=False)
                    new_ax_task_relationship.date_created = timezone.now()
                    new_ax_task_relationship.save()
                    messages.warning(request, 'task relationship saved')
                    new_task_form = buil_axiom_bot_message_task(initial={"task_project":project_to_build,"chat_user":request.user})
                
            
            if axiom_bot_message_task.objects.filter(task_project=project_to_build).exists():
                list_of_tasks = axiom_bot_message_task.objects.filter(task_project=project_to_build)
                temp_list_of_tasks = []
                for i_ttask, e_task in enumerate(list_of_tasks.values()):
                    if e_task['bot_function_id'] != None:
                        e_task['bot_function'] = connection_functions.objects.get(id=e_task['bot_function_id'])
                    if e_task['bot_personality_id'] != None:
                        e_task['bot_personality'] = model_personality.objects.get(id=e_task['bot_personality_id'])
                    if e_task['bot_saved_input_id'] != None:
                        e_task['bot_saved_input'] = connection_function_saved_inputs.objects.get(id=e_task['bot_saved_input_id'])

                    temp_list_of_tasks.append({"id":e_task['id'], "form":buil_axiom_bot_message_task(initial=e_task)})
                list_of_tasks_status = ax_task_status_list.objects.filter(task_observed__in=list_of_tasks)
                list_of_tasks_relationship = ax_task_prerequisite.objects.filter(main_task__in=list_of_tasks) | ax_task_prerequisite.objects.filter(second_task__in=list_of_tasks)
                
                axiom_bot_message_task_form = add_axiom_bot_message_task(request.GET or None, initial={"task_project":project_to_build,"chat_user":request.user})
                
                context = {'axiom_bot_message_task_form':axiom_bot_message_task_form,
                        'project_to_build':model_to_dict(project_to_build)}
                
                context['list_of_tasks'] = list_of_tasks.values()
                context['ax_task_prerequisite_form'] = AddAxTaskPrerequisiteForm(request.GET or None, allowed_relationships=list(list_of_tasks.values_list('id', flat=True)))
                context['list_of_task_relationships'] = list_of_tasks_relationship.values()
                context['temp_list_of_tasks'] = temp_list_of_tasks
                context['project_template_id'] = original_proj_id

                #print(list_of_tasks_relationship.values())
            
            return render(request, 'axiom/build_project_template.html', context)
        else:
            return redirect("/axiom/project_template")

class run_project_template(View):
    def get(self, request, project_template_id):
        if check_authentication(request) != None:
            return check_authentication(request)

        original_proj_id = project_template_id
        project_template_id = project_template_id.replace("_", " ")
        if project_template.objects.filter(pm_owner=request.user).exists():
            user_projects = project_template.objects.filter(pm_owner=request.user).values()
            user_projects_df = pd.DataFrame(user_projects)
            user_projects_df['url_name'] = user_projects_df['project_name'].str.replace(" ", "_")
        
        if project_template.objects.filter(pk=project_template_id).exists():
            project_to_build = project_template.objects.get(pk=project_template_id)
            context = {'project_to_build':model_to_dict(project_to_build)}
            
            if axiom_bot_message_task.objects.filter(task_project=project_to_build).exists():
                list_of_tasks = axiom_bot_message_task.objects.filter(task_project=project_to_build)
                complete_list_of_tasks = axiom_bot_message_task.objects.select_related('bot_personality', 'bot_saved_input', "bot_function").filter(task_project=project_to_build)
                list_of_tasks_status = ax_task_status_list.objects.filter(task_observed__in=list_of_tasks)
                list_of_tasks_attach = ax_task_attachement.objects.filter(attachemnet_task__in=list_of_tasks)
                list_of_tasks_relationship = ax_task_prerequisite.objects.filter(main_task__in=list_of_tasks) | ax_task_prerequisite.objects.filter(second_task__in=list_of_tasks)

                task_response = []
                for i_task in list_of_tasks:
                    if i_task.model_response:
                        if i_task.bot_local_function != None:
                            task_response.append({"id" : i_task.id, "response" : i_task.model_response})

                        elif "DynamicItemSchema" in i_task.model_response:
                            temp_response = i_task.model_response.replace("status='1' response=DynamicItemSchema(", "").replace(")", "")
                            task_response.append({"id" : i_task.id, "response" : temp_response})
                        elif "status='1' response=" in i_task.model_response:
                            temp_response = i_task.model_response.replace("status='1' response=", "")
                            task_response.append({"id" : i_task.id, "response" : markdown.markdown(temp_response.replace(r"\n", "\n"))})
                

                context['list_of_tasks'] = complete_list_of_tasks.values("id", "bot_tool", "user_prompt", "model_response", "task_project_order", "bot_personality__personality_name", 
                                                    "bot_saved_input__input_value_description", "bot_function__connection_function_name", "bot_local_function__local_function_name" )
                
                context['list_of_tasks_status'] = list_of_tasks_status.values()
                context['list_of_tasks_attach'] = list_of_tasks_attach.values()
                context['list_of_tasks_relationship'] = list_of_tasks_relationship.values()
                context['task_response'] = task_response
                context['project_template_id'] = original_proj_id
                context['user_projects'] = user_projects_df.to_dict('records')

            context['schedule_form'] = add_project_template_schedule(request.GET or None)
            
            return render(request, 'axiom/run_project_template.html', context)
        else:
            return redirect("/axiom/project_template")
    
    def post(self, request, project_template_id):
        if check_authentication(request) != None:
            return check_authentication(request)

        original_proj_id = project_template_id
        project_template_id = project_template_id.replace("_", " ")

        schedule_template = add_project_template_schedule(request.POST or None)

        if schedule_template.is_valid():
            new_schedule = schedule_template.save(commit=False)
            new_schedule.date_created = timezone.now()
            new_schedule.save()
            
            if new_schedule.project_run_schedule == "repeat_day":
                add_project_run_to_scheduler(new_schedule.project_name.pk, 1, new_schedule.run_date)
                return redirect(f'/axiom/run_project_template/{original_proj_id}')
            if new_schedule.project_run_schedule == "repeat_wkly":
                add_project_run_to_scheduler(new_schedule.project_name.pk, 7, new_schedule.run_date)
                return redirect(f'/axiom/run_project_template/{original_proj_id}')
            if new_schedule.project_run_schedule == "repeat_mthly":
                add_project_run_to_scheduler(new_schedule.project_name.pk, 30, new_schedule.run_date)
                return redirect(f'/axiom/run_project_template/{original_proj_id}')
            
            else:
                project_to_build = project_template.objects.get(pk=project_template_id)
                run_project(project_to_build)
                return redirect(f'/axiom/run_project_template/{original_proj_id}')

        if project_template.objects.filter(pm_owner=request.user).exists():
            user_projects = project_template.objects.filter(pm_owner=request.user).values()
            user_projects_df = pd.DataFrame(user_projects)
            user_projects_df['url_name'] = user_projects_df['project_name'].str.replace(" ", "_")

        if project_template.objects.filter(pk=project_template_id).exists():
            project_to_build = project_template.objects.get(pk=project_template_id)
            context = {'project_to_build':model_to_dict(project_to_build)}

            start_time = datetime.now()
            print(f"Start Time:  {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

            temp_output = run_project(project_to_build)

            finish_time = datetime.now()
            print(f"Finish Time: {finish_time.strftime('%Y-%m-%d %H:%M:%S')}")

            time_delta = finish_time - start_time
            print(f"Time Delta:  {time_delta}")

            #temp_output = run_project(project_to_build)
            
            

            if axiom_bot_message_task.objects.filter(task_project=project_to_build).exists():
                list_of_tasks = axiom_bot_message_task.objects.filter(task_project=project_to_build)
                complete_list_of_tasks = axiom_bot_message_task.objects.select_related('bot_personality', 'bot_saved_input', "bot_function").filter(task_project=project_to_build)
                list_of_tasks_status = ax_task_status_list.objects.filter(task_observed__in=list_of_tasks)
                list_of_tasks_attach = ax_task_attachement.objects.filter(attachemnet_task__in=list_of_tasks)
                list_of_tasks_relationship = ax_task_prerequisite.objects.filter(main_task__in=list_of_tasks) | ax_task_prerequisite.objects.filter(second_task__in=list_of_tasks)

                task_response = []
                for i_task in list_of_tasks:
                    if i_task.model_response:
                        if i_task.bot_local_function != None:
                            task_response.append({"id" : i_task.id, "response" : i_task.model_response})

                        elif "DynamicItemSchema" in i_task.model_response:
                            temp_response = i_task.model_response.replace("status='1' response=DynamicItemSchema(", "").replace(")", "")
                            task_response.append({"id" : i_task.id, "response" : temp_response})
                        elif "status='1' response=" in i_task.model_response:
                            temp_response = i_task.model_response.replace("status='1' response=", "")
                            task_response.append({"id" : i_task.id, "response" : markdown.markdown(temp_response.replace(r"\n", "\n"))})
            

                context['list_of_tasks'] = complete_list_of_tasks.values("id", "bot_tool", "user_prompt", "model_response", "task_project_order", "bot_personality__personality_name", 
                                                    "bot_saved_input__input_value_description", "bot_function__connection_function_name", "bot_local_function__local_function_name" )
                
                context['list_of_tasks_status'] = list_of_tasks_status.values()
                context['list_of_tasks_attach'] = list_of_tasks_attach.values()
                context['list_of_tasks_relationship'] = list_of_tasks_relationship.values()
                context['task_response'] = task_response
                context['project_template_id'] = original_proj_id
                context['user_projects'] = user_projects_df.to_dict('records')

            #context['list_of_tasks'] = temp_output['list_of_tasks']
            #context['list_of_tasks_status'] = temp_output['list_of_tasks']
            #context['list_of_tasks_attach'] = temp_output['list_of_tasks']
            #context['list_of_tasks_relationship'] = temp_output['list_of_tasks']
            #context['task_response'] = temp_output['task_response']
            #context['user_projects'] = user_projects_df.to_dict('records')

            #context['project_template_id'] = original_proj_id
            context['schedule_form'] = add_project_template_schedule(request.GET or None)
            
            return render(request, 'axiom/run_project_template.html', context)
        else:
            return redirect("/axiom/project_template")

class copy_project_template(View):
    def get(self, request, project_template_id):
        if check_authentication(request) != None:
            return check_authentication(request)

        original_proj_id = project_template_id
        project_template_id = project_template_id.replace("_", " ")
        if project_template.objects.filter(pk=project_template_id).exists():
            project_to_build = project_template.objects.get(pk=project_template_id)
            project_to_copy_form = add_project_template(instance=project_to_build)
            context = {'project_to_build':model_to_dict(project_to_build)}
            
            if axiom_bot_message_task.objects.filter(task_project=project_to_build).exists():
                list_of_tasks = axiom_bot_message_task.objects.filter(task_project=project_to_build)
                list_of_tasks_status = ax_task_status_list.objects.filter(task_observed__in=list_of_tasks)
                list_of_tasks_attach = ax_task_attachement.objects.filter(attachemnet_task__in=list_of_tasks)
                list_of_tasks_relationship = ax_task_prerequisite.objects.filter(main_task__in=list_of_tasks) | ax_task_prerequisite.objects.filter(second_task__in=list_of_tasks)

                task_response = []
                for i_task in list_of_tasks:
                    if i_task.model_response:
                        temp_response = re.search(r"response=\"\s*(.*)\"", i_task.model_response.replace("'", '"'))
                        if temp_response:
                            response_value = temp_response.group(1)

                            task_form_to_edit = add_axiom_bot_message_task(instance=i_task)
                            task_response.append({"id" : i_task.id, "task_form_to_edit" : task_form_to_edit, 
                                                  "response" : markdown.markdown(response_value.replace(r"\n", "\n").replace(r"/n", "\n"))})

                context['list_of_tasks'] = list_of_tasks.values()
                context['list_of_tasks_status'] = list_of_tasks_status.values()
                context['list_of_tasks_attach'] = list_of_tasks_attach.values()
                context['list_of_tasks_relationship'] = list_of_tasks_relationship.values()
                context['task_response'] = task_response
                context['project_template_id'] = original_proj_id
                context['project_to_copy_form'] = project_to_copy_form
            
            return render(request, 'axiom/copy_project_template.html', context)
        else:
            return redirect("/axiom/project_template")
    
    def post(self, request, project_template_id):
        if check_authentication(request) != None:
            return check_authentication(request)

        original_proj_id = project_template_id
        project_template_id = project_template_id.replace("_", " ")

        task_key_list = ["date_created", "task_project", "chat_user"
                        "bot_personality", "bot_tool", "bot_function", "bot_saved_input", "bot_local_function",
                        "user_prompt", "fixed_output", "model_response", "task_project_order",]

        project_template_form = add_project_template(request.POST or None)
        if project_template_form.is_valid():
            new_project_template = project_template_form.save(commit=False)
            new_project_template.created_date = timezone.now()
            new_project_template.save()

            task_projects = request.POST.getlist('task_project')
            chat_users = request.POST.getlist('chat_user')
            bot_personalities = request.POST.getlist('bot_personality')
            bot_tools = request.POST.getlist('bot_tool')
            task_type = request.POST.getlist('task_type')
            bot_saved_inputs = request.POST.getlist('bot_saved_input')
            bot_local_functions = request.POST.getlist('bot_local_function')
            user_prompts = request.POST.getlist('user_prompt')
            fixed_outputs = request.POST.getlist('fixed_output')
            orders = request.POST.getlist('task_project_order')
            filenames = request.POST.getlist('filename')

            # Zip lists into unified rows and iterate over them
            zipped_tasks = list(zip_longest(task_projects, chat_users, bot_personalities, 
                bot_tools, task_type, bot_local_functions,  bot_saved_inputs,  user_prompts, fixed_outputs, orders, filenames, fillvalue=''))

            valid_forms = []
            all_valid = False

            for project, user, bot, tool, task_tp, local_func, saved_inp, prompt, output, order, filename in zipped_tasks:
                form_data = {
                    'task_project': new_project_template,
                    'chat_user': user,
                    'bot_personality': bot,
                    'bot_tool': tool,
                    'task_type': task_tp,
                    'bot_local_function': local_func,
                    'bot_saved_input': saved_inp,
                    'user_prompt': prompt,
                    'fixed_output': output,
                    'task_project_order': order,
                    'filename': filename,
                }

                print(form_data, "form_data")
                temp_task_form = add_axiom_bot_message_task(data=form_data)

                if temp_task_form.is_valid():
                    valid_forms.append(temp_task_form)
                    all_valid = True
            
            if all_valid:
                for form in valid_forms:
                    form.save() 
                    
                return redirect('/axiom/run_project_template/'+str(new_project_template.pk).replace(" ", "_"))
            else:
                new_project_template.delete()
                print("else")

                if project_template.objects.filter(pk=project_template_id).exists():
                    project_to_build = project_template.objects.get(pk=project_template_id)
                    project_to_copy_form = add_project_template(instance=project_to_build)
                    context = {'project_to_build':model_to_dict(project_to_build)}
                    
                    if axiom_bot_message_task.objects.filter(task_project=project_to_build).exists():
                        list_of_tasks = axiom_bot_message_task.objects.filter(task_project=project_to_build)
                        list_of_tasks_status = ax_task_status_list.objects.filter(task_observed__in=list_of_tasks)
                        list_of_tasks_attach = ax_task_attachement.objects.filter(attachemnet_task__in=list_of_tasks)
                        list_of_tasks_relationship = ax_task_prerequisite.objects.filter(main_task__in=list_of_tasks) | ax_task_prerequisite.objects.filter(second_task__in=list_of_tasks)
    
                        task_response = []
                        for i_task in list_of_tasks:
                            if i_task.model_response:
                                temp_response = re.search(r"response=\"\s*(.*)\"", i_task.model_response.replace("'", '"'))
                                if temp_response:
                                    response_value = temp_response.group(1)
    
                                    task_form_to_edit = add_axiom_bot_message_task(instance=i_task)
                                    task_response.append({"id" : i_task.id, "task_form_to_edit" : task_form_to_edit, 
                                                        "response" : markdown.markdown(response_value.replace(r"\n", "\n").replace(r"/n", "\n"))})
    
                        context['list_of_tasks'] = list_of_tasks.values()
                        context['list_of_tasks_status'] = list_of_tasks_status.values()
                        context['list_of_tasks_attach'] = list_of_tasks_attach.values()
                        context['list_of_tasks_relationship'] = list_of_tasks_relationship.values()
                        context['task_response'] = task_response
                        context['project_template_id'] = original_proj_id
                        context['project_to_copy_form'] = project_to_copy_form
                    
                    return render(request, 'axiom/copy_project_template.html', context)

        else:         
            if project_template.objects.filter(pk=project_template_id).exists():
                project_to_build = project_template.objects.get(pk=project_template_id)
                project_to_copy_form = add_project_template(instance=project_to_build)
                context = {'project_to_build':model_to_dict(project_to_build)}
                
                if axiom_bot_message_task.objects.filter(task_project=project_to_build).exists():
                    list_of_tasks = axiom_bot_message_task.objects.filter(task_project=project_to_build)
                    list_of_tasks_status = ax_task_status_list.objects.filter(task_observed__in=list_of_tasks)
                    list_of_tasks_attach = ax_task_attachement.objects.filter(attachemnet_task__in=list_of_tasks)
                    list_of_tasks_relationship = ax_task_prerequisite.objects.filter(main_task__in=list_of_tasks) | ax_task_prerequisite.objects.filter(second_task__in=list_of_tasks)

                    task_response = []
                    for i_task in list_of_tasks:
                        if i_task.model_response:
                            temp_response = re.search(r"response=\"\s*(.*)\"", i_task.model_response.replace("'", '"'))
                            if temp_response:
                                response_value = temp_response.group(1)

                                task_form_to_edit = add_axiom_bot_message_task(instance=i_task)
                                task_response.append({"id" : i_task.id, "task_form_to_edit" : task_form_to_edit, 
                                                    "response" : markdown.markdown(response_value.replace(r"\n", "\n").replace(r"/n", "\n"))})

                    context['list_of_tasks'] = list_of_tasks.values()
                    context['list_of_tasks_status'] = list_of_tasks_status.values()
                    context['list_of_tasks_attach'] = list_of_tasks_attach.values()
                    context['list_of_tasks_relationship'] = list_of_tasks_relationship.values()
                    context['task_response'] = task_response
                    context['project_template_id'] = original_proj_id
                    context['project_to_copy_form'] = project_to_copy_form
                
                return render(request, 'axiom/copy_project_template.html', context)
            else:
                return redirect("/axiom/project_template")

class manage_project_runs(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        today = datetime.today()

        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))-1

        # Fetch relevant items for the current month view
        queryset = project_template_schedule.objects.filter(run_date__year=year, run_date__month=month)
        #print(queryset)

        # Group objects by their date field using a dictionary
        events_by_date = defaultdict(list)
        for obj in queryset:
            events_by_date[obj.run_date].append(obj)

        print(events_by_date)
        cal = CustomGridCalendar(events_by_date)
        html_calendar = cal.render_month(year, month)

        context = {
            'calendar_html': html_calendar,
            'current_year': year,
            'current_month': month,
        }
        return render(request, 'axiom/calendar.html', context)

class manage_internal_documents(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        context = {}
        temp_user_info = user_info.objects.get(user=request.user)
        context['objects_user_chat'] = pd.DataFrame(model_chats.objects.filter(chat_user=request.user).values()).to_dict('records')
        context['objects_axiom_projects'] = pd.DataFrame(project_template.objects.filter(pm_owner=request.user).values()).to_dict('records')
        context['objects_pm_project'] = pd.DataFrame(project.objects.filter(pm_owner=temp_user_info).values()).to_dict('records')
        if request.user.username == "daniel":
            context['objects_user_info'] = pd.DataFrame(user_info.objects.all().values()).to_dict('records')
        else:
            context['objects_user_info'] = pd.DataFrame(user_info.objects.filter(user_type="stakeholder").values()).to_dict('records')

        new_internal_document_form = add_internal_document(request.GET or None)
        context['new_internal_document_form'] = new_internal_document_form

        return render(request, 'axiom/new_internal_document.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        context = {}
        temp_user_info = user_info.objects.get(user=request.user)
        context['objects_user_chat'] = pd.DataFrame(model_chats.objects.filter(chat_user=request.user).values()).to_dict('records')
        context['objects_axiom_projects'] = pd.DataFrame(project_template.objects.filter(pm_owner=request.user).values()).to_dict('records')
        context['objects_pm_project'] = pd.DataFrame(project.objects.filter(pm_owner=temp_user_info).values()).to_dict('records')
        if request.user.username == "daniel":
            context['objects_user_info'] = pd.DataFrame(user_info.objects.all().values()).to_dict('records')
        else:
            context['objects_user_info'] = pd.DataFrame(user_info.objects.filter(user_type="stakeholder").values()).to_dict('records')

        new_internal_document_form = add_internal_document(request.POST or None)
        document_objects_dict = {}
        list_check = ["user_chat", "ax_projects", "pm_project", "user_infos"]
        for i, e_list_key in enumerate(list_check):
            if e_list_key in request.POST.keys():
                document_objects_dict[e_list_key] = request.POST[e_list_key]

        if new_internal_document_form.is_valid():
            new_internal_document = new_internal_document_form.save(commit=False)
            new_internal_document.date_created = timezone.now()
            new_internal_document.document_object = str(document_objects_dict)
            folder_path = "axiom/internal_documents/" + str(new_internal_document.document_type) + "/" + str(new_internal_document.document_name)
            os.makedirs(folder_path, exist_ok=True)
            new_internal_document.save()

            messages.warning(request, 'New Internal Doc!')
            return redirect('/axiom/create_internal_document')
        else:
            new_internal_document_form = add_internal_document(request.POST or None)

        context['new_internal_document_form'] = new_internal_document_form
        return render(request, 'axiom/new_project_template.html', context)


class manage_document_versions(View):
    def get(self, request, internal_doc_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        doc_id_url = internal_doc_id
        if "__" in internal_doc_id:
            doc_id_obj = doc_id_url
        else:
            doc_id_obj = str(internal_doc_id).replace("_", " ")
        temp_user_info = user_info.objects.get(user=request.user)
        context = {}
        if internal_document.objects.filter(pk=doc_id_obj).exists():
            internal_doc_to_edit = internal_document.objects.get(pk=doc_id_obj)
            temp_obj_list = json.loads(internal_doc_to_edit.document_object.replace("'", '"'))
            for i, e_obj in enumerate(temp_obj_list.keys()): #["user_chat", "ax_projects", "pm_project", "user_infos"]
                if e_obj == "user_chat":
                    temp_user_chats = pd.DataFrame(model_chats.objects.filter(chat_user=request.user).values())
                    obj_list_chat = temp_user_chats[temp_user_chats['id'] == int(temp_obj_list[e_obj].split('__')[-1])]
                    context['proj_user_chat'] = obj_list_chat.to_dict('records')
                
                elif e_obj == "user_infos":
                    temp_user_infos = pd.DataFrame(user_info.objects.all().values())
                    obj_list_user = temp_user_infos[temp_user_infos['user_id'] == int(temp_obj_list[e_obj].split('__')[-1])] 
                    context['proj_user_infos'] = obj_list_user.to_dict('records')
                
                elif e_obj == "ax_projects":
                    temp_user_ax_projects = pd.DataFrame(project_template.objects.filter(pm_owner=request.user).values())
                    obj_list_ax_proj = temp_user_ax_projects[temp_user_ax_projects['project_name'] == temp_obj_list[e_obj].split('__')[-1]]
                    obj_list_ax_proj['project_name_url'] = temp_obj_list[e_obj].split('__')[-1].replace(" ", "_")
                    context['proj_ax_projects'] = obj_list_ax_proj.to_dict('records')
                
                elif e_obj == "pm_project":
                    temp_user_pm_projects = pd.DataFrame(project.objects.filter(pm_owner=temp_user_info).values())
                    obj_list_pm_proj = temp_user_pm_projects[temp_user_pm_projects['project_name'] == temp_obj_list[e_obj].split('__')[-1]] 
                    obj_list_pm_proj['project_name_url'] = temp_obj_list[e_obj].split('__')[-1].replace(" ", "_")
                    context['proj_pm_project'] = obj_list_pm_proj.to_dict('records')

            if internal_document_version.objects.filter(internal_document=internal_doc_to_edit):
                internal_document_version_list = internal_document_version.objects.filter(internal_document=internal_doc_to_edit)
                latest_doc_version = pd.DataFrame(internal_document_version_list.values())
                latest_doc_version = latest_doc_version[latest_doc_version['document_version'] == latest_doc_version['document_version'].max()]
                latest_doc_version = latest_doc_version[["document_text", "document_notes"]]
            
            else:
                latest_doc_version = None
                print("no internal docs")

            if isinstance(latest_doc_version, pd.DataFrame):
                context['new_document_version_form'] = add_internal_document_version(request.GET or None, initial=latest_doc_version.iloc[0])
            else:
                context['new_document_version_form'] = add_internal_document_version(request.GET or None)
            context['internal_doc_to_edit'] = model_to_dict(internal_doc_to_edit)
            context['internal_doc_id'] = doc_id_url
            return render(request, 'axiom/manage_document_version.html', context)
        else:
            return redirect("/axiom/create_internal_document/")
    
    def post(self, request, internal_doc_id):
        if check_authentication(request) != None:
            return check_authentication(request)

        doc_id_url = internal_doc_id
        doc_id_obj = str(internal_doc_id).replace("_", " ")
        temp_user_info = user_info.objects.get(user=request.user)
        context = {}
        if internal_document.objects.filter(pk=doc_id_obj).exists():
            internal_doc_to_edit = internal_document.objects.get(pk=doc_id_obj)
            temp_obj_list = json.loads(internal_doc_to_edit.document_object.replace("'", '"'))
            for i, e_obj in enumerate(temp_obj_list.keys()): #["user_chat", "ax_projects", "pm_project", "user_infos"]
                if e_obj == "user_chat":
                    temp_user_chats_vals = model_chats.objects.filter(chat_user=request.user).values()
                    current_user_chats_vals = model_chats.objects.filter(id=int(temp_obj_list[e_obj].split('__')[-1])).values()
                    temp_user_chats = pd.DataFrame(temp_user_chats_vals)
                    obj_list_chat = temp_user_chats[temp_user_chats['id'] == int(temp_obj_list[e_obj].split('__')[-1])]
                    context['proj_user_chat'] = obj_list_chat.to_dict('records')
                
                elif e_obj == "user_infos":
                    temp_user_infos_vals = user_info.objects.all().values()
                    current_user_infos_vals = user_info.objects.filter(user_id=int(temp_obj_list[e_obj].split('__')[-1])).values()
                    temp_user_infos = pd.DataFrame(temp_user_infos_vals)
                    obj_list_user = temp_user_infos[temp_user_infos['user_id'] == int(temp_obj_list[e_obj].split('__')[-1])] 
                    context['proj_user_infos'] = obj_list_user.to_dict('records')
                
                elif e_obj == "ax_projects":
                    temp_user_ax_projects_vals = project_template.objects.filter(pm_owner=request.user).values()
                    current_user_ax_projects_vals = project_template.objects.filter(project_name=temp_obj_list[e_obj].split('__')[-1]).values()
                    temp_user_ax_projects = pd.DataFrame(temp_user_ax_projects_vals)
                    obj_list_ax_proj = temp_user_ax_projects[temp_user_ax_projects['project_name'] == temp_obj_list[e_obj].split('__')[-1]]
                    obj_list_ax_proj['project_name_url'] = temp_obj_list[e_obj].split('__')[-1].replace(" ", "_")
                    context['proj_ax_projects'] = obj_list_ax_proj.to_dict('records')
                
                elif e_obj == "pm_project":
                    temp_user_pm_projects_val =  project.objects.filter(pm_owner=temp_user_info).values()
                    current_user_pm_projects_val = project.objects.filter(project_name=temp_obj_list[e_obj].split('__')[-1]).values()
                    temp_user_pm_projects = pd.DataFrame(temp_user_pm_projects_val)
                    obj_list_pm_proj = temp_user_pm_projects[temp_user_pm_projects['project_name'] == temp_obj_list[e_obj].split('__')[-1]] 
                    obj_list_pm_proj['project_name_url'] = temp_obj_list[e_obj].split('__')[-1].replace(" ", "_")
                    context['proj_pm_project'] = obj_list_pm_proj.to_dict('records')

            if internal_document_version.objects.filter(internal_document=internal_doc_to_edit):
                internal_document_version_list = internal_document_version.objects.filter(internal_document=internal_doc_to_edit)
                latest_doc_version = pd.DataFrame(internal_document_version_list.values())
                latest_doc_version = latest_doc_version[latest_doc_version['document_version'] == latest_doc_version['document_version'].max()]
                latest_doc_version_output = latest_doc_version[["document_text", "document_notes"]]
            
            else:
                internal_document_version_list = None
                latest_doc_version_output = None
                print("no internal docs")
### get request info

        if 'delete_doc' in request.POST.keys():
            doc_id_url = internal_doc_id
            doc_id_obj = str(internal_doc_id).replace("_", " ")
            temp_user_info = user_info.objects.get(user=request.user)
            context = {}
            if internal_document.objects.filter(pk=doc_id_obj).exists():
                internal_doc_to_edit = internal_document.objects.get(pk=doc_id_obj)

                folder_path = "axiom/internal_documents/" + str(internal_doc_to_edit.document_type) + "/" + str(internal_doc_to_edit.document_name)

                if os.path.exists(folder_path):
                    shutil.rmtree(folder_path)
                else:
                    print("The folder does not exist.")
                
                internal_doc_to_edit.delete()
            return redirect("/axiom/create_internal_document/")
        
        elif 'document_text' in request.POST:
            temp_doc_version_form = add_internal_document_version(request.POST or None)
            if temp_doc_version_form.is_valid():
                new_internal_doc_version = temp_doc_version_form.save(commit=False)
                new_internal_doc_version.date_created = timezone.now()
                new_internal_doc_version.internal_document = internal_doc_to_edit
                if internal_document_version_list == None:
                    new_internal_doc_version.document_version = 1
                else:
                    new_internal_doc_version.document_version = internal_document_version_list.count() + 1
                
                new_internal_doc_version.save()
                return redirect("/axiom/manage_document_version/" + doc_id_url)
        elif 'download_doc' in request.POST:
            if internal_document_version_list == None:
                print("no doc to download")
            else:
                markdown_text = latest_doc_version['document_text'].iloc[0]
                folder_path = "axiom/internal_documents/" + str(internal_doc_to_edit.document_type) + "/" + str(internal_doc_to_edit.document_name)
                print(latest_doc_version['document_version'].astype(str))
                temp_file_path = folder_path+"/" + str(internal_doc_to_edit.document_name) + "_" + str(latest_doc_version['document_version'].iloc[0].astype(str)) +  ".md"

                with open(temp_file_path , "w", encoding="utf-8") as file:
                    file.write(markdown_text)
        
        elif 'summarize_doc' in request.POST:
            doc_context = {}

            for e_chat in current_user_chats_vals:
                summarize_chat(model_chat_id=e_chat['id'])
                temp_doc = internal_document.objects.get(document_name='user_chat_summary__chat_id__'+str(e_chat['id']))
                chat_summary_versions = internal_document_version.objects.filter(internal_document=temp_doc)
                chat_summary_versions_df = pd.DataFrame(chat_summary_versions.values())
                latest_summary_version = chat_summary_versions_df[chat_summary_versions_df['document_version'] == chat_summary_versions_df['document_version'].max()]
                doc_context['chat_summary_'+str(e_chat['chat_title'])] = latest_summary_version['document_text'].iloc[0]
                
            for e_user_info in current_user_infos_vals:
                if e_user_info['user_type'] == 'stakeholder':
                    sh_task_name = "stakeholder-task-" + str(e_user_info['user_id'])
                    if task.objects.filter(task_name=sh_task_name).exists():
                        sh_task = task.objects.filter(task_name=sh_task_name).values()

                        doc_context["user_info_"+str(e_user_info['user_id'])] = {"user_info": e_user_info, "stakeholder_details":sh_task}
                    else:
                        doc_context["user_info_"+str(e_user_info['user_id'])] = {"user_info": e_user_info,}        
                else:
                    doc_context["user_info_"+str(e_user_info['user_id'])] = {"user_info": e_user_info,}
            
            for e_ax_proj in current_user_ax_projects_vals:
                temp_ax_tasks = axiom_bot_message_task.objects.filter(task_project=e_ax_proj['project_name']).values()
                doc_context["ax_project_tasks_"+e_ax_proj['project_name']] = {"project_info":e_ax_proj, "project_tasks":temp_ax_tasks}
                #print("tasks ax", temp_ax_tasks)
                #print(e_ax_proj)
            
            for e_pm_proj in current_user_pm_projects_val:
                temp_pm_tasks = task.objects.filter(task_project=e_pm_proj['project_name']).values()
                doc_context["pm_project_tasks_"+e_pm_proj['project_name']] = {"project_info":e_pm_proj, "project_tasks":temp_pm_tasks}
                #print("tasks pm", temp_pm_tasks)
                #print(e_pm_proj)

            print('summarize_doc', doc_context)
            temp_model_personality = internal_doc_to_edit.document_personality
            temp_model_connection  = model_connection.objects.get(id=2)
            
            run_model = ChatOpenAI( base_url=temp_model_connection.model_base, api_key=temp_model_connection.model_api_key,
            model=temp_model_connection.model_name, temperature=0.1, top_p=0.1)

            class PrivateChatSummary(BaseModel):
                general_summary: str = Field(description="Summary of relevant information found in chat history.")
                private_summary: str = Field(description="All private information from chat history.")
        
            temp_prompt = ( "You are an AI assitant being obeserved for your efficiency and performance, "
            "Analyze the information provided and create a detailed summary of relevant information to be used as a document of reference going forward;" \
            "Be sure to inlcude all the information that would be relevant for the conversation going forward if the chat history were removed;"
            "Be sure to collect and write down all private and personal, or professional information including client names and details only in the private summary;")
            run_model_w_struct = run_model.with_structured_output(PrivateChatSummary)
            user_prompt = ChatPromptTemplate.from_messages([("assistant", "{system_context}"), ("human", "{promt_message}"),])
            chain = user_prompt | run_model_w_struct
            summaries_list = chain.invoke({"promt_message": temp_prompt, "system_context": doc_context,})

            if isinstance(internal_document_version_list, pd.DataFrame):
                doc_version = int(latest_doc_version['document_version'].iloc[0])+1
            else:
                doc_version = 1 
            new_doc_version = internal_document_version.objects.create( date_created = timezone.now(), document_text = summaries_list.general_summary,
            document_notes = summaries_list.private_summary, document_version = doc_version, internal_document = internal_doc_to_edit,)


### doc version form 
        if latest_doc_version_output != None:
            context['new_document_version_form'] = add_internal_document_version(request.GET or None, initial=latest_doc_version_output.iloc[0])
        else:
            context['new_document_version_form'] = add_internal_document_version(request.GET or None)
        context['internal_doc_to_edit'] = model_to_dict(internal_doc_to_edit)
        context['internal_doc_id'] = doc_id_url
        return render(request, 'axiom/manage_document_version.html', context)

