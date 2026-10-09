# Copyright 2026 Axiomatic Lab
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://apache.org
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

import requests, markdown, json, sqlite3
import pandas as pd
from sqlalchemy import create_engine
from django.forms.models import model_to_dict
from django.conf import settings
from django.contrib import messages
from django.utils import timezone


from portfolio.forms import DetailedSignUpForm, add_new_users, create_new_lead_form
from portfolio.models import campaign, campaign_funnel
from synapse.models import user_info, User

from pm.models import project, task, project_stakeholder

class authenticate_users(View):
    def get(self, request):
        user_auth_form = AuthenticationForm(request.GET or None)

        context = {'user_auth_form':user_auth_form}
        return render(request, './login.html', context)
    
    def post(self, request):
        user_auth_form = AuthenticationForm(data=request.POST)

        if user_auth_form.is_valid():
            username = user_auth_form.cleaned_data.get('username')
            password = user_auth_form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                
                return redirect('/daemon/model_chat_messages/1')

        context = {'user_auth_form':user_auth_form}
        return render(request, './login.html', context)

class create_new_user(View):
    def get(self, request):
        create_user_form = UserCreationForm(request.GET or None)
        context = {'create_user_form':create_user_form,}
        return render(request, './signup.html', context)
    
    def post(self, request):
        create_user_form = UserCreationForm(request.POST or None)

        if create_user_form.is_valid():
            new_user = create_user_form.save(commit=False)
            new_user.save()
            return redirect("/login")
        else:
            create_user_form = UserCreationForm(request.POST or None)

        context = {'create_user_form':create_user_form,}
        
        return render(request, './signup.html', context)

class about_us(View):
    def about_us(request):
        context = {}

        with open('about_us.md', 'r', encoding='utf-8') as f:
            text = f.read()

        context['content'] = markdown.markdown(text)

        return render(request, './about_us.html', context)
    
    def privacy(request):
        context = {}

        with open('privacy_policy.md', 'r', encoding='utf-8') as f:
            text = f.read()

        context['content'] = markdown.markdown(text)

        return render(request, './privacy.html', context)
    
    def terms(request):
        context = {}

        with open('terms_of_service.md', 'r', encoding='utf-8') as f:
            text = f.read()

        context['content'] = markdown.markdown(text)

        return render(request, './terms.html', context)

    def llms(request):
            context = {}
    
            with open('llms.md', 'r', encoding='utf-8') as f:
                text = f.read()
    
            context['content'] = markdown.markdown(text)
    
            return render(request, './terms.html', context)

class contact_us(View):
    def get(self, request):
        context = {}

        DetailedSignUpForm_form = create_new_lead_form(request.GET or None)

        context['DetailedSignUpForm_form'] = DetailedSignUpForm_form

        return render(request, './contact_us.html', context)
    
    def post(self, request):
        context = {}

        if request.method == 'POST':
            DetailedSignUpForm_form = create_new_lead_form(request.POST)
            if DetailedSignUpForm_form.is_valid():
                DetailedSignUpForm_form.save()
                
                return redirect('/login')
        else:
            DetailedSignUpForm_form = create_new_lead_form()

        context['DetailedSignUpForm_form'] = DetailedSignUpForm_form
        return render(request, './contact_us.html', context)


models_dataset = [
{
"name": "Llama - Ultravox",
"total_params": 1.0,
"active_params": 1.0,
"model_info": {"model_type":"Audio to Text",
                "4-bit (Q4)":"ggml-org/ultravox-v0_5-llama-3_2-1b-GGUF:Q4_K_M",
                "8-bit (Q8)":"ggml-org/ultravox-v0_5-llama-3_2-1b-GGUF:Q8_0",}
},
{
"name": "IBM - Granite 4.2",
"total_params": 3.0,
"active_params": 3.0,
"model_info": {"model_type":"Recommended 3B Model",
                "4-bit (Q4)":"ibm-granite/granite-4.2-3b-GGUF:Q4_0",
                "8-bit (Q8)":"ibm-granite/granite-4.2-3b-GGUF:Q8_0",
                "FP16 (Unquantized)":"ibm-granite/granite-4.2-3b-GGUF:BF16",},
},
{
"name": "Mistral 8B Reasoning",
"total_params": 8.0,
"active_params": 8.0,
"model_info": {"model_type":"Recommended 3B Model",
                "4-bit (Q4)":"mistralai/Ministral-3-8B-Reasoning-2512-GGUF:Q4_K_M",
                "8-bit (Q8)":"mistralai/Ministral-3-8B-Reasoning-2512-GGUF:Q8_0",
                "FP16 (Unquantized)":"mistralai/Ministral-3-8B-Reasoning-2512-GGUF:BF16",},
},
{
"name": "Ministral 3 14B ",
"total_params": 14.0,
"active_params": 14.0,
"model_info": {"model_type":"Alternative 12-14B Model",
                "4-bit (Q4)":"mistralai/Ministral-3-14B-Instruct-2512-GGUF:Q4_K_M",
                "8-bit (Q8)":"mistralai/Ministral-3-14B-Instruct-2512-GGUF:Q8_0",
                "FP16 (Unquantized)":"mistralai/Ministral-3-14B-Instruct-2512-GGUF:BF16",},
},
]


class home_page(View):
    def get(self, request):
        context = {}

        context['django_models_list'] = models_dataset
        return render(request, "temp_html.html", context)
    
    def post(self, request):
        funnel_id = 3
        context = {}

        if campaign_funnel.objects.filter(id=funnel_id).exists():
            temp_campaign_funnel = campaign_funnel.objects.get(id=funnel_id)
            context['campaign_funnel'] = model_to_dict(temp_campaign_funnel)

            temp_funnel_name = str(temp_campaign_funnel.funnel_name).replace(" ", "_")

            temp_user_lead = create_new_lead_form(request.POST)

            if temp_user_lead.is_valid():
                new_lead = temp_user_lead.save(commit=False)
                new_lead.created_date = timezone.now()
                new_lead.campaign_funnel = temp_campaign_funnel

                new_lead.save()
                print("yes, ", new_lead)
                
                temp_output_dict = {"lead_id":str(new_lead.id)}
                for key, value in json.loads(temp_campaign_funnel.funnel_input_form).items():
                    if key in request.POST.keys():
                        temp_output_dict[key] = request.POST[key]
                output_df = pd.DataFrame(temp_output_dict, index=[0])

                db_conf = settings.DATABASES['default']
                db_conn = sqlite3.connect(db_conf['NAME'])
            
                try:
                    output_df.to_sql(temp_funnel_name, db_conn, if_exists="append", index=False)
                    messages.success(request, "Thank you for your interest, we will be in touch soon!.")

                    temp_project_name = f"lead-{str(new_lead.id)}"
                    temp_task_name = f"lead-task-{str(new_lead.id)}"
                    if project.objects.filter(project_name=temp_project_name).exists():
                        user_project = project.objects.get(project_name=temp_project_name)
                    else:
                        temp_product = project.objects.create(project_name=temp_project_name,
                                                            pm_owner= user_info.objects.get(user=User.objects.get(username="daniel")),
                                                            project_description=f"Client Overview for {new_lead.last_name}, {new_lead.first_name}",
                                                            date_created=timezone.now())
                        
                        temp_task = task.objects.create(date_created=timezone.now(),
                                                        task_name=temp_task_name,
                                                        task_description=f"Client Overview for {new_lead.last_name}, {new_lead.first_name}",
                                                        start_date = timezone.now(), soft_due_date = timezone.now(), hard_due_date = timezone.now(),
                                                        task_project=temp_product)

                    return redirect("/")
                except:
                    new_lead.delete()
                    messages.warning(request, "Something went wrong, please try again.")
                    context["new_lead_form"] = create_new_lead_form()
            else:
                context["new_lead_form"] = create_new_lead_form(request.POST)

            temp_input_form = json.loads(temp_campaign_funnel.funnel_input_form)
            for key in temp_input_form.keys():
                if not isinstance(temp_input_form[key], list):
                    temp_input_form[key] = [temp_input_form[key]]
            context["funnel_input_form"] = temp_input_form
            
            if temp_campaign_funnel.funnel_hero_img:
                context["funnel_hero_img"] = temp_campaign_funnel.funnel_hero_img
            else:
                with open(temp_campaign_funnel.funnel_hero_md, 'r', encoding='utf-8') as f:
                    text = f.read()
                context["funnel_hero_md"] = markdown.markdown(text)

        return render(request, "home.html", context)