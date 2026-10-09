from django.shortcuts import render, redirect
from django.views import View
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.forms.models import model_to_dict

from django.conf import settings
from django.contrib import messages

import requests, markdown, json, sqlite3
import pandas as pd

from .models import *
from .forms import *

from pm.models import project, task, project_stakeholder


def check_authentication(check_request):
    if not check_request.user.is_authenticated:
        return redirect("/login")
    elif not check_request.user.is_staff:
        return redirect("/login")
    
        

class create_new_projects(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        new_project_form = add_new_projects(request.GET or None)

        context = {"new_project_form":new_project_form}
        return render(request, "portfolio/create_new_project.html", context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        new_project_form = add_new_projects(request.POST or None)

        if new_project_form.is_valid():
            new_project = new_project_form.save(commit=False)
            new_project.date_created = timezone.now()
            new_project.save()

            new_project_form = add_new_projects()
            messages.success(request, 'project created')      

        context = {"new_project_form":new_project_form}
        return render(request, "portfolio/create_new_project.html", context)

class view_project(View):
    def get(self, request, project_id):
        context = {}
        context['project_id'] = str(project_id)
        if portfolio_projects.objects.filter(slug=project_id).exists():
            project_to_see = portfolio_projects.objects.get(slug=project_id)
            print(project_to_see, project_to_see.project_type)
            if project_to_see.project_type == "open_source":
                get_github_info = requests.get(f"https://api.github.com/repos/{project_to_see.project_repo_link}")
                get_github_readme = requests.get(f"https://api.github.com/repos/{project_to_see.project_repo_link}/readme", headers={"Accept": "application/vnd.github.raw+json"})
                if get_github_readme.status_code == 200:
                    github_readme = get_github_readme.text
                    context['github_readme'] = markdown.markdown(github_readme)
                
                if get_github_info.status_code == 200:
                    github_info = get_github_info.json()
                    context['github_info'] = github_info

                context['project_to_see'] = model_to_dict(project_to_see)

                return render(request, "portfolio/view_project.html", context)

            elif project_to_see.project_type == "services":
                context['services_body'] = project_to_see.project_description
                context['services_context'] = project_to_see.project_casestudy
                context['campaign_funnel_id'] = int(project_to_see.project_repo_link)
                if campaign_funnel.objects.filter(id=int(project_to_see.project_repo_link)).exists():
                    temp_campaign_funnel = campaign_funnel.objects.get(id=project_to_see.project_repo_link)
                    context['campaign_funnel'] = model_to_dict(temp_campaign_funnel)
                    print(context['campaign_funnel'])

                    context["new_lead_form"] = create_new_lead_form(request.GET or None)
                    
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

                return render(request, "portfolio/view_service.html", context)
            else:
                return redirect('/')
        else:
            return redirect('/')
    
    def post(self, request, project_id):
        context = {}
        if portfolio_projects.objects.filter(slug=project_id).exists():
            project_to_see = portfolio_projects.objects.get(slug=project_id)

            if project_to_see.project_type == "open_source":

                get_github_info = requests.get(f"https://api.github.com/repos/{project_to_see.project_repo_link}")
                get_github_readme = requests.get(f"https://api.github.com/repos/{project_to_see.project_repo_link}/readme", headers={"Accept": "application/vnd.github.raw+json"})
                if get_github_readme.status_code == 200:
                    github_readme = get_github_readme.text
                    context['github_readme'] = markdown.markdown(github_readme)
                
                if get_github_info.status_code == 200:
                    github_info = get_github_info.json()
                    context['github_info'] = github_info

                context['project_to_see'] = model_to_dict(project_to_see)

                return render(request, "portfolio/view_project.html", context)

            elif project_to_see.project_type == "services":
                context['services_body'] = project_to_see.project_description
                context['services_context'] = project_to_see.project_casestudy

                if campaign_funnel.objects.filter(id=project_to_see.project_repo_link).exists():
                    temp_campaign_funnel = campaign_funnel.objects.get(id=project_to_see.project_repo_link)
                    context['campaign_funnel'] = model_to_dict(temp_campaign_funnel)

                    context["new_lead_form"] = create_new_lead_form(request.GET or None)
                    
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
                
                return render(request, "portfolio/view_service.html", context)
            else:
                return redirect('/')
        else:
            return redirect('/')


class view_portfolio(View):
    def get(self, request):
        context = {}

        get_all_projects = portfolio_projects.objects.all()

        context['all_projects'] = get_all_projects.values()

        return render(request, "portfolio/view_portfolio.html", context)


class create_campaign_funnel(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        new_campaign_funnel_form = add_new_campaign_funnel(request.GET or None)

        context = {"new_campaign_funnel_form":new_campaign_funnel_form}
        return render(request, "portfolio/create_new_campaign_funnel.html", context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)
        context = {}

        new_campaign_funnel_form = add_new_campaign_funnel(request.POST or None)

        if new_campaign_funnel_form.is_valid():
            new_campaign_funnel = new_campaign_funnel_form.save(commit=False)
            new_campaign_funnel.date_created = timezone.now()


            temp_funnel_dict = json.loads(new_campaign_funnel.funnel_input_form)
            temp_funnel_dict_key_list = list(temp_funnel_dict.keys())
            
            temp_funnel_dict_key_list.append("lead_id")
            temp_funnel_name = str(new_campaign_funnel.funnel_name).replace(" ", "_")

            db_conf = settings.DATABASES['default']
            db_conn = sqlite3.connect(db_conf['NAME'])

            new_table_df = pd.DataFrame(columns=temp_funnel_dict_key_list)
        
            try:
                new_table_df.to_sql(temp_funnel_name, db_conn, if_exists="fail", index=False)
                messages.success(request, "campaign funnel has been created.")
                new_campaign_funnel.save()
                new_campaign_funnel_form = add_new_campaign_funnel()
            except:
                messages.warning(request, "table already exists with this name.")            


        context["new_campaign_funnel_form"] = new_campaign_funnel_form
        return render(request, "portfolio/create_new_campaign_funnel.html", context)

class view_campaign_funnel(View):
    def get(self, request, funnel_id):       
        context = {}

        if campaign_funnel.objects.filter(slug=funnel_id).exists():
            temp_campaign_funnel = campaign_funnel.objects.get(slug=funnel_id)
            context['campaign_funnel'] = model_to_dict(temp_campaign_funnel)

            context["new_lead_form"] = create_new_lead_form(request.GET or None)
            
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

            return render(request, "portfolio/view_campaign_funnel.html", context)
        else:
            return redirect("/portfolio")
    
    def post(self, request, funnel_id):
        context = {}
        if check_authentication(request) != None:
            return check_authentication(request)

        if campaign_funnel.objects.filter(slug=funnel_id).exists():
            temp_campaign_funnel = campaign_funnel.objects.get(slug=funnel_id)
            context['campaign_funnel'] = model_to_dict(temp_campaign_funnel)

            temp_funnel_name = str(temp_campaign_funnel.funnel_name).replace(" ", "_")

            temp_user_lead = create_new_lead_form(request.POST)

            if temp_user_lead.is_valid():
                new_lead = temp_user_lead.save(commit=False)
                new_lead.created_date = timezone.now()
                new_lead.campaign_funnel = temp_campaign_funnel

                new_lead.save()
                
                temp_output_dict = {"lead_id":str(new_lead.id)}
                for key, value in json.loads(temp_campaign_funnel.funnel_input_form).items():
                    if key in request.POST.keys():
                        temp_output_dict[key] = request.POST[key]
                output_df = pd.DataFrame(temp_output_dict, index=[0])

                db_conf = settings.DATABASES['default']
                db_conn = sqlite3.connect(db_conf['NAME'])
            
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

        return render(request, "portfolio/view_campaign_funnel.html", context)
    
    def see_all_info(request, funnel_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        context = {}

        if campaign_funnel.objects.filter(slug=funnel_id).exists():
            temp_campaign_funnel = campaign_funnel.objects.get(slug=funnel_id)
            context['campaign_funnel'] = model_to_dict(temp_campaign_funnel)
            temp_leads_list = pd.DataFrame(campaign_funnel_lead.objects.all().values())
            relevant_lead_list = temp_leads_list[['id', 'email', 'first_name', 'last_name', 'date_created']]

            temp_funnel_name = str(temp_campaign_funnel.funnel_name).replace(" ", "_")
            db_conf = settings.DATABASES['default']
            db_conn = sqlite3.connect(db_conf['NAME'])

            temp_df = pd.read_sql(f'SELECT * FROM \"{temp_funnel_name}\";', db_conn)
            temp_df['lead_id'] = temp_df['lead_id'].astype('int')

            output = pd.merge(temp_df, relevant_lead_list, how='left', left_on='lead_id', right_on='id')
            output['lead_id_a'] = output['lead_id'].apply(lambda x: f'<a href="/cadence/projects/lead-{x}" target="_blank"> {x} </a>')
            context['temp_df'] = output.style.set_table_attributes('class="table" style="color: var(--text);"').to_html(index=False)
            #context['temp_df'] = output.to_dict('records')

            return render(request, "portfolio/view_all_campaign_funnel.html", context)

        else:
            return redirect("/portfolio")


class campaign_faq_view(View):
    def get(self, request, campaign_faq_id):    
        context = {}
        if campaign_faq.objects.filter(slug=campaign_faq_id).exists():
            temp_campaign_faq = campaign_faq.objects.get(slug=campaign_faq_id)
            context['campaign_faq'] = model_to_dict(temp_campaign_faq)
            return render(request, "portfolio/view_campaign_faq.html", context)
        else:
            return redirect("/portfolio")

    def post(self, request, campaign_faq_id):
        context = {}

        if "user_message" in request.POST.keys():
            print(request.POST)

        if campaign_faq.objects.filter(slug=campaign_faq_id).exists():
            temp_campaign_faq = campaign_faq.objects.get(slug=campaign_faq_id)
            context['campaign_faq'] = model_to_dict(temp_campaign_faq)

            return render(request, "portfolio/view_campaign_faq.html", context)
        else:
            return redirect("/portfolio")

    def see_blog_post(request, blog_post_id):
        context = {}

        if campaign_blog.objects.filter(slug=blog_post_id).exists():
            temp_campaign_blog = campaign_blog.objects.get(slug=blog_post_id)
            context['campaign_blog'] = model_to_dict(temp_campaign_blog)

            return render(request, "portfolio/view_blog_post.html", context)
        else:
            return redirect("/portfolio")

class link_in_bio(View):
    def get(self, request):
        context = {}
        if check_authentication(request) != None:
            return check_authentication(request)
        temp_user_info = user_info.objects.get(user=request.user)

        if user_link_in_bio_info.objects.filter(link_user_info=temp_user_info).exists():
            temp_p = user_link_in_bio_info.objects.get(link_user_info=temp_user_info)
            temp_link_in_bio_form = add_user_link_in_bio_info_form(request.GET or None, initial=model_to_dict(temp_p))
            temp_new_link_form = add_link_in_bio_links_form(request.GET or None,)
            context['new_link_form'] = temp_new_link_form
            context['link_in_bio_form'] = temp_link_in_bio_form

        else:
            temp_link_in_bio_form = add_user_link_in_bio_info_form(request.GET or None,)
            context['link_in_bio_form'] = temp_link_in_bio_form

        return render(request, "portfolio/manage_link_in_bio.html", context)

    def post(self, request):
        context = {}
        if check_authentication(request) != None:
            return check_authentication(request)

        temp_user_info = user_info.objects.get(user=request.user)
        if user_link_in_bio_info.objects.filter(link_user_info=temp_user_info).exists():
            temp_user_link_in_bio = user_link_in_bio_info.objects.get(link_user_info=temp_user_info)

        if "link_order" in request.POST.keys():
            
            temp_link_form_to_create = add_link_in_bio_links_form(request.POST or None)
            if temp_link_form_to_create.is_valid():
                link_to_create = temp_link_form_to_create.save(commit=False)
                link_to_create.user_link = temp_user_link_in_bio
                link_to_create.save()

                temp_link_form_to_create = add_link_in_bio_links_form(request.POST or None)
                temp_link_in_bio_form = add_user_link_in_bio_info_form(request.GET or None, initial=model_to_dict(user_link_in_bio_info.objects.get(link_user_info=temp_user_info)))
                context['new_link_form'] = temp_link_form_to_create
                context['link_in_bio_form'] = temp_link_in_bio_form  

                messages.success(request, "link added.")
                return render(request, "portfolio/manage_link_in_bio.html", context)

            else:
                temp_link_form_to_create = add_link_in_bio_links_form(request.POST or None)
                temp_link_in_bio_form = add_user_link_in_bio_info_form(request.GET or None, initial=model_to_dict(user_link_in_bio_info.objects.get(link_user_info=temp_user_info)))
                context['new_link_form'] = temp_link_form_to_create
                context['link_in_bio_form'] = temp_link_in_bio_form

                messages.warning(request, "something went wrong, please try again.")
                return render(request, "portfolio/manage_link_in_bio.html", context)    

        elif "instagram_link" in request.POST.keys():
            temp_link_in_bio_form_to_create = add_user_link_in_bio_info_form(request.POST or None)
            if temp_link_in_bio_form_to_create.is_valid():
                link_in_bio_to_create = temp_link_in_bio_form_to_create.save(commit=False)
                link_in_bio_to_create.link_user_info = temp_user_info
                link_in_bio_to_create.save()
            else:
                temp_link_in_bio_form_to_create = add_user_link_in_bio_info_form(request.POST or None)
                context['link_in_bio_form'] = temp_link_in_bio_form_to_create
    
                messages.warning(request, "something went wrong, please try again.")
                return render(request, "portfolio/manage_link_in_bio.html", context)
        else:

            if user_link_in_bio_info.objects.filter(link_user_info=temp_user_info).exists():
                temp_link_in_bio_form = add_user_link_in_bio_info_form(request.GET or None, initial=user_link_in_bio_info.objects.get(link_user_info=temp_user_info))
                temp_new_link_form = add_link_in_bio_links_form(request.GET or None,)
                context['new_link_form'] = temp_new_link_form
                context['link_in_bio_form'] = temp_link_in_bio_form

            else:
                temp_link_in_bio_form = add_user_link_in_bio_info_form(request.GET or None,)
                context['link_in_bio_form'] = temp_link_in_bio_form

            return render(request, "portfolio/manage_link_in_bio.html", context)

    def see_link_in_bio(request, user_info_id):
            context = {}
    
            if user_info.objects.filter(user=user_info_id).exists():
                temp_user = user_info.objects.get(user=user_info_id)
                if user_link_in_bio_info.objects.filter(link_user_info=temp_user).exists():
                    temp_user_link_in_bio = user_link_in_bio_info.objects.get(link_user_info=temp_user)
                    temp_user_links = link_in_bio_links.objects.filter(user_link=temp_user_link_in_bio)
                    context['user_link_in_bio'] = temp_user_link_in_bio
                    context['temp_user_links'] = temp_user_links
                    context['user_info'] = model_to_dict(temp_user)
    
                return render(request, "portfolio/view_link_in_bio.html", context)
            else:
                return redirect("/portfolio")
    
