from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, JsonResponse
from django.views import View
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.views.decorators.csrf import csrf_exempt
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from django.conf import settings

import pandas as pd
import json, re, pytz, os
from .models import *
from .forms import *
from .mechanisms import apscheduler_functions
from synapse.models import user_info
from axiom.models import project_template

UPLOAD_FOLDER = "/home/daniel/Desktop/test/"

from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
from quicksand.quicksand import quicksand

from axiom.views import run_project
from .calendar_util import ProjectGridCalendar
from collections import defaultdict



def check_task_status():
    date_format = '%d/%m/%Y'
    all_tasks = pd.DataFrame(task.objects.all().values())
    today = datetime.now().replace(tzinfo=pytz.UTC)
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

def form_to_json_schema(form):
    schema = {}
    
    for name, field in form.fields.items():    
        field_data = {}
        
        if hasattr(field, 'choices') and field.choices:
            field_data['choices'] = [{'option': str(c[1])} for c in field.choices]

        schema[name] = field_data
    return schema

def add_business_days(start_date, num_days, holidays=None):
    date_format = '%d/%m/%Y'

    if holidays is None:
        holidays = []
    ### add clause to ensure holidays are correct date format to be compared
    
    if not isinstance(num_days, float) or not isinstance(num_days, int):
        try:
            num_days = float(num_days)
        except:
            data = {'message':'num_days value is not a valid number'}
            return data

    if isinstance(start_date, str):
        new_date = datetime.strptime(start_date, date_format).date()
    else:
        new_date = start_date
    days_added = 0
    while days_added < num_days:
        new_date += timedelta(days=1)
        if new_date.weekday()< 5 and new_date not in holidays:
            days_added += 1
    
    data = {'message':f'new date is {new_date}',
            'new_date':new_date,}
    return data

def add_months(start_date, num_months, holidays=None):
    date_format = '%d/%m/%Y'

    if holidays is None:
        holidays = []
    ### add clause to ensure holidays are correct date format to be compared
    
    if not isinstance(num_months, float) or not isinstance(num_months, int):
        try:
            num_months = float(num_months)
        except:
            data = {'message':'num_days value is not a valid number'}
            return data

    if isinstance(start_date, str):
        new_date = datetime.strptime(start_date, date_format).date()
    else:
        new_date = start_date
    months_added = 0
    while months_added < num_months:
        new_date += relativedelta(months=1)
        months_added += 1
        
    while new_date in holidays or new_date.weekday() > 4:
        new_date += timedelta(days=1)
        
    data = {'message':f'new date is {new_date}',
            'new_date':new_date,}
    return data

def create_repeat_tasks(task_id):
    date_format = '%d/%m/%Y'
    if task.objects.filter(id=task_id).exists():
        task_to_repeat = task.objects.get(id=task_id)
        task_repeat_schedule = task_to_repeat.task_schedule
        new_task_start_date = task_to_repeat.start_date
        new_task_soft_due_date = task_to_repeat.soft_due_date
        new_task_hard_due_date = task_to_repeat.hard_due_date

        if task_to_repeat.task_project is not None:
            new_task_project = task_to_repeat.task_project
        elif task_to_repeat.task_deliverable is not None:
            new_task_deliverable = task_to_repeat.task_deliverable
        else:
            return {'message':f'{task_id} is not valid;',
                    'state':'0'}

        if task_repeat_schedule == 'one_time':
            return {'message':f'{task_id} is not valid;',
                    'state':'0'}
        
        elif task_repeat_schedule == 'repeat_wkly':
            new_task_start_date = add_business_days(new_task_start_date, 5)
            new_task_soft_due_date = add_business_days(new_task_soft_due_date, 5)
            new_task_hard_due_date = add_business_days(new_task_hard_due_date, 5)

        elif task_repeat_schedule == 'repeat_mthly':
            new_task_start_date = add_months(new_task_start_date, 1)
            new_task_soft_due_date = add_months(new_task_soft_due_date, 1)
            new_task_hard_due_date = add_months(new_task_hard_due_date, 1)
        elif task_repeat_schedule == 'repeat_yrly':
            new_task_start_date = add_months(new_task_start_date, 12)
            new_task_soft_due_date = add_months(new_task_soft_due_date, 12)
            new_task_hard_due_date = add_months(new_task_hard_due_date, 12)
        
        if new_task_start_date == task_to_repeat.start_date:
            return {'message':f'{task_id} is not valid;',
                    'state':'0'}
        
        try:
            new_task_created = task.objects.create(
                task_name = task_to_repeat.task_name,
                task_description = task_to_repeat.task_description,
                start_date = new_task_start_date['new_date'],
                soft_due_date = new_task_soft_due_date['new_date'],
                hard_due_date = new_task_hard_due_date['new_date'],
                task_schedule = task_to_repeat.task_schedule,
                task_project = new_task_project
            )
        except:
            new_task_created = task.objects.create(
                task_name = task_to_repeat.task_name,
                task_description = task_to_repeat.task_description,
                start_date = new_task_start_date['new_date'],
                soft_due_date = new_task_soft_due_date['new_date'],
                hard_due_date = new_task_hard_due_date['new_date'],
                task_schedule = task_to_repeat.task_schedule,
                task_deliverable = new_task_deliverable
            )

        if task_staff.objects.filter(task=task_to_repeat.id).exists():
            task_staf_to_reset = pd.DataFrame(task_staff.objects.filter(task=task_to_repeat).values())
            for i, e_task_staff_to_reset in task_staf_to_reset.iterrows():
                task_staff.objects.create(
                    staff = user_info.objects.get(pk=e_task_staff_to_reset['staff_id']),
                    task = task.objects.get(id=new_task_created.id),
                )


        ### check if task has related tasks; re-assgin it
        
        ### check if task has staff & grouping; re-assign it
        check_task_status()
        return {'message':f'{new_task_created.id} task has been created;',
                'new_task':new_task_created,
                'state':'1'}
    else:
        print('nothing')
        return {'message':f'{task_id} is not valid;',
                'state':'0'}

def get_api_filter(object_to_get, request_id):
    print(object_to_get.objects.all())

def check_authentication(check_request):
    if not check_request.user.is_authenticated:
        user_auth_form = AuthenticationForm(check_request.GET or None)
        context = {'user_auth_form':user_auth_form}
        return render(check_request, 'pm/login.html', context)

def check_files(request):
    print(request.FILES)
    if 'filename' not in request.FILES:
        return {'message':'no file',
                    'state':'0'}
    else:
        file_to_check = request.FILES['filename']
        file_content = file_to_check.read()
        qs = quicksand(file_content)
        qs.process()

        # Define 'safe' based on analysis results
        if not qs.results.get('exploits_found'):
            filename = re.sub(r'[<>:"/\\|?*\n\t\r\x00-\x1F]', '', file_to_check.name)
            with open(os.path.join(UPLOAD_FOLDER, filename), 'wb+') as destination:
                for chunk in file_to_check.chunks():
                    destination.write(chunk)

            return {'message':'File saved',
                    'file_path': str(os.path.join(UPLOAD_FOLDER, filename)) ,
                    'state':'1'}
        
        
        return {'message':'Malicious file detected.',
                    'state':'0'}

def get_user_dashboard_info(request):
    context = {}
    get_user_info = user_info.objects.get(user_id=request.user.id)
    context['user_info'] = get_user_info

    if request.user.username == 'daniel':
        get_all_project_groups = pd.DataFrame(project_group.objects.all().values())
        get_all_project_groupings = pd.DataFrame(project_grouping.objects.all().values())
        get_all_projects = pd.DataFrame(project.objects.all().values())
        try:
            get_all_project_groupings = pd.merge(get_all_project_groupings, get_all_project_groups, left_on='project_group_id', right_on='id', how='left').fillna(0)
            get_all_projects = pd.merge(get_all_projects, get_all_project_groupings, left_on='project_name', right_on='project_id', how='left').fillna(0)
            get_all_projects['project_name_for_link'] = get_all_projects['project_name'].str.replace(' ', '_')
        except:
            get_all_projects = pd.DataFrame(project.objects.all().values())
            get_all_projects['project_name_for_link'] = get_all_projects['project_name'].str.replace(' ', '_')
            context['projects'] = get_all_projects.to_dict('records')

        
        get_all_tasks = pd.DataFrame()
        get_all_deliverables = pd.DataFrame()
        for i, e_project in enumerate(get_all_projects['project_name']):
            temp_deliverables = pd.DataFrame(deliverable.objects.filter(deliverable_project=e_project).values())
            if not temp_deliverables.empty:
                temp_deliverables['deliverable_project'] = e_project
                temp_deliverables['deliverable_project_name_link'] = temp_deliverables['deliverable_project_id'].str.replace(' ', '_')
                get_all_deliverables = pd.concat([temp_deliverables, get_all_deliverables])


                for i_deliv, e_deliv in enumerate(temp_deliverables['id']):
                    temp_tasks = pd.DataFrame(task.objects.filter(task_deliverable=e_deliv).values())
                    if not temp_tasks.empty:
                        temp_tasks['task_project'] = e_project
                        temp_tasks['task_project_name_link'] = e_project.replace(' ', '_')
                        get_all_tasks = pd.concat([temp_tasks, get_all_tasks])
            
            temp_tasks = pd.DataFrame(task.objects.filter(task_project=e_project).values())
            if not temp_tasks.empty:
                temp_tasks['task_project'] = e_project
                temp_tasks['task_project_name_link'] = e_project.replace(' ', '_')
                get_all_tasks = pd.concat([temp_tasks, get_all_tasks])
            
            queryset = get_all_tasks.to_dict('records')

            today = datetime.today()
            year = int(request.GET.get('year', today.year))
            month = int(request.GET.get('month', today.month))

            # Group objects by their date field using a dictionary
            events_by_date = defaultdict(list)
            for obj in queryset:
                events_by_date[obj['start_date']].append(obj)

            cal = ProjectGridCalendar(events_by_date)
            html_calendar = cal.render_month(year, month)


            context['calendar_html']= html_calendar
            context['current_year']= year
            context['current_month']= month

            context['all_tasks'] = get_all_tasks.to_dict('records')
            context['all_deliverables'] = get_all_deliverables.to_dict('records')

    
    elif get_user_info.user_type == "staff":
        get_all_tasks = pd.DataFrame()
        get_user_tasks = pd.DataFrame(task_staff.objects.filter(staff=get_user_info).values())
        if not get_user_tasks.empty:
            get_user_tasks = get_user_tasks.drop_duplicates(subset=['task_id', 'staff_id'], keep='first')
            for i, task_e in enumerate(get_user_tasks['task_id']):
                temp_tasks = pd.DataFrame(task.objects.filter(id=task_e).values())
                if not temp_tasks.empty:
                    temp_tasks['task_project'] = temp_tasks['task_project_id']
                    temp_tasks['task_project_name_link'] = temp_tasks['task_project'].str.replace(' ', '_')
                    get_all_tasks = pd.concat([temp_tasks, get_all_tasks])
                
            context['all_tasks'] = get_all_tasks.to_dict('records')
        
            get_all_projects = pd.DataFrame()
            for i, projects_e in enumerate(get_all_tasks['task_project_id'].unique()):
                temp_project = pd.DataFrame(project.objects.filter(project_name=projects_e).values())
                if not temp_project.empty:
                    temp_project['project_name_link'] = temp_project['project_name'].str.replace(' ', '_')
                    get_all_projects = pd.concat([temp_project, get_all_projects])
            
            context['projects'] = get_all_projects.to_dict('records')
            
            get_all_deliverables = pd.DataFrame()
            for i, deliverable_e in enumerate(get_all_tasks['task_deliverable_id'].unique()):
                temp_deliverable = pd.DataFrame(deliverable.objects.filter(id=deliverable_e).values())
                if not temp_deliverable.empty:
                    temp_deliverable['project_name_link'] = temp_deliverable['deliverable_project_id'].str.replace(' ', '_')
                    get_all_deliverables = pd.concat([temp_deliverable, get_all_deliverables])
            
            context['all_deliverables'] = get_all_deliverables.to_dict('records')
    
    all_user_messages_dict = user_messages.objects.filter(user_reciver=get_user_info) | user_messages.objects.filter(message_sender=get_user_info.pk)
    all_users_messages = pd.DataFrame(all_user_messages_dict.values())

    if all_users_messages.empty:
        pass
    else:
        list_of_sender = all_users_messages["message_sender"].unique().tolist()
        output_list = []
        for i, e_sender in enumerate(list_of_sender):
            try:
                output_list.append({'id':f"{e_sender}", 'value':f"{user_info.objects.get(pk=e_sender).user.username}"})

            except:
                output_list.append({'id':f"{e_sender}", 'value':f"{e_sender}"})
        
        context['list_of_sender'] = output_list

    return context

def get_project_info(project_name):
    temp_context = {}
    temp_context['project_name'] = project_name
    project_name = str(project_name).replace('_', ' ')
    
    if project.objects.filter(project_name=project_name).exists():
        project_to_return = pd.DataFrame(project.objects.filter(project_name=project_name).values())
        project_to_return['project_name_for_link'] = project_to_return['project_name'].str.replace(' ', '_')   
        temp_context['project_to_return'] = project_to_return.to_dict('records')

        projects_task = pd.DataFrame(task.objects.filter(task_project_id = project_name).values())
        if not projects_task.empty:
            temp_context['projects_task'] = projects_task.to_dict('records')

        if deliverable.objects.filter(deliverable_project=project_name):
            project_deliverables = pd.DataFrame(deliverable.objects.filter(deliverable_project=project_name).values())
            temp_context['project_deliverables'] = project_deliverables.to_dict('records')

            deliverables_grouping = pd.DataFrame(deliverable_grouping.objects.filter(deliverable_id__in=project_deliverables['id'].tolist()).values())
            if not deliverables_grouping.empty:
                deliverables_grouping = deliverables_grouping.drop('id', axis=1)
                project_deliverables = pd.merge(project_deliverables, deliverables_grouping, left_on='id', right_on='deliverable_id', how='left').fillna(0)
                temp_context['project_deliverables'] = project_deliverables.to_dict('records')

            deliverables_stakeholders = pd.DataFrame(deliverable_stakeholder.objects.filter(deliverable_id__in=project_deliverables['id'].tolist()).values())
            if not deliverables_stakeholders.empty:
                temp_context['deliverables_stakeholders'] = deliverables_stakeholders.to_dict('records')
            
            deliverables_tasks = pd.DataFrame(task.objects.filter(task_deliverable_id__in=project_deliverables['id'].tolist()).values())
            if not deliverables_tasks.empty:
                temp_context['deliverables_tasks'] = deliverables_tasks.to_dict('records')

    return temp_context

def new_task_add_to_scheduler(task_id):

    if task.objects.filter(id=task_id).exists():
        db_conf = settings.DATABASES['default']
        db_url = f"sqlite:///{db_conf['NAME']}"
        jobstores = {'default': SQLAlchemyJobStore(url=db_url)}
        scheduler = BackgroundScheduler(jobstores=jobstores)
        scheduler.start(paused=True)
        
        print("adding to store ..." + str(task_id))
        task_to_schedule = task.objects.get(id=task_id)
        scheduler.add_job(apscheduler_functions.check_task_status, 'date', run_date=task_to_schedule.start_date, id='start_date_'+str(task_id),
                        replace_existing=True, kwargs={'task_id': task_id,})
        
        scheduler.add_job(apscheduler_functions.check_task_status, 'date', run_date=task_to_schedule.soft_due_date, 
                        id='soft_due_date_'+str(task_id), replace_existing=True, kwargs={'task_id': task_id,})
        
        scheduler.add_job(apscheduler_functions.check_task_status, 'date', run_date=task_to_schedule.hard_due_date, 
                        id='hard_due_date_'+str(task_id), replace_existing=True, kwargs={'task_id': task_id,})
        
        if not task_to_schedule.task_project:
            task_deliverable_info = task_to_schedule.task_deliverable
            task_project_info = task_deliverable_info.deliverable_project
        else:
            task_project_info = task_to_schedule.task_project
        
        user_to_notify = task_project_info.pm_owner

        user_messages_to_send = [
            {"title":"start_date","run_date":task_to_schedule.start_date, "message":"Your task "+ task_to_schedule.task_name + " starts today."},
            {"title":"start_date_1","run_date":task_to_schedule.start_date - timedelta(days=1), "message":"Your task "+ task_to_schedule.task_name + " starts tomorrow."},
            {"title":"start_date_7","run_date":task_to_schedule.start_date - timedelta(days=7), "message":"Your task "+ task_to_schedule.task_name + " starts in a week."},

            {"title":"soft_due_date","run_date":task_to_schedule.soft_due_date, "message":"Your task "+ task_to_schedule.task_name + " is due today."},
            {"title":"soft_due_date_1","run_date":task_to_schedule.soft_due_date - timedelta(days=1), "message":"Your task "+ task_to_schedule.task_name + " is due tomorrow."},
            {"title":"soft_due_date_7","run_date":task_to_schedule.soft_due_date - timedelta(days=7), "message":"Your task "+ task_to_schedule.task_name + " is due in a week."},

            {"title":"hard_due_date","run_date":task_to_schedule.hard_due_date, "message":"Your task "+ task_to_schedule.task_name + " is pastdue today."},
            {"title":"hard_due_date_1","run_date":task_to_schedule.hard_due_date - timedelta(days=1), "message":"Your task "+ task_to_schedule.task_name + " is pastdue tomorrow."},
            {"title":"hard_due_date_7","run_date":task_to_schedule.hard_due_date - timedelta(days=7), "message":"Your task "+ task_to_schedule.task_name + " is pastdue in a week."},
        ]

        for i_message in user_messages_to_send:
            unique_id = i_message['title'] + "_for_" + str(task_id) + "_to_" + str(user_to_notify.pk)
            scheduler.add_job(apscheduler_functions.send_user_message, 'date', run_date=i_message['run_date'], id=unique_id, 
                            kwargs={'message': i_message['message'], 'user_to_recieve_id': user_to_notify.pk})

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
        project_to_run = project_template.objects.filter(pk=project_template_id)

        run_date = date_start
        user_to_notify = project_to_run.pm_owner
        number_of_days = day_count

        project_to_build = project_template.objects.get(pk=original_proj_id)
        scheduler.add_job(func=run_project, trigger='interval', start_date=run_date, id='run_schedule_'+str(original_proj_id),
                        days=number_of_days, replace_existing=True, kwargs={'project_to_build': project_to_build,})
        
        i_message = {"title":"run_project","run_date":timezone.now(), "message":"Your task "+ timezone.now() + " starts today."}
        unique_id = i_message['title'] + "_for_" + str(original_proj_id) + "_to_" + str(user_to_notify.pk)
        scheduler.add_job(apscheduler_functions.send_user_message, 'date', run_date=i_message['run_date'], id=unique_id, 
                        kwargs={'message': i_message['message'], 'user_to_recieve_id': user_to_notify.pk})

#check_task_status()

class create_project(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_project_form = create_new_projects(request.GET or None)
        context = {'create_project_form':create_project_form}
        return render(request, 'pm/create_project.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_project_form = create_new_projects(data=request.POST or None)

        if create_project_form.is_valid():
            new_project = create_project_form.save(commit=False)
            new_project.created_date = timezone.now()
            new_project.save()
            
            context = {'new_project':new_project}
            return redirect('/cadence/projects/')

        context = {'create_project_form':create_project_form}
        return render(request, 'pm/create_project.html', context)

    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        create_project_form = create_new_projects()
        create_project_form = form_to_json_schema(create_project_form)
        json_form = {'message':'This form is used to create a new project, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Project Creation Form', 
                          'description':'This form is used to create projects. All fields must be filled for the form to be submitted.', 
                          'form':create_project_form,
                          'format':{'Project Creation Form': {
                        'project_name':'a unique name for project',
                        'project_description':'detailed description of project',
                        'pm_owner':'username of staff user in-charge of project',
                        }}},
                     ]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_project_data = data['Project Creation Form']
        if all(key in new_project_data for key in ['project_name', 'project_description', 'pm_owner',]):
            pm_owner_user = User.objects.get(username = new_project_data['pm_owner'])
            pm_owner_user_info = user_info.objects.get(user = pm_owner_user.id)
            new_project_data['pm_owner'] = pm_owner_user_info
            create_project_form = create_new_projects(new_project_data)
            
            if create_project_form.is_valid():
                new_project = create_project_form.save(commit=False)
                new_project.created_date = timezone.now()
                new_project.save()
                
                data = {'message':'new project has been created.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_project_form.errors}
                print(create_project_form.errors)
        
        print('project not created')
        data = {'message':'An error has occured, to create a project, please ensure your request follows the format below.',
                    'format':{'Project Creation Form': {
                        'project_name':'a unique name for project',
                        'project_description':'detailed description of project',
                        'pm_owner':'username of staff user in-charge of project',
                        }}}
        return JsonResponse(data)

class delete_project(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        delete_project_form = delete_project_f(request.GET or None)
        context = {'delete_project_f':delete_project_form}
        return render(request, 'pm/delete_project.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        delete_project_form = delete_project_f(request.POST or None)
        project_name = re.findall(r"value=\"(.*?)\"", str(delete_project_form))
        if project.objects.filter(project_name=project_name[0]).exists():
            project_to_delete = project.objects.get(project_name=project_name[0])
            if project_to_delete.pm_owner.user == request.user:
                project_to_delete.delete()
                #print('deleted', project_to_delete)
                messages.success(request, 'project deleted')
                return redirect('/cadence/projects/')
            elif request.user.is_superuser:
                project_to_delete.delete()
                #print('deleted', project_to_delete)
                messages.success(request, 'project deleted')
                return redirect('/cadence/projects/')
            else:
                print('not deleted', project_to_delete)
        else:
            print('not a project')
            
        delete_project_form = delete_project_f(request.GET or None)
        context = {'delete_project_f':delete_project_form}
        return render(request, 'pm/delete_project.html', context)

    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        delete_project_f = delete_project_f()
        delete_project_f = form_to_json_schema(delete_project_f)
        json_form = {'message':'This form is used to delete a project, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Delete Project Form', 
                          'description':'This form is used to delete projects, please provide the name of the project you would like to delete.', 
                          'form':delete_project_f,
                          'format':{'Delete Project Form': {
                        'project_name':'name of project you would like to delete',
                        }}},
                     ]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        delete_project_data = data['Delete Project Form']
        if all(key in delete_project_data for key in ['project_name']):
            if project.objects.filter(project_name=delete_project_data['project_name']).exists():
                project_to_delete = project.objects.get(project_name=delete_project_data['project_name'])
                if project_to_delete.pm_owner.user == request.user:
                    project_to_delete.delete()
                    data = {'message':'project has been deleted.'}
                    #print(data)
                    return JsonResponse(data)
                elif request.user.is_superuser:
                    project_to_delete.delete()
                    data = {'message':'project has been deleted.'}
                    #print(data)
                    return JsonResponse(data)
            
                
        data = {'message':'An error has occured, to delete a project, please provide the project name in the format below.',
                'format':{'Delete Project Form': {
                'project_name':'name of project you would like to delete',
                        }}}
        return JsonResponse(data)

class create_deliverable(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_deliverable_form = new_deliverable_frm(request.GET or None)
        context = {'create_deliverable_form':create_deliverable_form}
        return render(request, 'pm/create_deliverable.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_deliverable_form = new_deliverable_frm(request.POST or None)

        if create_deliverable_form.is_valid():
            new_deliverable = create_deliverable_form.save(commit=False)
            new_deliverable.created_date = timezone.now()
            new_deliverable.save()
            
            context = {'new_deliverable':new_deliverable}
            return redirect('/cadence/projects/')
        else:
            
            context = {'create_deliverable_form':create_deliverable_form}
            return render(request, 'pm/create_deliverable.html', context)

    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_deliverable_form = new_deliverable_frm()
        create_deliverable_form = form_to_json_schema(create_deliverable_form)
        json_form = {'message':'This form is used to create a new project, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Deliverable Creation Form', 
                          'description':'This form is used to create deliverables. All fields must be filled for the form to be submitted.', 
                          'form':create_deliverable_form,
                          'format':{'Deliverable Creation Form': {
                        'deliverable_name':'a unique name for the deliverable',
                        'deliverable_description':'detailed description of the deliverable',
                        'deliverable_project':'name of the project this deliverable belongs to',
                        'start_date':'DD/MM/YYYY'
                        }}},
                     ]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_deliverable_data = data['Deliverable Creation Form']

        if all(key in new_deliverable_data for key in ['deliverable_name', 'deliverable_description', 'deliverable_project', 'start_date']):
            deliverable_project = project.objects.get(project_name = new_deliverable_data['deliverable_project'])
            new_deliverable_data['deliverable_project'] = deliverable_project
            new_deliverable_data['start_date'] = (datetime.strptime(new_deliverable_data['start_date'], '%d/%m/%Y'))
            create_deliverable_form = new_deliverable_frm(new_deliverable_data)
            
            if create_deliverable_form.is_valid():
                new_deliverable = create_deliverable_form.save(commit=False)
                new_deliverable.created_date = timezone.now()
                new_deliverable.save()
                
                data = {'message':'new deliverable has been created.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_deliverable_form.errors}
                print(create_deliverable_form.errors)

        print('deliverable not created')
        
        data = {'message':'An error has occured, to create a deliverable, please ensure your request follows the format below.',
                    'format':{'Deliverable Creation Form': {
                        'deliverable_name':'a unique name for the deliverable',
                        'deliverable_description':'detailed description of the deliverable',
                        'deliverable_project':'name of the project this deliverable belongs to',
                        'start_date':'DD/MM/YYYY'
                        }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_deliverable(request, deliverable_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if deliverable.objects.filter(id=deliverable_id).exists():
            deliverable_to_delete = deliverable.objects.get(id=deliverable_id)
            deliverable_to_delete.delete()
            
        data = {'message':'deliverable deleted'}
        return redirect('/cadence/projects/')
    
class create_tasks(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_task_form = create_new_tasks(request.GET or None)
        context = {'create_task_form':create_task_form}
        return render(request, 'pm/create_tasks.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_task_form = create_new_tasks(data=request.POST or None)

        if create_task_form.is_valid():
            new_task = create_task_form.save(commit=False)
            new_task.created_date = timezone.now()
            new_task.save()
            
            context = {'new_task':new_task}
            new_task_add_to_scheduler(new_task.id)
            return redirect('/cadence/projects/')

        context = {'create_task_form':create_task_form}
        return render(request, 'pm/create_tasks.html', context)

    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        create_task_form = create_new_tasks()
        create_task_form = form_to_json_schema(create_task_form)
        json_form = {'message':'This form is used to create a new task, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Task Creation Form', 
                          'description':'This form is used to create tasks. All fields must be filled for the form to be submitted.', 
                          'form':create_task_form,
                          'format':{'Task Creation Form': {
                        'task_name':'a unique name for the tasks',
                        'task_description':'detailed description of the tasks',
                        'start_date':'projected start date for task in date format \'DD/MM/YYYY\'',
                        'soft_due_date':'preferred due date for task in date format \'DD/MM/YYYY\'',
                        'hard_due_date':'absolute latest due date for task in date format \'DD/MM/YYYY\'',
                        'task_status':'default is \'not_started\'',
                        'task_schedule':'default is \'one_time\'',
                        'task_project':'a project from the list of projects; only select 1 project or 1 deliverable',
                        'task_deliverable':'a deliverable from the list of deliverables; only select 1 project or 1 deliverable',
                        }}},
                     ]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_task_data = data['Task Creation Form']
        if all(key in new_task_data for key in ['task_name', 'task_description',
                                                'start_date', 'soft_due_date',
                                                'hard_due_date', 'task_status',
                                                'task_schedule', 'task_project', 'task_deliverable',]):

            new_task_data['start_date'] = (datetime.strptime(new_task_data['start_date'], '%d/%m/%Y'))
            new_task_data['soft_due_date'] = (datetime.strptime(new_task_data['soft_due_date'], '%d/%m/%Y'))
            new_task_data['hard_due_date'] = (datetime.strptime(new_task_data['hard_due_date'], '%d/%m/%Y'))
            try:
                if project.objects.filter(project_name=new_task_data['task_project']).exists():
                    new_task_data['task_project'] = project.objects.get(project_name=new_task_data['task_project'])
            except:
                if deliverable.objects.filter(deliverable_name=new_task_data['deliverable_name']).exists():
                    new_task_data['deliverable_name'] = deliverable.objects.get(deliverable_name=new_task_data['deliverable_name'])
            
            create_task_form = create_new_tasks(new_task_data)
            
            if create_task_form.is_valid():
                new_task = create_task_form.save(commit=False)
                new_task.created_date = timezone.now()
                new_task.save()

                new_task_add_to_scheduler(new_task.id)
                
                data = {'message':'new task has been created.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_task_form.errors}
                print(create_task_form.errors)
            
        data = {'message':'An error has occured, to create a task, please ensure your request follows the format below.',
                    'format':{'Task Creation Form': {
                        'task_name':'a unique name for the tasks',
                        'task_description':'detailed description of the tasks',
                        'start_date':'projected start date for task in date format \'DD/MM/YYYY\'',
                        'soft_due_date':'preferred due date for task in date format \'DD/MM/YYYY\'',
                        'hard_due_date':'absolute latest due date for task in date format \'DD/MM/YYYY\'',
                        'task_status':'default is \'not_started\'',
                        'task_schedule':'default is \'one_time\'',
                        'task_project':'a project from the list of projects; only select 1 project or 1 deliverable',
                        'task_deliverable':'a deliverable from the list of deliverables; only select 1 project or 1 deliverable',
                        }}}
        return JsonResponse(data)

class delete_tasks(View):
    def delete_task(request, task_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if not request.user.is_superuser:
            if user_info.objects.filter(user_id=request.user.id).exists():
                request_user_info = user_info.objects.get(user_id=request.user.id)
                if task_staff.objects.filter(staff_id=user_info.id).exists():
                    request_user_tasks = pd.DataFrame(task_staff.objects.filter(staff_id=user_info.id).values())
                    if (request_user_tasks['task_id'] == task_id).any():
                        if task.objects.filter(id=task_id).exists():
                            task_to_delete = task.objects.get(id=task_id)
                            task_to_delete.delete()

                            messages.success(request, 'task deleted')
                            return redirect('/cadence/projects/')           
            
            
            messages.error(request, 'task not deleted')
            return redirect('/cadence/projects/')
        
        if task.objects.filter(id=task_id).exists():
            task_to_delete = task.objects.get(id=task_id)
            task_to_delete.delete()
            
        messages.success(request, 'task deleted')
        return redirect('/cadence/projects/')

    def complete_task(request, task_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if not request.user.is_superuser:
            request_user_info = user_info.objects.get(user_id=request.user.id)
            if task_staff.objects.filter(staff_id=user_info.id).exists():
                request_user_tasks = pd.DataFrame(task_staff.objects.filter(staff_id=user_info.id).values())
                if (request_user_tasks['task_id'] == task_id).any():
                    if task.objects.filter(id=task_id).exists():
                        task_to_complete = task.objects.get(id=task_id)
                        task_to_complete.task_status = 'completed'
                        task_to_complete.save()
                        if task_to_complete.task_schedule == 'one_time':
                            #data = {'message':'task is now completed.'}
                            messages.success(request, 'task is now completed.')
                            return redirect('/cadence/projects/')
                        elif task_to_complete.task_schedule in repeat_schedules:
                            new_task_created = create_repeat_tasks(task_id)
                            #data = {'message':new_task_created['message']}
                            messages.success(request, new_task_created['message'])
                            return redirect('/cadence/projects/')          
            
            messages.error(request, 'task not deleted')
            return redirect('/cadence/projects/')

        
        repeat_schedules = ['repeat_wkly', 'repeat_mthly', 'repeat_yrly']
        if task.objects.filter(id=task_id).exists():
            task_to_complete = task.objects.get(id=task_id)
            task_to_complete.task_status = 'completed'
            task_to_complete.save()
            if task_to_complete.task_schedule == 'one_time':
                #data = {'message':'task is now completed.'}
                messages.success(request, 'task is now completed.')
                return redirect('/cadence/projects/')
            elif task_to_complete.task_schedule in repeat_schedules:
                new_task_created = create_repeat_tasks(task_id)
                #data = {'message':new_task_created['message']}
                messages.success(request, new_task_created['message'])
                return redirect('/cadence/projects/')
        
        else:
            #data = {'message':'task is not valid.'}
            messages.error(request, 'task is not valid.')
            return redirect('/cadence/projects/')
    
class add_task_staff(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_task_staff_form = add_staff_to_task(request.GET or None)
        context = {'add_task_staff_form':add_task_staff_form}
        return render(request, 'pm/add_task_staff.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_task_staff_form = add_staff_to_task(data=request.POST or None)

        if add_task_staff_form.is_valid():
            new_task_staff = add_task_staff_form.save(commit=False)
            new_task_staff.created_date = timezone.now()
            new_task_staff.save()
            
            context = {'new_task_staff':new_task_staff}
            messages.success(request, 'task new task staff created: ' + str(new_task_staff.id))
            return redirect('/cadence/projects/')

        context = {'add_task_staff_form':add_task_staff_form}
        return render(request, 'pm/add_task_staff.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        add_task_staff_form = add_staff_to_task()
        add_task_staff_form = form_to_json_schema(add_task_staff_form)
        json_form = {'message':'This form is used to assign a task to staff members, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Assign Task to Staff Form', 
                          'description':'This form is used to assign a task to staff members, please provide the id of the task and user.', 
                          'form':add_task_staff_form,
                          'format':{'Assign Task to Staff Form': {
                        'task':'the id of the task from the tasks list',
                        'staff':'the id of the staff from the tasks list',
                        }}},
                     ]}
        return JsonResponse(json_form)

    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_task_staff_data = data['Assign Task to Staff Form']

        if all(key in new_task_staff_data for key in ['staff', 'task']):
            if task.objects.filter(id=new_task_staff_data['task']).exists():
                new_task_staff_data['task'] = task.objects.get(id=new_task_staff_data['task'])
            
            if User.objects.filter(id=new_task_staff_data['staff']):
                if user_info.objects.filter(user=new_task_staff_data['staff']).exists():
                    if user_info.objects.get(user=new_task_staff_data['staff']).user_type == 'staff':
                        new_task_staff_data['staff'] = user_info.objects.get(user=new_task_staff_data['staff'])
                    else:
                        data = {'message':'user must be staff, to user to task, please ensure your request follows the format below.',
                        'format':{'Assign Task to Staff Form': {
                        'task':'the id of the task from the tasks list',
                        'staff':'the id of the staff from the tasks list',
                        }}}
                        return JsonResponse(data)

            
            add_task_staff_form = add_staff_to_task(new_task_staff_data)
            
            if add_task_staff_form.is_valid():
                new_task_staff = add_task_staff_form.save(commit=False)
                new_task_staff.created_date = timezone.now()
                new_task_staff.save()
                
                data = {'message':'new staff was added to task.'}
                return JsonResponse(data)
            else:
                context = {'errors':add_task_staff_form.errors}
                print(add_task_staff_form.errors)
        
        data = {'message':'An error has occured, to user to task, please ensure your request follows the format below.',
                'format':{'Assign Task to Staff Form': {
                    'task':'the name of the task from the tasks list',
                    'staff':'the id of the staff from the tasks list',
                    }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_task_staff(request, task_staff_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if task_staff.objects.filter(id=task_staff_id).exists():
            task_staff_to_delete = task_staff.objects.get(id=task_staff_id)
            task_staff_to_delete.delete()
            
        data = {'message':'task staff deleted'}
        return redirect('/cadence/projects/')

class add_stakeholder_deliverable(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_stakeholder_to_deliverable_form = add_stakeholder_to_deliverable(request.GET or None)
        context = {'add_stakeholder_to_deliverable_form':add_stakeholder_to_deliverable_form}
        return render(request, 'pm/add_stakeholder_to_deliverable.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_stakeholder_to_deliverable_form = add_stakeholder_to_deliverable(data=request.POST or None)

        if add_stakeholder_to_deliverable_form.is_valid():
            new_deliverable_stakeholder = add_stakeholder_to_deliverable_form.save(commit=False)
            new_deliverable_stakeholder.created_date = timezone.now()
            new_deliverable_stakeholder.save()
            
            context = {'new_deliverable_stakeholder':new_deliverable_stakeholder}
            messages.success(request, 'task new deliverable stakeholder created: ' + str(new_deliverable_stakeholder.id))
            return redirect('/cadence/projects/')

        context = {'add_stakeholder_to_deliverable_form':add_stakeholder_to_deliverable_form}
        return render(request, 'pm/add_stakeholder_to_deliverable.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        add_stakeholder_to_deliverable_form = add_stakeholder_to_deliverable()
        add_stakeholder_to_deliverable_form = form_to_json_schema(add_stakeholder_to_deliverable_form)
        json_form = {'message':'This form is used to assign a deliverable to stakeholders, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Assign Deliverable to Stakeholder Form', 
                          'description':'This form is used to assign a deliverable to stakeholders, please provide the id of the stakeholder and deliverable.', 
                          'form':add_stakeholder_to_deliverable_form,
                          'format':{'Assign Deliverable to Stakeholder Form': {
                        'stake_holder':'the id of the stakeholder from the list',
                        'deliverable':'the id of the deliverbale from the list',
                        }}},
                     ]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_deliverable_stakeholder = data['Assign Deliverable to Stakeholder Form']

        if all(key in new_deliverable_stakeholder for key in ['stake_holder', 'deliverable']):
            if deliverable.objects.filter(id=new_deliverable_stakeholder['deliverable']).exists():
                new_deliverable_stakeholder['deliverable'] = deliverable.objects.get(id=new_deliverable_stakeholder['deliverable'])
            
            if User.objects.filter(id=new_deliverable_stakeholder['stake_holder']):
                if user_info.objects.filter(user=new_deliverable_stakeholder['stake_holder']).exists():
                    if user_info.objects.get(user=new_deliverable_stakeholder['stake_holder']).user_type == 'stakeholder':
                        new_deliverable_stakeholder['stake_holder'] = user_info.objects.get(user=new_deliverable_stakeholder['stake_holder'])
                    else:
                        data = {'message':'user must be stakeholder to be added to deliverabel, please ensure your request follows the format below.',
                        'format':{'Assign Deliverable to Stakeholder Form': {
                        'stake_holder':'the id of the stakeholder from the list',
                        'deliverable':'the id of the deliverbale from the list',
                        }}}
                        return JsonResponse(data)

            
            add_stakeholder_to_deliverable_form = add_stakeholder_to_deliverable(new_deliverable_stakeholder)
            
            if add_stakeholder_to_deliverable_form.is_valid():
                new_deliverable_stakeholder = add_stakeholder_to_deliverable_form.save(commit=False)
                new_deliverable_stakeholder.created_date = timezone.now()
                new_deliverable_stakeholder.save()
                
                data = {'message':'new stakeholder was added to deliverable.'}
                return JsonResponse(data)
            else:
                context = {'errors':add_stakeholder_to_deliverable_form.errors}
                print(add_stakeholder_to_deliverable_form.errors)
        
        data = {'message':'An error has occured, to add stakeholder to deliverable, please ensure your request follows the format below.',
                'format':{'Assign Deliverable to Stakeholder Form': {
                        'stake_holder':'the id of the stakeholder from the list',
                        'deliverable':'the id of the deliverbale from the list',
                        }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_stakeholder_deliverable(request, stakeholder_deliverable_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if deliverable_stakeholder.objects.filter(id=stakeholder_deliverable_id).exists():
            stakeholder_deliverable_to_delete = deliverable_stakeholder.objects.get(id=stakeholder_deliverable_id)
            stakeholder_deliverable_to_delete.delete()
            
        data = {'message':'deliverable stakeholder deleted'}
        return redirect('/cadence/projects/')



class add_stakeholder_project(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_stakeholder_to_project_form = add_stakeholder_to_project(request.GET or None)
        context = {'add_stakeholder_to_project_form':add_stakeholder_to_project_form}
        return render(request, 'pm/add_stakeholder_to_project.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_stakeholder_to_project_form = add_stakeholder_to_project(data=request.POST or None)

        if add_stakeholder_to_project_form.is_valid():
            new_project_stakeholder = add_stakeholder_to_project_form.save(commit=False)
            new_project_stakeholder.created_date = timezone.now()
            new_project_stakeholder.save()
            
            context = {'new_project_stakeholder':new_project_stakeholder}
            messages.success(request, 'task new project stakeholder created: ' + str(new_project_stakeholder.id))
            return redirect('/cadence/projects/')

        context = {'add_stakeholder_to_project_form':add_stakeholder_to_project_form}
        return render(request, 'pm/add_stakeholder_to_project.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        add_stakeholder_to_project_form = add_stakeholder_to_project()
        add_stakeholder_to_project_form = form_to_json_schema(add_stakeholder_to_project_form)
        json_form = {'message':'This form is used to assign a project to stakeholders, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Assign project to Stakeholder Form', 
                          'description':'This form is used to assign a project to stakeholders, please provide the id of the stakeholder and project.', 
                          'form':add_stakeholder_to_project_form,
                          'format':{'Assign project to Stakeholder Form': {
                        'stake_holder':'the id of the stakeholder from the list',
                        'project':'the id of the deliverbale from the list',
                        }}},
                     ]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_project_stakeholder = data['Assign project to Stakeholder Form']

        if all(key in new_project_stakeholder for key in ['stake_holder', 'project']):
            if project.objects.filter(id=new_project_stakeholder['project']).exists():
                new_project_stakeholder['project'] = project.objects.get(id=new_project_stakeholder['project'])
            
            if User.objects.filter(id=new_project_stakeholder['stake_holder']):
                if user_info.objects.filter(user=new_project_stakeholder['stake_holder']).exists():
                    if user_info.objects.get(user=new_project_stakeholder['stake_holder']).user_type == 'stakeholder':
                        new_project_stakeholder['stake_holder'] = user_info.objects.get(user=new_project_stakeholder['stake_holder'])
                    else:
                        data = {'message':'user must be stakeholder to be added to deliverabel, please ensure your request follows the format below.',
                        'format':{'Assign project to Stakeholder Form': {
                        'stake_holder':'the id of the stakeholder from the list',
                        'project':'the id of the deliverbale from the list',
                        }}}
                        return JsonResponse(data)

            
            add_stakeholder_to_project_form = add_stakeholder_to_project(new_project_stakeholder)
            
            if add_stakeholder_to_project_form.is_valid():
                new_project_stakeholder = add_stakeholder_to_project_form.save(commit=False)
                new_project_stakeholder.created_date = timezone.now()
                new_project_stakeholder.save()
                
                data = {'message':'new stakeholder was added to project.'}
                return JsonResponse(data)
            else:
                context = {'errors':add_stakeholder_to_project_form.errors}
                print(add_stakeholder_to_project_form.errors)
        
        data = {'message':'An error has occured, to add stakeholder to project, please ensure your request follows the format below.',
                'format':{'Assign project to Stakeholder Form': {
                        'stake_holder':'the id of the stakeholder from the list',
                        'project':'the id of the deliverbale from the list',
                        }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_stakeholder_project(request, stakeholder_project_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if project_stakeholder.objects.filter(id=stakeholder_project_id).exists():
            stakeholder_project_to_delete = project_stakeholder.objects.get(id=stakeholder_project_id)
            stakeholder_project_to_delete.delete()
            
        data = {'message':'project stakeholder deleted'}
        return redirect('/cadence/projects/')






class add_project_group(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_project_group_form = create_project_group(request.GET or None)
        context = {'add_project_group_form':add_project_group_form}
        return render(request, 'pm/add_project_group.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_project_group_form = create_project_group(data=request.POST or None)

        if add_project_group_form.is_valid():
            new_project_group = add_project_group_form.save(commit=False)
            new_project_group.created_date = timezone.now()
            new_project_group.save()
            
            context = {'new_project_group':new_project_group}
            messages.success(request, 'task new project group created: ' + str(new_project_group.id))
            return redirect('/cadence/projects/')

        context = {'add_project_group_form':add_project_group_form}
        return render(request, 'pm/add_project_group.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        add_project_group_form = create_project_group()
        add_project_group_form = form_to_json_schema(add_project_group_form)
        json_form = {'message':'This form is used to create project groups, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Create Project Group Form', 
                          'description':'This form is used to , please provide a project group name and description in the format provided.', 
                          'form':add_project_group_form,
                          'format':{'Create Project Group Form': {
                        'project_group_name':'unique project group name',
                        'project_group_description':'a detailed description of the project group and it\'s purpose',
                        }}},
                     ]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_project_group = data['Create Project Group Form']

        if all(key in new_project_group for key in ['project_group_name', 'project_group_description']):
            
            add_project_group_form = create_project_group(new_project_group)
            
            if add_project_group_form.is_valid():
                new_project_group = add_project_group_form.save(commit=False)
                new_project_group.created_date = timezone.now()
                new_project_group.save()
                
                data = {'message':'new project group created.'}
                return JsonResponse(data)
            else:
                context = {'errors':add_project_group_form.errors}
                print(add_project_group_form.errors)
        
        data = {'message':'An error has occured, to create project group, please ensure your request follows the format below.',
                'format':{'Create Project Group Form': {
                        'project_group_name':'unique project group name',
                        'project_group_description':'a detailed description of the project group and it\'s purpose',
                        }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_project_group(request, project_group_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if project_group.objects.filter(id=project_group_id).exists():
            project_group_to_delete = project_group.objects.get(id=project_group_id)
            project_group_to_delete.delete()
            
        data = {'message':'project group deleted'}
        return redirect('/cadence/projects/')


class add_deliverable_group(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_deliverable_group_form = create_deliverable_group(request.GET or None)
        context = {'add_deliverable_group_form':add_deliverable_group_form}
        return render(request, 'pm/add_deliverable_group.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_deliverable_group_form = create_deliverable_group(data=request.POST or None)

        if add_deliverable_group_form.is_valid():
            new_deliverable_group = add_deliverable_group_form.save(commit=False)
            new_deliverable_group.created_date = timezone.now()
            new_deliverable_group.save()
            
            context = {'new_deliverable_group':new_deliverable_group}
            messages.success(request, 'task new deliverable group created: ' + str(new_deliverable_group.id))
            return redirect('/cadence/projects/')

        context = {'add_deliverable_group_form':add_deliverable_group_form}
        return render(request, 'pm/add_deliverable_group.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        add_deliverable_group_form = create_deliverable_group()
        add_deliverable_group_form = form_to_json_schema(add_deliverable_group_form)
        json_form = {'message':'This form is used to create deliverable groups, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Create Deliverable Group Form', 
                          'description':'This form is used to , please provide a deliverable group name and description in the format provided.', 
                          'form':add_deliverable_group_form,
                          'format':{'Create Deliverable Group Form': {
                        'deliverable_group_name':'unique deliverable group name',
                        'deliverable_group_description':'a detailed deliverable of the project group and it\'s purpose',
                        }}},
                     ]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_deliverable_group = data['Create Deliverable Group Form']

        if all(key in new_deliverable_group for key in ['deliverable_group_name', 'deliverable_group_description']):
            
            add_deliverable_group_form = create_deliverable_group(new_deliverable_group)
            
            if add_deliverable_group_form.is_valid():
                new_deliverable_group = add_deliverable_group_form.save(commit=False)
                new_deliverable_group.created_date = timezone.now()
                new_deliverable_group.save()
                
                data = {'message':'new deliverable group created.'}
                return JsonResponse(data)
            else:
                context = {'errors':add_deliverable_group_form.errors}
                print(add_deliverable_group_form.errors)
        
        data = {'message':'An error has occured, to create deliverable group, please ensure your request follows the format below.',
                'format':{'Create Deliverable Group Form': {
                        'deliverable_group_name':'unique deliverable group name',
                        'deliverable_group_description':'a detailed deliverable of the project group and it\'s purpose',
                        }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_deliverable_group(request, deliverable_group_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if deliverable_group.objects.filter(id=deliverable_group_id).exists():
            deliverable_group_to_delete = deliverable_group.objects.get(id=deliverable_group_id)
            deliverable_group_to_delete.delete()
            
        data = {'message':'deliverable group deleted'}
        return redirect('/cadence/projects/')
    

class add_project_grouping(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_project_grouping_form = create_project_grouping(request.GET or None)
        context = {'add_project_grouping_form':add_project_grouping_form}
        return render(request, 'pm/add_project_grouping.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_project_grouping_form = create_project_grouping(data=request.POST or None)

        if add_project_grouping_form.is_valid():
            new_project_grouping = add_project_grouping_form.save(commit=False)
            new_project_grouping.created_date = timezone.now()
            new_project_grouping.save()
            
            context = {'new_project_grouping':new_project_grouping}
            messages.success(request, 'task new project grouping created: ' + str(new_project_grouping.id))
            return redirect('/cadence/projects/')

        context = {'add_project_grouping_form':add_project_grouping_form}
        return render(request, 'pm/add_project_grouping.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        create_project_grouping_form = create_project_grouping()
        create_project_grouping_form = form_to_json_schema(create_project_grouping_form)
        json_form = {'message':'This form is used to add a project to a group, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Add Project To Project Group Form', 
                          'description':'This form is used to add a project to a group, please provide project and project group id in the format provided.', 
                          'form':create_project_grouping_form,
                          'format':{'Add Project To Project Group Form': {
                        'project':'name of the project to add to group',
                        'project_group':'id of the project group',
                        }}},
                     ]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_project_grouping = data['Add Project To Project Group Form']

        if all(key in new_project_grouping for key in ['project', 'project_group']):
            if project_group.objects.filter(id=new_project_grouping['project_group']).exists():
                new_project_grouping['project_group'] = project_group.objects.get(id=new_project_grouping['project_group'])
            if project.objects.filter(project_name=new_project_grouping['project']).exists():
                new_project_grouping['project'] = project.objects.get(project_name=new_project_grouping['project'])

            create_project_grouping_form = create_project_grouping(new_project_grouping)
            
            if create_project_grouping_form.is_valid():
                new_project_grouping = create_project_grouping_form.save(commit=False)
                new_project_grouping.created_date = timezone.now()
                new_project_grouping.save()
                
                data = {'message':'project was added to group.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_project_grouping_form.errors}
                print(create_project_grouping_form.errors)
        
        data = {'message':'An error has occured, to add a project to a project group, please ensure your request follows the format below.',
                'format':{'Add Project To Project Group Form': {
                        'project':'name of the project to add to group',
                        'project_group':'id of the project group',
                        }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_project_grouping(request, project_grouping_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if project_grouping.objects.filter(id=project_grouping_id).exists():
            project_grouping_id_to_delete = project_grouping.objects.get(id=project_grouping_id)
            project_grouping_id_to_delete.delete()
            
        data = {'message':'project grouping deleted'}
        return redirect('/cadence/projects/')


class add_deliverable_grouping(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_deliverable_grouping_form = create_deliverable_grouping(request.GET or None)
        context = {'add_deliverable_grouping_form':add_deliverable_grouping_form}
        return render(request, 'pm/add_deliverable_grouping.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_deliverable_grouping_form = create_deliverable_grouping(data=request.POST or None)

        if add_deliverable_grouping_form.is_valid():
            new_deliverable_grouping = add_deliverable_grouping_form.save(commit=False)
            new_deliverable_grouping.created_date = timezone.now()
            new_deliverable_grouping.save()
            
            context = {'new_deliverable_grouping':new_deliverable_grouping}
            messages.success(request, 'task new deliverable grouping created: ' + str(new_deliverable_grouping.id))
            return redirect('/cadence/projects/')

        context = {'add_deliverable_grouping_form':add_deliverable_grouping_form}
        return render(request, 'pm/add_deliverable_grouping.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        create_deliverable_grouping_form = create_deliverable_grouping()
        create_deliverable_grouping_form = form_to_json_schema(create_deliverable_grouping_form)
        json_form = {'message':'This form is used to add a deliverable to a group, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Add Deliverable To Deliverable Group Form', 
                          'description':'This form is used to add a deliverable to a group, please provide deliverable and deliverable group id in the format provided.', 
                          'form':create_deliverable_grouping_form,
                          'format':{'Add Deliverable To Deliverable Group Form': {
                        'deliverable':'id of the deliverable to add to group',
                        'deliverable_group':'id of the deliverable group',
                        }}},
                     ]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_deliverable_grouping = data['Add Deliverable To Deliverable Group Form']

        if all(key in new_deliverable_grouping for key in ['deliverable', 'deliverable_group']):
            if deliverable_group.objects.filter(id=new_deliverable_grouping['deliverable_group']).exists():
                new_deliverable_grouping['deliverable_group'] = deliverable_group.objects.get(id=new_deliverable_grouping['deliverable_group'])
            if deliverable.objects.filter(id=new_deliverable_grouping['deliverable']).exists():
                new_deliverable_grouping['deliverable'] = deliverable.objects.get(id=new_deliverable_grouping['deliverable'])

            create_deliverable_grouping_form = create_deliverable_grouping(new_deliverable_grouping)
            
            if create_deliverable_grouping_form.is_valid():
                new_deliverable_grouping = create_deliverable_grouping_form.save(commit=False)
                new_deliverable_grouping.created_date = timezone.now()
                new_deliverable_grouping.save()
                
                data = {'message':'deliverable was added to group.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_deliverable_grouping_form.errors}
                print(create_deliverable_grouping_form.errors)
        
        data = {'message':'An error has occured, to add a project to a project group, please ensure your request follows the format below.',
                'format':{'Add Deliverable To Deliverable Group Form': {
                        'project':'id of the deliverable to add to group',
                        'project_group':'id of the deliverable group',
                        }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_deliverable_grouping(request, deliverable_grouping_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if deliverable_grouping.objects.filter(id=deliverable_grouping_id).exists():
            deliverable_grouping_id_to_delete = deliverable_grouping.objects.get(id=deliverable_grouping_id)
            deliverable_grouping_id_to_delete.delete()
            
        data = {'message':'deliverable grouping deleted'}
        return redirect('/cadence/projects/')

class create_prerequisites(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_task_prerequisite_form = add_task_prerequisite(request.GET or None)
        context = {'add_task_prerequisite_form':add_task_prerequisite_form}
        return render(request, 'pm/add_prerequisite_to_task.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_task_prerequisite_form = add_task_prerequisite(data=request.POST or None)

        if add_task_prerequisite_form.is_valid():
            new_task_prerequisite = add_task_prerequisite_form.save(commit=False)
            new_task_prerequisite.created_date = timezone.now()
            new_task_prerequisite.save()
            
            context = {'new_task_prerequisite':new_task_prerequisite}
            messages.success(request, 'new task prerequisite created: ' + str(new_task_prerequisite.id))
            return redirect('/cadence/projects/')

        context = {'add_task_prerequisite_form':add_task_prerequisite_form}
        return render(request, 'pm/add_prerequisite_to_task.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        add_task_prerequisite_form = add_task_prerequisite()
        add_task_prerequisite_form = form_to_json_schema(add_task_prerequisite_form)
        json_form = {'message':'This form is used to add a prerequisite to a task, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Add Task Prerequisite Form', 
                          'description':'This form is used to add a prerequisite to a task.', 
                          'form':add_task_prerequisite_form,
                          'format':{'Add Task Prerequisite Form': {
                        'task_relationship':'see list in form',
                        'main_task':'id of the main task',
                        'second_task':'id of the second task',
                        }}},
                     ]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_task_prerequisite = data['Add Task Prerequisite Form']

        if all(key in new_task_prerequisite for key in ['task_relationship', 'main_task', 'second_task']):
            if task.objects.filter(id=new_task_prerequisite['main_task']).exists():
                new_task_prerequisite['main_task'] = task.objects.get(id=new_task_prerequisite['main_task'])
            if task.objects.filter(id=new_task_prerequisite['second_task']).exists():
                new_task_prerequisite['second_task'] = task.objects.get(id=new_task_prerequisite['second_task'])

            create_task_prerequisite_form = add_task_prerequisite(new_task_prerequisite)
            
            if create_task_prerequisite_form.is_valid():
                new_task_prerequisite = create_task_prerequisite_form.save(commit=False)
                new_task_prerequisite.created_date = timezone.now()
                new_task_prerequisite.save()
                
                data = {'message':'prerequisite was added to task.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_task_prerequisite_form.errors}
                print(create_task_prerequisite_form.errors)
        
        data = {'message':'An error has occured, to add a prerequisite to a task, please ensure your request follows the format below.',
                'format':{'Add Task Prerequisite Form': {
                        'task_relationship':'see list in form',
                        'main_task':'id of the main task',
                        'second_task':'id of the second task',
                        }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_task_prerequisite(request, task_prerequisite_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if task_prerequisite.objects.filter(id=task_prerequisite_id).exists():
            task_prerequisite_id_to_delete = task_prerequisite.objects.get(id=task_prerequisite_id)
            task_prerequisite_id_to_delete.delete()
            
        data = {'message':'task prerequisite deleted'}
        return redirect('/cadence/projects/')
    
class user_message_view(View):
    def get(self, request, message_sender):
        if check_authentication(request) != None:
            return check_authentication(request)
        context = {}
        context['message_sender'] = message_sender
        request_user = User.objects.get(username=request.user)
        request_user = user_info.objects.get(user=request_user)
        all_user_messages_dict = user_messages.objects.filter(user_reciver=request_user) | user_messages.objects.filter(message_sender=request_user.pk)
        all_users_messages = pd.DataFrame(all_user_messages_dict.values())

        list_of_sender_1 = all_users_messages["message_sender"].unique().tolist()
        list_of_sender_2 = all_users_messages["user_reciver_id"].astype(str).unique().tolist()
        list_of_sender = list(set(list_of_sender_1 + list_of_sender_2))
        output_list = []
        for i, e_sender in enumerate(list_of_sender):
            try:
                output_list.append({'id':f"{e_sender}", 'value':f"{user_info.objects.get(pk=e_sender).user.username}"})

            except:
                output_list.append({'id':f"{e_sender}", 'value':f"{e_sender}"})
        
        messages_to_show = all_users_messages[(all_users_messages['message_sender']==message_sender) | (all_users_messages['user_reciver_id'].astype(str)==message_sender)]
        
        if message_sender == 'system':
            messages_to_show = all_users_messages[all_users_messages['message_type']=='system']
            add_user_messages_form = add_user_messages(request.GET or None, initial={"message_sender":request_user.pk})   
        elif message_sender == 'scheduler':
            messages_to_show = all_users_messages[all_users_messages['message_sender']=='scheduler']
            add_user_messages_form = add_user_messages(request.GET or None, initial={"message_sender":request_user.pk})
        else:
            user_reciver_u = User.objects.get(id=message_sender)
            user_reciver = user_info.objects.get(user=user_reciver_u)
            add_user_messages_form = add_user_messages(request.GET or None, initial={"user_reciver":user_reciver, "message_sender":request_user})

            if user_reciver.user_type == "stakeholder":
                if task.objects.filter(task_name=f"stakeholder-task-{user_reciver_u.id}").exists():
                    task_to_return = task.objects.get(task_name=f"stakeholder-task-{user_reciver_u.id}")
                    task_to_return_df = pd.DataFrame(task.objects.filter(task_name=f"stakeholder-task-{user_reciver_u.id}").values())
                    context['task_to_return'] = task_to_return_df.to_dict('records')
                    context['project_name'] = task_to_return.task_project.project_name

                    task_attachements_to_return = pd.DataFrame(task_attachement.objects.filter(attachemnet_task_id=task_to_return.id).values())
                    if not task_attachements_to_return.empty:
                        context['task_attachements_to_return'] = task_attachements_to_return.to_dict('records')
                    
                    task_comments_to_return = pd.DataFrame(task_comments.objects.filter(comment_task_id=task_to_return.id).values())
                    if not task_comments_to_return.empty:
                        context['task_comments_to_return'] = task_comments_to_return.to_dict('records')
                    
                    context['task_attachement_form'] = add_task_attachement(request.GET or None)
                    context['task_comment_form'] = add_task_comments(request.GET or None)


        context['add_user_messages_form'] = add_user_messages_form
        context['list_of_sender'] = output_list
        context['messages_to_show'] = messages_to_show.to_dict('records')
        return render(request, 'pm/user_message_view.html', context)
    
    def post(self, request, message_sender):
        if check_authentication(request) != None:
            return check_authentication(request)
        context = {}
        context['message_sender'] = message_sender
        request_user = User.objects.get(username=request.user)
        add_user_messages_form = add_user_messages(data=request.POST or None)

        if add_user_messages_form.is_valid():
            new_user_messages = add_user_messages_form.save(commit=False)
            new_user_messages.created_date = timezone.now()
            new_user_messages.message_sender = str(user_info.objects.get(user=request_user).pk)
            new_user_messages.save()
            
            context = {'new_user_messages':new_user_messages}
            messages.success(request, 'new user_message created: ' + str(new_user_messages.id))
            
        return redirect(f'/cadence/user_message_view/{message_sender}')


class add_user_message(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_user_messages_form = add_user_messages(request.GET or None)
        context = {'add_user_messages_form':add_user_messages_form}
        return render(request, 'pm/add_user_message.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        request_user = User.objects.get(username=request.user)
        add_user_messages_form = add_user_messages(data=request.POST or None)

        if add_user_messages_form.is_valid():
            new_user_messages = add_user_messages_form.save(commit=False)
            new_user_messages.message_sender = user_info.objects.get(user=request_user)
            new_user_messages.created_date = timezone.now()
            new_user_messages.save()
            
            context = {'new_user_messages':new_user_messages}
            messages.success(request, 'new user_message created: ' + str(new_user_messages.id))
            return redirect('/cadence/projects/')

        context = {'add_user_messages_form':add_user_messages_form}
        return render(request, 'pm/add_user_message.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        add_user_messages_form = add_user_messages()
        add_user_messages_form = form_to_json_schema(add_user_messages_form)
        json_form = {'message':'This form is used to send a user message, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Send User Message Form', 
                          'description':'This form is used to send a user message.', 
                          'form':add_user_messages_form,
                          'format':{'Send User Message Form': {
                        'message_type':'see list in form',
                        'message':'message to send to user',
                        }}},
                     ]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_user_messages = data['Send User Message Form']

        if all(key in new_user_messages for key in ['message_type', 'message']):

            create_user_messages_form = add_user_messages(new_user_messages)
            if create_user_messages_form.is_valid():
                new_user_messages = create_user_messages_form.save(commit=False)
                new_user_messages.created_date = timezone.now()
                new_user_messages.save()
                
                data = {'message':'message was sent to user.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_user_messages_form.errors}
                print(create_user_messages_form.errors)
        
        data = {'message':'An error has occured, to send a message, please ensure your request follows the format below.',
                'format':{'Send User Message Form': {
                        'message_type':'see list in form',
                        'message':'message to send to user',
                        }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_user_messages(request, user_messages_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if user_messages.objects.filter(id=user_messages_id).exists():
            user_messages_id_to_delete = user_messages.objects.get(id=user_messages_id)
            user_messages_id_to_delete.delete()
            
        data = {'message':'user message deleted'}
        return redirect('/cadence/projects/')

class add_task_status(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_task_status_list_form = add_task_status_list(request.GET or None)
        context = {'add_task_status_list_form':add_task_status_list_form}
        return render(request, 'pm/add_task_status_list.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        add_task_status_list_form = add_task_status_list(data=request.POST or None)

        if add_task_status_list_form.is_valid():
            new_task_status_list = add_task_status_list_form.save(commit=False)
            new_task_status_list.created_date = timezone.now()
            new_task_status_list.save()
            
            context = {'new_task_status_list':new_task_status_list}
            messages.success(request, 'new task status created: ' + str(new_task_status_list.id))
            return redirect('/cadence/projects/')

        context = {'add_task_status_list_form':add_task_status_list_form}
        return render(request, 'pm/add_task_status_list.html.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        add_task_status_list_form = add_task_status_list()
        add_task_status_list_form = form_to_json_schema(add_task_status_list_form)
        json_form = {'message':'This form is used to add a task status to a task, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Add Task Status Form', 
                          'description':'This form is used to add a status to a task.', 
                          'form':add_task_status_list_form,
                          'format':{'Add Task Status Form': {
                        'status_of_task':'see list in form',
                        'task_observed':'id of the task',
                        'task_message':'task message, notes, and/or comments',
                        }}},
                     ]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_task_status_list = data['Add Task Status Form']

        if all(key in new_task_status_list for key in ['task_observed', 'status_of_task', 'task_message']):
            if task.objects.filter(id=new_task_status_list['task_observed']).exists():
                new_task_status_list['task_observed'] = task.objects.get(id=new_task_status_list['task_observed'])
            
            create_task_status_list_form = add_task_status_list(new_task_status_list)
            
            if create_task_status_list_form.is_valid():
                new_task_status_list = create_task_status_list_form.save(commit=False)
                new_task_status_list.created_date = timezone.now()
                new_task_status_list.save()
                
                data = {'message':'status was added to task.'}
                return JsonResponse(data)
            else:
                context = {'errors':create_task_status_list_form.errors}
                print(create_task_status_list_form.errors)
        
        data = {'message':'An error has occured, to add a status to a task, please ensure your request follows the format below.',
                'format':{'Add Task Status Form': {
                        'status_of_task':'see list in form',
                        'task_observed':'id of the task',
                        'task_message':'task message, notes, and/or comments',
                        }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_task_status_list(request, task_status_list_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if task_status_list.objects.filter(id=task_status_list_id).exists():
            task_status_list_id_to_delete = task_status_list.objects.get(id=task_status_list_id)
            task_status_list_id_to_delete.delete()
            
        data = {'message':'task status deleted'}
        return redirect('/cadence/projects/')


class task_management(View):
    def create_task_comments(request, project_name, task_id):
        if check_authentication(request) != None:
            return check_authentication(request)

        context = {}
        context['project_name'] = project_name
        context['task_id'] = task_id
        get_user_info = user_info.objects.get(user_id=request.user.id)
        context['user_info'] = get_user_info

        create_task_comment = add_task_comments(data=request.POST or None)

        if create_task_comment.is_valid():
            new_task_comment = create_task_comment.save(commit=False)
            new_task_comment.created_date = timezone.now()
            new_task_comment.task_comment_owner = get_user_info
            new_task_comment.comment_task = task.objects.get(id=task_id)
            new_task_comment.task_comment_type = 'u'
            new_task_comment.save()
            
            context = {'new_task_comment':new_task_comment}
            messages.success(request, 'created: new task comment ' + str(new_task_comment.id))
            return redirect(f'/cadence/projects/{project_name}/{task_id}/')

        return redirect(f'/cadence/projects/{project_name}/{task_id}/')
    
    def create_task_comments_get_api(request, project_name, task_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        create_task_comment = add_task_comments()
        create_task_comment = form_to_json_schema(create_task_comment)
        json_form = {'message':'This form is used to add a task prerequisite, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Add Task Comments Form', 
                          'description':'This form is used to add a task comment, please provide the task id, and the comment to add.', 
                          'form':create_task_comment,
                          'format':{'Add Task Comments Form': {
                        'comment_task':'id of the task',
                        'comment':'the comment to be added',
                        }}},
                     ]}
        
        return JsonResponse(json_form)
    
    @csrf_exempt
    def create_task_comments_post_api(request, project_name, task_id):
        if check_authentication(request) != None:
            return check_authentication(request)

        context = {}
        context['project_name'] = project_name
        context['task_id'] = task_id
        get_user_info = user_info.objects.get(user_id=request.user.id)
        context['user_info'] = get_user_info
        
        data = json.loads(request.body.decode('utf-8'))
        create_task_comment = data['Add Task Comments Form']

        if all(key in create_task_comment for key in ['comment_task', 'comment']):
            new_task_comment = task_comments(comment=create_task_comment['comment'])
            if task.objects.filter(id=create_task_comment['comment_task']).exists():
                new_task_comment.comment_task = task.objects.get(id=create_task_comment['comment_task'])
                new_task_comment.created_date = timezone.now()
                new_task_comment.task_comment_owner = get_user_info
                new_task_comment.task_comment_type = 'a'
                new_task_comment.save()
                
                data = {'message':'task comment was added.'}
                return JsonResponse(data)
        
        data = {'message':'An error has occured, to add a task prerquisite, please ensure your request follows the format below.',
                'format':{'Add Task Comments Form': {
                        'comment_task':'id of the task',
                        'comment':'the comment to be added',
                        }}}
        return JsonResponse(data)
    
    def create_task_attachements(request, project_name, task_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if not task.objects.filter(id=task_id).exists():
            return redirect('/cadence/projects/')

        context = {}
        context['project_name'] = project_name
        context['task_id'] = task_id
        get_user_info = user_info.objects.get(user_id=request.user.id)
        context['user_info'] = get_user_info

        new_task_attachement = task_attachement(attachemnet_owner=get_user_info, 
                                                attachemnet_task=task.objects.get(id=task_id),
                                                datetime_created=timezone.now(),)
        temp_file_path = check_files(request)
        if temp_file_path['state'] == '1':
            new_task_attachement.attachement = temp_file_path['file_path']
        else:
            messages.success(request, 'file not saved')
            return redirect(f'/cadence/projects/{project_name}/{task_id}/')

        new_task_attachement.save()
        
        context = {'new_task_comment':new_task_attachement}
        messages.success(request, 'created: new task attachement ' + str(new_task_attachement.id))
        return redirect(f'/cadence/projects/{project_name}/{task_id}/')

class manage_projects(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        context = get_user_dashboard_info(request)
        return render(request, 'pm/manage_projects.html', context)
    
    def get_deliverable_data(request, deliverable_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        context = get_user_dashboard_info(request)
        get_user_info = user_info.objects.get(user_id=request.user.id)

        try:
            get_deliverable = deliverable.objects.get(id=deliverable_id)
            context['get_deliverable'] = get_deliverable
        except deliverable.DoesNotExist:
            return redirect('/cadence/projects/')
        
        get_project = pd.DataFrame(project.objects.filter(project_name=get_deliverable.deliverable_project_id).values())
        get_project['project_name_for_link'] = get_project['project_name'].str.replace(' ', '_')
        context['get_project'] = get_project.to_dict('records')
        get_stakeholders = pd.DataFrame(deliverable_stakeholder.objects.filter(deliverable_id=get_deliverable.id).values())
        if not get_stakeholders.empty:
            get_all_stakeholders = pd.DataFrame()
            for i, e_stakeholders in enumerate(get_stakeholders['stake_holder_id'].unique()):
                temp_stakeholder = pd.DataFrame(user_info.objects.filter(user_id=e_stakeholders).values())
                temp_user = pd.DataFrame(User.objects.filter(id=e_stakeholders).values())
                temp_user = temp_user.drop(columns=['password'])
                temp_stakeholder = pd.merge(temp_stakeholder, temp_user, left_on='user_id', right_on="id", how='left')
                get_all_stakeholders = pd.concat([temp_stakeholder, get_all_stakeholders])
            
            context['get_stakeholders'] = get_all_stakeholders.to_dict('records')
        if get_user_info.user_type == "staff":
            get_tasks = pd.DataFrame(task.objects.filter(task_deliverable_id=get_deliverable.id))
            context['get_tasks'] = get_tasks.to_dict('records')
        
        return render(request, 'pm/manage_projects.html', context)

    def get_project_data(request, project_name):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        context = get_user_dashboard_info(request)
        get_user_info = user_info.objects.get(user_id=request.user.id)
        temp_context = get_project_info(project_name)
        context.update(temp_context)
        temp_project = project.objects.get(project_name=str(project_name).replace('_', ' '))

        
        if project_stakeholder.objects.filter(sh_project=temp_project).exists():
            get_stakeholders = pd.DataFrame(project_stakeholder.objects.filter(sh_project=temp_project).values())
            get_all_stakeholders = pd.DataFrame()
            for i, e_stakeholders in enumerate(get_stakeholders['stake_holder_id'].unique()):
                temp_stakeholder = pd.DataFrame(user_info.objects.filter(user_id=e_stakeholders).values())
                temp_user = pd.DataFrame(User.objects.filter(id=e_stakeholders).values())
                temp_user = temp_user.drop(columns=['password'])
                temp_stakeholder = pd.merge(temp_stakeholder, temp_user, left_on='user_id', right_on="id", how='left')
                get_all_stakeholders = pd.concat([temp_stakeholder, get_all_stakeholders])
            
            context['get_stakeholders'] = get_all_stakeholders.to_dict('records')

        return render(request, 'pm/manage_projects.html', context)
    
    def get_project_task_data(request, project_name, task_id):
        if check_authentication(request) != None:
            return check_authentication(request)

        context = get_user_dashboard_info(request)
        get_user_info = user_info.objects.get(user_id=request.user.id)
        context['task_id'] = task_id

        temp_context = get_project_info(project_name)
        context.update(temp_context)
        
        if task.objects.filter(id=task_id).exists():
            task_to_return = pd.DataFrame(task.objects.filter(id=task_id).values())
            context['task_to_return'] = task_to_return.to_dict('records')

            task_attachements_to_return = pd.DataFrame(task_attachement.objects.filter(attachemnet_task_id=task_id).values())
            if not task_attachements_to_return.empty:
                context['task_attachements_to_return'] = task_attachements_to_return.to_dict('records')
            
            task_comments_to_return = pd.DataFrame(task_comments.objects.filter(comment_task_id=task_id).values())
            if not task_comments_to_return.empty:
                context['task_comments_to_return'] = task_comments_to_return.to_dict('records')
            
            task_prerequisites_to_return = pd.DataFrame(task_prerequisite.objects.filter(main_task_id=task_id).values())
            if not task_prerequisites_to_return.empty:
                task_prerequisites_to_return = pd.DataFrame(task.objects.filter(id__in=task_prerequisites_to_return['second_task_id'].tolist()).values())
                context['task_prerequisites_to_return'] = task_prerequisites_to_return.to_dict('records')

            task_object = task.objects.get(id=task_id)
            task_observed={'task_observed':task_object}
            main_task={'main_task':task_object}
            context['task_prerequisite_form'] = add_task_prerequisite(request.GET or None, initial=main_task)
            context['task_status_list_form'] = add_task_status_list(request.GET or None, initial=task_observed)
            
            context['task_attachement_form'] = add_task_attachement(request.GET or None)
            context['task_comment_form'] = add_task_comments(request.GET or None)

            task_staff_to_return = pd.DataFrame(task_staff.objects.filter(task_id=task_id).values())
            if not task_staff_to_return.empty:
                task_staff_to_return = task_staff_to_return.drop_duplicates(subset=['task_id', 'staff_id'])
                task_staff_to_return = pd.DataFrame(user_info.objects.filter(user_id__in = task_staff_to_return['staff_id'].to_list()).values())
                context['task_staff_to_return'] = task_staff_to_return.to_dict('records')

        return render(request, 'pm/manage_projects.html', context)