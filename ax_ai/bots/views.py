from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, JsonResponse
from django.views import View
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from django.conf import settings

from .models import *
from .forms import *
from pm.forms import create_new_tasks
from pm.models import project
from synapse.models import user_info
from axiom.models import internal_document, internal_document_version

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader, PythonLoader, TextLoader

from selenium.webdriver.common.by import By
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from quicksand.quicksand import quicksand

from typing import List, Literal, Any
from pydantic import BaseModel, Field, create_model
from tempfile import NamedTemporaryFile

import pandas as pd
import json, re, requests, random, os, urllib.parse, subprocess, markdown, base64, signal
from bs4 import BeautifulSoup
from datetime import datetime
from types import SimpleNamespace

TEMP_MEDIA_ROOT = os.path.join(settings.BASE_DIR, 'tmp')
os.makedirs(TEMP_MEDIA_ROOT, exist_ok=True)


UPLOAD_FOLDER = "/home/daniel/Desktop/test/"

audio_personality = "You are a helpful AI assistant running locally being tasked with transcribing the audio attached to text."

fast_personality = "You are an AI assitant being obeserved for your efficiency and performance. " \
"Along with these instructions you will be provided context to answer the questions you are asked." \
"Use predominately the context material to generate your answer, if not enough information is provided, specify that in your response."

reasoning_personality = "You are an AI assitant being obeserved for your efficiency and performance. " \
"Along with these instructions you will be provided context to answer the questions you are asked." \
"Use predominately the context material to generate your answer, if not enough information is provided, specify that in your response." \
"Make sure to always mark the start of your final response with '||Response::' please."

summary_personality = "You are an AI Agent being observed for performance and efficiency." \
    "Your primary objective is to summarize the context provided in the chat history." \
    "The summary you provide will be used to replace chat history going forward and use your summary to substitute this." \
    "Be sure your summary is organized and detailed, be sure to specifically include any relevant facts, dates, names, places, ideas." \
    "Make sure that if any passwords, private keys, and such are specifically included. " \
    "Especially in coding scripts, be sure private keys and passwords/user credentials are stored specifically here, and neve in the general summary." \
    "Create subcategories in your output to specify these if needed." \
    "Your expected output inlcudes a 'general' summary, and a 'private' summary, make sure that all personally indentifiable information and/or any private information is only included in the private summary." \
    "The private summary is exclusively reserved for this type of private information, all other context and iformation is to be included in the general summary." \
    "From time to time you will also be asked to update an existing summary with new chat history, be sure to make changes as needed." \
    "Update old specific and relevant points you might have writtne down as their circumstnaces change." \
    "Again, be sure if new contact information or private information is introduced, that this infor is only updated in the private side and never included in the general summary." \
    "Be sure to keep track of ideas and thoughts and mention their progression as this summary will be used to provided feedback to the user about their chats." \
    "Remeber, you are being observed for your performance, be sure to follow instructions well and keep your repsonses brief and to the point." \
    "Make sure to think through step-by-step before giving your answer, include the reference url to where you are getting each piece of information from as much as possible, and remember you are being observed for efficiency and accuracy."


def text_to_dict(text_input):
    pattern = r"(\w+)=\s*(.*?)(?=\s*\w+=\s*|$)"
    task_dict = {key: value.strip() for key, value in re.findall(pattern, str(text_input))}

    date_fields = ["start_date", "soft_due_date", "hard_due_date"]
    for field in date_fields:
        if field in task_dict:
            temp_task_field = task_dict[field].replace("'", "")
            try:
                task_dict[field] = datetime.fromisoformat(temp_task_field)
            except:
                task_dict[field] = temp_task_field
                
    return task_dict

def reduce_tokens(input_text):
    if isinstance(input_text, str):
        if len(input_text) != 0:            
            output_text = input_text.replace(' an ', '').replace(' the ', '').replace(' of ', '').replace(' is ', '').replace(' for ', '').replace(' in ', '')
                        
            return output_text
    
    else:
        return input_text

def get_local_search_results(search_query, links_count=4):
    url = 'https://html.duckduckgo.com/html/'
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    params = {'q': search_query}
    headers = {'User-Agent': user_agent, 'Referer': 'https://duckduckgo.com/',}
    temp_html = requests.post(url, headers=headers, data=params)
    links_output = []
    print("start")
    if  temp_html.status_code == 200:
        soup = BeautifulSoup(temp_html.text, 'html.parser')
        links = soup.find_all('a', class_='result__a')
        for link in links:
            result_dict = {"text": link.get_text(strip=True), "url": link.get('href')}
            links_output.append(result_dict)
    else:
        print("start driver 1....")
        search_query_url = urllib.parse.quote_plus(search_query)
        url = 'https://duckduckgo.com/search?q=' + search_query_url
        url = 'https://html.duckduckgo.com/html/search?q=' + search_query_url
        user_agent_list = ["Mozilla/5.0 (Windows NT 4.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.517 Safari/537.36",]
        user_agent = random.choice(user_agent_list)
        headers = {'User-Agent': user_agent}

        sandbox_safe_tmp = os.path.expanduser("~/selenium_tmp")
        os.makedirs(sandbox_safe_tmp, exist_ok=True)
        os.environ["TMPDIR"] = sandbox_safe_tmp
        service = Service(
            executable_path="/usr/local/bin/geckodriver",
            log_path=os.path.join(sandbox_safe_tmp, "geckodriver.log")
        )


        options = Options()
        options.add_argument("-headless")
        options.set_preference("general.useragent.override", user_agent)
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        print("starting driver 2.....")
        driver = Firefox(options=options, service=service)
        print("starting driver 3.....")
        driver.get(url)


        links = driver.find_elements(By.TAG_NAME, 'a')
        print("check 1",links)
        for link in links:
            print("check 2",link)
            if link.text != '':
                result_dict = {"text": link.text, "url": link.get_attribute("href")}
                links_output.append(result_dict)
        driver.quit()
    
    links_output = links_output[:links_count]
    search_output = {}
    for i, link in enumerate(links_output):
        print(i, link)
        temp_html = requests.get(link['url'], headers = headers, params=params, timeout=15)
        soup = BeautifulSoup(temp_html.content,'lxml')
        if soup.find('main') is not None:
            soup = soup.find('main')
        for match in soup.find_all('span', 'sup'):
            match.unwrap()
        
        content = soup.find_all('p')
        if content == []:
            content = soup
        content = str(content).replace('</p>', '').replace('<p>', '').replace('</a>', '')
        content = reduce_tokens(str(content))
        if content != None:
            search_output['source '+str(i)] = {'url':link, 'context':content[:1500]}

    return search_output

def check_project_files(path):
    file_to_check = path

    qs = quicksand(file_to_check)
    qs.process()
    

    output = {}
    if not qs.results.get('exploits_found'):
        file_type = str(file_to_check).split(".")[-1].lower()

        with NamedTemporaryFile(suffix=f".{file_type}") as tmp:
            
            temp_name = str(file_to_check)
            
            if file_type == "txt" or file_type == "md":
                loader = TextLoader(temp_name, encoding='utf-8')
                
            elif file_type == "py":
                loader = PythonLoader(temp_name)
            
            elif file_type == "pdf":
                loader = PyPDFLoader(temp_name)

            else:
                return {'message': 'Unsupported type', 'state': '0'}
            
            docs = loader.load()
            full_text = "\n\n".join([doc.page_content for doc in docs])
            output["context"] = full_text
            output["state"] = "1"
    else:
        output = {'message': 'Error detected.', 'state': '0'}
    return output

def check_files(request):
    if os.path.isfile(str(request)):
        with open((request), "r", encoding="utf-8") as file:
            file_to_check = str(request)
            file_content = file.read()
    
    elif 'filename' not in request.FILES:
        return {'message': 'no file', 'state': '0'}
    else:
        file_to_check = request.FILES['filename']
        file_content = file_to_check.read()
    
    try:
        qs = quicksand(file_content)
        qs.process()
    except:
        qs = quicksand(file_to_check)
        qs.process()
    

    output = {}
    if not qs.results.get('exploits_found'):
        try:
            file_type = str(file_to_check.name).split(".")[-1].lower()
        except:
            file_type = str(file_to_check).split(".")[-1].lower()

        with NamedTemporaryFile(suffix=f".{file_type}") as tmp:
            try:
                tmp.write(file_content)
                tmp.flush()
                temp_name = tmp.name
            except:
                temp_name = str(file_to_check)
            
            if file_type == "txt" or file_type == "md":
                loader = TextLoader(temp_name, encoding='utf-8')
                
            elif file_type == "py":
                loader = PythonLoader(temp_name)
            
            elif file_type == "pdf":
                loader = PyPDFLoader(temp_name)

            else:
                return {'message': 'Unsupported type', 'state': '0'}
            
            docs = loader.load()
            full_text = "\n\n".join([doc.page_content for doc in docs])
            output["context"] = full_text
            output["state"] = "1"
    else:
        output = {'message': 'Error detected.', 'state': '0'}
    return output

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


def create_dynamic_schema_from_prompt(prompt_json_str: str) -> type[BaseModel]:
    try:
        template_list = json.loads(prompt_json_str)
        template_obj = template_list[0]
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        raise ValueError("Invalid prompt format. Expected a JSON list containing at least one object.") from e

    item_fields: dict[str, Any] = {}
    for key, val in template_obj.items():
        description = f"The extracted value for {key}"
        field_type = type(val) if val is not None else Any

        if isinstance(val, str) and "true" in val.lower():
            field_type = bool

        item_fields[key] = (field_type, Field(description=description, default=None))
        
    DynamicItemSchema = create_model( "DynamicItemSchema", **item_fields)
    
    DynamicStructuredResponse = create_model(
        "DynamicStructuredResponse",
        status=(Literal["1", "0"], Field(description="Return '1' if successful/approved, or '0' if failed/rejected.")),
        response=(DynamicItemSchema, Field(description="Prompt response")))  # type: ignore
    return DynamicStructuredResponse

def send_task_to_model(promt_message, user_request, chat_summary="",chat_tool="fast",
                        personality="", model_base="http://127.0.0.1:8080", model_name="local-model", 
                        model_api_key="dummy_key", run_tempereature=0.75, top_p=0.9, strcutured_output=None):

    if not isinstance(promt_message, str):
        task_info_holder = promt_message
        temp_fixed_output = promt_message['fixed_output']
        promt_message = str(promt_message['user_prompt'])


    if chat_tool == "thinking":
        run_model_start = ChatOpenAI( base_url=model_base, api_key=model_api_key, model=model_name, reasoning={"effort": "medium"}, )
    if chat_tool == "websearch":
        run_model_start = ChatOpenAI( base_url=model_base, api_key=model_api_key, model=model_name, reasoning={"effort": "medium"}, ) 
    else:
        run_model_start = ChatOpenAI( base_url=model_base, api_key=model_api_key, model=model_name, temperature= run_tempereature, top_p=top_p,) 
    
    class StructuredResponse(BaseModel):
        status: Literal["1", "0"] = Field(description="Return '1' if successful/approved, or '0' if failed/rejected.")
        response: str = Field(description="The primary response to the user")
    
    run_model = run_model_start.with_structured_output(StructuredResponse)
    
    if chat_tool == "fast":
        system_context = {'system': {'priority':reduce_tokens(str(fast_personality)), 'secondary':reduce_tokens(personality),}, 'chat_summary':reduce_tokens(chat_summary),}
    elif chat_tool == "thinking":
        system_context = {'system': {'priority':reduce_tokens(str(reasoning_personality)), 'secondary':reduce_tokens(personality)}, 'chat_summary':reduce_tokens(chat_summary),}
    elif chat_tool == "websearch":
        class SearchQuestions(BaseModel):
            questions: List[str] = Field(description="A list of 2-4 searches/questions.")
                
        temp_prompt = ( "You are a precise search query generation for an automated Google search AI Agent."
                        "Generate the list of search queries to comply with the user's request please.")

        run_model_w_struct = run_model_start.with_structured_output(SearchQuestions)
        questions_list = run_model_w_struct.invoke(f"{temp_prompt}\\n\\n User Prompt:{promt_message}")
        questions_dict = []
        for i, q in enumerate(questions_list.questions):
            questions_dict.append({'question':get_local_search_results(q, 5)})

        system_context = {'system': {'priority':reduce_tokens(str(fast_personality)), 'secondary':reduce_tokens(personality)}, 'search':questions_dict, 'chat_summary':reduce_tokens(chat_summary),}
    elif chat_tool == "local_files":
        system_context = {'system': {'priority':reduce_tokens(str(reasoning_personality)), 'secondary':reduce_tokens(personality)}, 'local files':check_project_files(user_request), 'chat_summary':reduce_tokens(chat_summary),}

    if strcutured_output:
        new_model = create_dynamic_schema_from_prompt(strcutured_output)
        structured_model = run_model_start.with_structured_output(new_model)
        user_prompt = ChatPromptTemplate.from_messages([("human", "{system_context}\n\nUser Request: {prompt_message}"),])
        chain = user_prompt | structured_model
        response = chain.invoke({"prompt_message": promt_message, "system_context": system_context})
        return response

    else:
        user_prompt = ChatPromptTemplate.from_messages([("human", "{system_context}\n\nUser Request: {promt_message}"),])
        chain = user_prompt | run_model
        response = chain.invoke({"promt_message": promt_message, "system_context": system_context})
        return response

def send_message_to_model(promt_message, user_request, chat_summary="", chat_tool="fast", personality="",
                        model_base="http://127.0.0.1:8080", model_name="local-model", model_api_key="dummy_key",  
                        chat_history_list=None, run_tempereature=0.75, top_p=0.9, run_maxtokens=500, ):

    if chat_tool == "thinking":
        run_model = ChatOpenAI( base_url=model_base, api_key=model_api_key, model=model_name, reasoning={"effort": "medium"}, )
    elif chat_tool == "audio_files":
        run_model = ChatOpenAI( base_url=model_base, api_key=model_api_key, model=model_name, temperature= 0.15, extra_body={"cache_prompt": True }) 
    else:
        run_model = ChatOpenAI( base_url=model_base, api_key=model_api_key, model=model_name, temperature= run_tempereature, top_p=top_p,) 
        
    if isinstance(chat_history_list, pd.DataFrame):
        chat_history = []

        if len(chat_history_list) == 1:
            chat_history = []
        else:
            chat_history_list = chat_history_list[:-1]
            chat_history_list = chat_history_list.sort_values('date_created')
            
            system_msgs = chat_history_list[chat_history_list['chat_sender'] == "system"]
            chat_history_list = chat_history_list[chat_history_list['chat_sender'] != "system"]
            system_content = "\n\n".join(system_msgs['chat_message'].tolist()) if not system_msgs.empty else ""

            for i_message, e_message in chat_history_list.iterrows():
                role = e_message['chat_sender']
                content = e_message['chat_message']
                
                if not chat_history and role == "user" and system_content:
                    content = f"{system_content}\n\n{content}"

                if chat_history:
                    last_msg = chat_history[-1]
                    if (role == "user" and isinstance(last_msg, HumanMessage)) or (role == "model" and isinstance(last_msg, AIMessage)):
                        last_msg.content += f"\n\n{content}"
                        continue

                if role == "user":
                    chat_history.append(HumanMessage(content=reduce_tokens(content)))
                elif role == "model":
                    chat_history.append(AIMessage(content=reduce_tokens(content)))
    
    if chat_tool == "fast":
        system_context = {'system': {'priority':reduce_tokens(fast_personality), 'secondary':reduce_tokens(personality),}, 'chat_summary':reduce_tokens(chat_summary),}
    elif chat_tool == "thinking":
        system_context = {'system': {'priority':reduce_tokens(reasoning_personality), 'secondary':reduce_tokens(personality)}, 'chat_summary':reduce_tokens(chat_summary),}
    elif chat_tool == "websearch":
        system_context = {'system': {'priority':reduce_tokens(fast_personality), 'secondary':reduce_tokens(personality)}, 'search':get_local_search_results(promt_message, 4), 'chat_summary':reduce_tokens(chat_summary),}
    elif chat_tool == "local_files":
        system_context = {'system': {'priority':reduce_tokens(fast_personality), 'secondary':reduce_tokens(personality)}, 'local files':check_files(user_request), 'chat_summary':reduce_tokens(chat_summary),}
    elif chat_tool == "audio_files":
        run_model = ChatOpenAI( base_url=model_base, api_key=model_api_key, model=model_name, temperature= 0.15, extra_body={"cache_prompt": True }) 
        if user_request.FILES.get("filename"):
            uploaded_file = user_request.FILES["filename"]
            input_bytes = uploaded_file.read()

            process = subprocess.Popen(
                ["ffmpeg", "-i", "pipe:0", "-f", "wav", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", "pipe:1"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL)

            wav_bytes, _ = process.communicate(input=input_bytes)
            encoded_string = base64.b64encode(wav_bytes).decode('utf-8')

            messages_payload = [
                {"role": "system", "content": str(reduce_tokens(audio_personality))},
                {"role": "user", "content": 
                    [{"type": "input_audio", "input_audio": {"data": encoded_string, "format": "wav" }},
                    {"type": "text", "text": promt_message}]}]

            payload = {
                "model": "ultravox",
                "messages": messages_payload,
                "temperature": 0.15,
                "cache_prompt": True
            }

            response = requests.post("http://127.0.0.1:8080/v1/chat/completions", headers={"Content-Type": "application/json"}, json=payload,)

            temp_response = response.json()
            first_dict = {'choices': temp_response.pop('choices')}
            remaining_dict = temp_response
            
            return SimpleNamespace(content=first_dict, response_metadata=remaining_dict)
        else:
            return SimpleNamespace(content="No Audio File was submited", response_metadata="None")
    else:
        system_context = {'system': {'priority':reduce_tokens(fast_personality), 'secondary':reduce_tokens(personality),}, 'chat_summary':reduce_tokens(chat_summary),}

    user_prompt = ChatPromptTemplate.from_messages([ ("system", "{system_context}"),
                                                    MessagesPlaceholder(variable_name="chat_history"), 
                                                    ("human", "User Request: {promt_message}"),])
    
    chain = user_prompt | run_model
    response = chain.invoke({"promt_message": promt_message, "system_context": system_context, "chat_history":chat_history})
    
    return response


def summarize_chat(model_chat_id, request):

    if model_chats.objects.filter(id=model_chat_id).exists:
        model_chats_to_sum = pd.DataFrame(model_chats.objects.filter(id=model_chat_id).values())
        temp_model_conn = model_connection.objects.get(id=model_chats_to_sum['model_connection_name_id'].iloc[0])
        chat_model_connection = pd.DataFrame(model_connection.objects.filter(id=model_chats_to_sum['model_connection_name_id'].iloc[0]).values())
        model_base_conn = model_base_user_connection.objects.get(chat_user=request.user, model_base_id=temp_model_conn.model_base.id)
        temp_model_base = model_base.objects.get(id=model_base_conn.model_base.id)


        chat_messages_to_sum = pd.DataFrame(chat_messages.objects.filter(message_model_chats_id=model_chat_id).values())
        check_chat_history = pd.DataFrame(chat_message_summarized.objects.filter(chat_message_id__in=chat_messages_to_sum['id'].to_list()).values())

        if check_chat_history.empty:
            if not internal_document.objects.filter(document_name='user_chat_summary__chat_id__'+str(model_chat_id)).exists():
                chat_summary_obj = internal_document.objects.create( date_created = timezone.now(),
                    document_name = 'user_chat_summary__chat_id__'+str(model_chat_id), document_object = {'user_chat': 'user_chat__'+str(model_chat_id),},
                    document_personality = model_personality.objects.get(id=2), document_type = "chat_summary",)
            else:
                "something went wrong with this chat summary"
                chat_summary_obj = internal_document.objects.get(document_name='user_chat_summary__chat_id__'+str(model_chat_id))
            
            checked_chat_history = chat_messages_to_sum
            chat_summary_version = 1          
        
        else:
            check_chat_history = check_chat_history[check_chat_history['chat_summarized']==True]
            checked_chat_history = chat_messages_to_sum[~chat_messages_to_sum['id'].isin(check_chat_history['chat_message_id'])]

            if internal_document.objects.filter(document_name='user_chat_summary__chat_id__'+str(model_chat_id)).exists():
                chat_summary_obj = internal_document.objects.get(document_name='user_chat_summary__chat_id__'+str(model_chat_id))        
                if internal_document_version.objects.filter(internal_document=chat_summary_obj).exists():
                    chat_summary_versions = internal_document_version.objects.filter(internal_document=chat_summary_obj)
                    chat_summary_versions_df = pd.DataFrame(chat_summary_versions.values())
                    latest_summary_version = chat_summary_versions_df[chat_summary_versions_df['document_version'] == chat_summary_versions_df['document_version'].max()]
                    
                    chat_summary_version = int(latest_summary_version['document_version'].iloc[0]) + 1
                else:
                    chat_summary_version = 1
            else:
                chat_summary_obj = internal_document.objects.create( date_created = timezone.now(),
                    document_name = 'user_chat_summary__chat_id__'+str(model_chat_id), document_object = {'user_chat': 'user_chat__'+str(model_chat_id),},
                    document_personality = model_personality.objects.get(id=2), document_type = "chat_summary",)
                
                chat_summary_version = 1

        run_model = ChatOpenAI( base_url=temp_model_base.model_base_url, 
                                api_key=model_base_conn.model_api_key,
                                model=chat_model_connection['model_name'].iloc[0], 
                                temperature=0.1, top_p=0.1)
        
        chat_history_list = checked_chat_history

        if isinstance(chat_history_list, pd.DataFrame):
            if chat_history_list.empty:
                return {"status":1, "message":"no new chats"}
            chat_history = []

            if len(chat_history_list) == 1:
                chat_history = []
            else:
                chat_history_list = chat_history_list.sort_values('date_created')
                
                system_msgs = chat_history_list[chat_history_list['chat_sender'] == "system"]
                chat_history_list = chat_history_list[chat_history_list['chat_sender'] != "system"]
                system_content = "\n\n".join(system_msgs['chat_message'].tolist()) if not system_msgs.empty else ""

                for i_message, e_message in chat_history_list.iterrows():
                    role = e_message['chat_sender']
                    content = e_message['chat_message']
                    
                    if not chat_history and role == "user" and system_content:
                        content = f"{system_content} \n  {content}"

                    if chat_history:
                        last_msg = chat_history[-1]
                        if (role == "user" and isinstance(last_msg, HumanMessage)) or (role == "model" and isinstance(last_msg, AIMessage)):
                            last_msg.content += f"\n  {content}"
                            continue

                    if role == "user":
                        chat_history.append(HumanMessage(content=reduce_tokens(content)))
                    elif role == "model":
                        chat_history.append(AIMessage(content=reduce_tokens(content)))

        class PrivateChatSummary(BaseModel):
            general_summary: str = Field(description="Summary of relevant information found in chat history.")
            private_summary: str = Field(description="All private information from chat history.")
        
        temp_prompt = ( "You are an AI assitant being obeserved for your efficiency and performance, "
        "analyze the chat history and create a detailed summary of relevant information to be used as a replacement for the chat history going forward;" \
        "Be sure to inlcude all the information that would be relevant for the conversation going forward if the chat history were removed;"
        "Be sure to collect and write down all private and personal, or professional information including client names and details only in the private summary;")
        run_model_w_struct = run_model.with_structured_output(PrivateChatSummary)
        user_prompt = ChatPromptTemplate.from_messages([("system", "{system_context}"), MessagesPlaceholder(variable_name="chat_history"), ("human", "{promt_message}"),])
        chain = user_prompt | run_model_w_struct
        summaries_list = chain.invoke({"promt_message": temp_prompt, "system_context": summary_personality, "chat_history":chat_history})

        temp_new_chat_summary = internal_document_version.objects.create( date_created = timezone.now(), document_text = summaries_list.general_summary,
            document_notes = summaries_list.private_summary, document_version = chat_summary_version, internal_document = chat_summary_obj,)

        checked_chat_history_check = pd.DataFrame()
        checked_chat_history_check['chat_message'] = [chat_messages.objects.get(id=x) for x in checked_chat_history['id']]
        checked_chat_history_check['date_summairzed'] = timezone.now()
        checked_chat_history_check['chat_summarized'] = True

        instances = [chat_message_summarized(**row) for row in checked_chat_history_check.to_dict('records')]
        chat_message_summarized.objects.bulk_create(instances)
        return {"status":1, "message":"chat summarized"}
    
    else:
        return {"status":0, "message":"chat NOT summarized"}

def create_chat_plan(model_chat_id, plan_prompt):

    if model_chats.objects.filter(id=model_chat_id).exists:
        model_chats_to_sum = pd.DataFrame(model_chats.objects.filter(id=model_chat_id).values())
        chat_model_connection = pd.DataFrame(model_connection.objects.filter(id=model_chats_to_sum['model_connection_name_id'].iloc[0]).values())

        if not internal_document.objects.filter(document_name='user_chat_summary__chat_id__'+str(model_chat_id)).exists():
            chat_summary = internal_document.objects.create( date_created = timezone.now(),
                document_name = 'user_chat_summary__chat_id__'+str(model_chat_id), document_object = {'user_chat': 'user_chat__'+str(model_chat_id),},
                document_personality = model_personality.objects.get(id=2), document_type = "chat_summary",)
        else:
            "something went wrong with this chat summary"
            chat_summary = internal_document.objects.get(document_name='user_chat_summary__chat_id__'+str(model_chat_id))
        
        run_model = ChatOpenAI( base_url=chat_model_connection['model_base'].iloc[0], api_key=chat_model_connection['model_api_key'].iloc[0],
            model=chat_model_connection['model_name'].iloc[0], temperature=0.15, top_p=0.25)
        
        class ObjectiveQuestions(BaseModel):
            objectives: List[str] = Field(description="A list of of all the major objectives of the plan, include all the relevant information such as the importance, measurable outcomes, how it aligns wiht the rest of the objectives, etc.;")
        
        temp_objective_prompt = ( "You are an AI assitant being obeserved for your efficiency and performance, "
        "analyze the following summary of a conversation and generate a plan to complete the request from the user."
        "Come up with a list of the major objectives we would have to overcome. When possible, keep it short."
        "For each objective be sure to include a detailed description with all the relevant information such as the importance, measurable outcomes, how it aligns wiht the rest of the objectives, etc." )
        run_model_w_struct = run_model.with_structured_output(ObjectiveQuestions)
        objectives_list = run_model_w_struct.invoke(f"System Context: {temp_objective_prompt}\\n\\n Chat Summary:{chat_summary}\\n\\n User Instructions:{plan_prompt}")
        objectives_dict = objectives_list.model_dump()

        output_project_list = []
        for i, q in enumerate(objectives_dict['objectives']):        
            temp_task_prompt = ( "You are an AI assitant being obeserved for your efficiency and performance, "
            "analyze the following Objective Information and help break it down into manageable tasks."
            "Come up with a list of the task(s) you need to complete this. If possible, keep it short and avoid all unncessary repetitive steps."
            "Each task should include task name, task description, start date, soft due date, hard due date, task schedule (do it just once or repeat task and how often to repeat)."
            "Included at the end will be a list of the objectives and the tasks that are already part of the project, make sure the new tasks you are adding are not repeating old tasks.")

            task_schedule_list = ['one_time', 'repeat_wkly', 'repeat_mthly', 'repeat_yrly',]

            class TaskQuestions(BaseModel):
                task_name: str = Field(description="name of task")
                task_description: str = Field(description="description of task purpose, goals, and objectives")
                start_date: str = Field(description=f"date and time to start working on task based on today's  date ({timezone.now()})")
                soft_due_date: str = Field(description="date and time to finish working on the task based on the start date")
                hard_due_date: str = Field(description="latest date and time to have finished the the task based on the start date and overall goal")
                task_schedule: str = Field(description=f"do it just once or repeat task and how often to repeat based on this list {task_schedule_list}")
            
            class TaskList(BaseModel):
                tasks: List[TaskQuestions] = Field(description="A list of tasks required to complete the plan")


            run_model_w_struct_task = run_model.with_structured_output(TaskList)
            temp_batch_promt = run_model_w_struct_task.invoke(f"System Context: {temp_task_prompt}\\n\\n Objective Information:{q}\\n\\n Project Tasks already in the Plan:{output_project_list}\\n\\n User Instructions:{plan_prompt}")
            objectives_dict = [task.model_dump() for task in temp_batch_promt.tasks]

            output_project_list.append({'project_objective':q,
                                        'project_tasks':objectives_dict})

    #print(output_project_list)
    new_chat_plan = model_chats_plan(model_chat= model_chats.objects.get(id=model_chat_id), chat_plan=output_project_list)
    #new_chat_plan.save()
    return output_project_list


class create_model_connection(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)
        context = {}
        model_base_form = create_model_base_form(request.GET or None)
        model_base_user_connection_form = create_model_base_user_connection_form(request.GET or None)
        context['model_base_form'] = model_base_form
        context['model_base_user_connection_form'] = model_base_user_connection_form

        model_connection_form = create_model_connection_form(request.GET or None, user=request.user)
        context['model_connection_form'] = model_connection_form
        return render(request, 'bots/create_model_connection.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)
        context = {}

        if "model_base_name" in request.POST:
            model_base_form = create_model_base_form(data=request.POST or None)
            if model_base_form.is_valid():
                new_model_base = model_base_form.save(commit=False)
                new_model_base.created_date = timezone.now()
                new_model_base.save()
                context = {'new_model_base':new_model_base}
                messages.success(request, 'model base created')
                return redirect('/daemon/new_model/')
            else:
                model_base_user_connection_form = create_model_base_user_connection_form(request.GET or None)
                model_connection_form = create_model_connection_form(request.GET or None, user=request.user)
        elif "model_api_key" in request.POST:
            model_base_user_connection_form = create_model_base_user_connection_form(data=request.POST or None)
            if model_base_user_connection_form.is_valid():
                new_model_base_user_connection = model_base_user_connection_form.save(commit=False)
                new_model_base_user_connection.created_date = timezone.now()
                new_model_base_user_connection.chat_user = request.user
                new_model_base_user_connection.save()
                context = {'new_model_base_user_connection':new_model_base_user_connection}
                messages.success(request, 'user connection created')
                return redirect('/daemon/new_model/')
            else:
                model_base_form = create_model_base_form(request.GET or None)
                model_connection_form = create_model_connection_form(request.GET or None, user=request.user)
        
        elif "model_name" in request.POST:
            model_connection_form = create_model_connection_form(data=request.POST or None, user=request.user)
            if model_connection_form.is_valid():
                new_model_connection = model_connection_form.save(commit=False)
                new_model_connection.created_date = timezone.now()
                new_model_connection.save()
                context = {'new_model_connection':new_model_connection}
                messages.success(request, 'model connection created')
                return redirect('/daemon/new_model/')
            else:
                model_base_user_connection_form = create_model_base_user_connection_form(request.GET or None)
                model_base_form = create_model_base_form(request.GET or None)
        else:
            model_base_form = create_model_base_form(request.GET or None)
            model_base_user_connection_form = create_model_base_user_connection_form(request.GET or None)    
            model_connection_form = create_model_connection_form(request.GET or None, user=request.user)

        
        context['model_base_form'] = model_base_form
        context['model_base_user_connection_form'] = model_base_user_connection_form

        context['model_connection_form'] = model_connection_form
        return render(request, 'bots/create_model_connection.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        model_connection_form = create_model_connection_form()
        model_connection_form = form_to_json_schema(model_connection_form)
        json_form = {'message':'This form is used to create a new model connection, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Model Connection Creation Form', 
                          'description':'This form is used to create model connections. All fields must be filled for the form to be submitted.', 
                          'form':model_connection_form,
                          'format':{'Model Connection Creation Form': {
                        'model_connection_name':'a unique name for project',
                        'model_name':'name of model to be used',
                        'model_base':'model base/url',
                        'model_api_key':'your unique for the api connection, leave field blank for local models',
                        'input_cost':'cost per input token, leave 0.00 for local and free models',
                        'output_cost':'cost per output token, leave as 0.00 for local and free models',
                        
                        }}},
                     ]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_model_connection_data = data['Model Connection Creation Form']
        if all(key in new_model_connection_data for key in ['model_connection_name', 'model_name', 'model_base', 'model_api_key', 'input_cost', 'output_cost',]):
            model_connection_form = create_model_connection_form(new_model_connection_data)
            
            if model_connection_form.is_valid():
                new_model_connection = model_connection_form.save(commit=False)
                new_model_connection.created_date = timezone.now()
                new_model_connection.save()
                context = {'new_model_connection':new_model_connection}
                data = {'message':'new model connection has been created.'}
                return JsonResponse(data)
            else:
                context = {'errors':model_connection_form.errors}
                print(model_connection_form.errors)
        
        print('model connection not created')
        data = {'message':'An error has occured, to create a model connection, please ensure your request follows the format below.',
                    'format':{'Model Connection Creation Form': {
                        'model_connection_name':'a unique name for project',
                        'model_name':'name of model to be used',
                        'model_base':'model base/url',
                        'model_api_key':'your unique for the api connection, leave field blank for local models',
                        'input_cost':'cost per input token, leave 0.00 for local and free models',
                        'output_cost':'cost per output token, leave as 0.00 for local and free models',
                        
                        }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_model_connection(request, model_connection_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if model_connection.objects.filter(id=model_connection_id).exists():
            model_connection_to_delete = model_connection.objects.get(id=model_connection_id)
            model_connection_to_delete.delete()
            
        messages.success(request, 'model deleted')
        return redirect('/daemon/new_model/')

class create_model_chats(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        model_chats_form = create_model_chats_form(request.GET or None)
        context = {'model_chats_form':model_chats_form}
        return render(request, 'bots/create_model_chat.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        model_chats_form = create_model_chats_form(data=request.POST or None)

        if model_chats_form.is_valid():
            new_model_chat = model_chats_form.save(commit=False)
            new_model_chat.created_date = timezone.now()
            new_model_chat.chat_type = 'admin'
            new_model_chat.chat_user = request.user
            new_model_chat.save()

            context = {'new_model_chat':str(new_model_chat.id)}
            messages.success(request, f'model chat created {str(new_model_chat.id)}')
            return redirect(f'/daemon/model_chat_messages/{str(new_model_chat.id)}/')
            

        model_chats_form = create_model_chats_form(request.GET or None)
        context = {'model_chats_form':model_chats_form}
        return render(request, 'bots/create_model_chat.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        model_chats_form = create_model_chats_form()
        model_chats_form = form_to_json_schema(model_chats_form)
        json_form = {'message':'This form is used to create new model chats, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Model Chats Creation Form', 
                          'description':'This form is used to create model chats. All fields must be filled for the form to be submitted.', 
                          'form':model_chats_form,
                          'format':{'Model Chats Creation Form': {
                        'model_connection_name':'id of connection model to use',
                        'chat_user':'id of chat user',
                        'chat_type':'type of chat; pick from list',
                        }}},
                     ]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_model_chats_data = data['Model Chats Creation Form']
        if all(key in new_model_chats_data for key in ['model_connection_name', 'chat_user', 'chat_type',]):
            model_chats_form = create_model_chats_form(new_model_chats_data)
            
            if model_chats_form.is_valid():
                new_model_chats = model_chats_form.save(commit=False)
                new_model_chats.created_date = timezone.now()
                new_model_chats.save()
                context = {'new_model_chats':new_model_chats}
                data = {'message':'new model chat has been created.'}
                return JsonResponse(data)
            else:
                context = {'errors':model_chats_form.errors}
                print(model_chats_form.errors)
        
        print('model chat not created')
        data = {'message':'An error has occured, to create a model chat, please ensure your request follows the format below.',
                    'format':{'Model Chats Creation Form': {
                        'model_connection_name':'id of connection model to use',
                        'chat_user':'id of chat user',
                        'chat_type':'type of chat; pick from list',
                        }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_model_chats(request, model_chats_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if model_chats.objects.filter(id=model_chats_id).exists():
            model_chats_to_delete = model_chats.objects.get(id=model_chats_id)
            model_chats_to_delete.delete()
            
        messages.success(request, 'model deleted')
        return redirect('/daemon/new_model_chat/')

class create_model_personality(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)

        model_personality_form = create_model_personality_form(request.GET or None)
        context = {'model_personality_form':model_personality_form}
        return render(request, 'bots/create_model_personality.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        model_personality_form = create_model_personality_form(data=request.POST or None)

        if model_personality_form.is_valid():
            new_model_personlaity = model_personality_form.save(commit=False)
            new_model_personlaity.created_date = timezone.now()
            new_model_personlaity.save()
            context = {'new_model_personlaity':new_model_personlaity}
            messages.success(request, 'model personality created')
            return redirect('/daemon/new_model_personality/')
            

        model_personality_form = create_model_personality_form(request.GET or None)
        context = {'model_personality_form':model_personality_form}
        return render(request, 'bots/create_model_personality.html', context)
    
    def get_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        model_personality_form = create_model_personality_form()
        model_personality_form = form_to_json_schema(model_personality_form)
        json_form = {'message':'This form is used to create new model chats, you will find the relevant item(s) below. Please make sure your response follows the format provided below.',
                     'items':[
                         {'name': 'Model Personality Creation Form', 
                          'description':'This form is used to create model personalities. All fields must be filled for the form to be submitted.', 
                          'form':model_personality_form,
                          'format':{'Model Chats Creation Form': {
                        'personality_name':'unique name for personality',
                        'personality_description':'detailed version of what your agents personality is',
                        'personality_type':'type of personalities; pick from list',
                        }}},
                     ]}
        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        data = json.loads(request.body.decode('utf-8'))
        new_model_personalities_data = data['Model Personality Creation Form']
        if all(key in new_model_personalities_data for key in ['personality_name', 'personality_description', 'personality_type',]):
            model_personality_form = create_model_personality_form(new_model_personalities_data)
            
            if model_personality_form.is_valid():
                new_model_personlaity = model_personality_form.save(commit=False)
                new_model_personlaity.created_date = timezone.now()
                new_model_personlaity.save()
                context = {'new_model_personlaity':new_model_personlaity}
                data = {'message':'new model personality has been created.'}
                return JsonResponse(data)
            else:
                context = {'errors':model_personality_form.errors}
                print(model_personality_form.errors)
        
        print('model personality not created')
        data = {'message':'An error has occured, to create a model personality, please ensure your request follows the format below.',
                    'format':{'Model Chats Creation Form': {
                        'personality_name':'unique name for personality',
                        'personality_description':'detailed version of what your agents personality is',
                        'personality_type':'type of personalities; pick from list',
                        }}}
        return JsonResponse(data)
    
    @csrf_exempt
    def delete_model_personality(request, model_personality_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        if model_personality.objects.filter(id=model_personality_id).exists():
            model_personality_to_delete = model_personality.objects.get(id=model_personality_id)
            model_personality_to_delete.delete()
            
        messages.success(request, 'personality deleted')
        return redirect('/daemon/new_model_personality/')

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

class initiate_models(View):
    def get(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        models_to_initiate = pd.DataFrame(model_intiate.objects.all().values())
        context = {'models_to_initiate':models_to_initiate.to_dict('records')}
        context['django_models_list'] = models_dataset
        return render(request, 'bots/initiate_model.html', context)
    
    def post(self, request):
        if check_authentication(request) != None:
            return check_authentication(request)
        context = {}
        
        if model_intiate.objects.filter(id=request.POST['models_to_initiate']).exists():
            if request.POST['start_stop'] == "start":
                command_response = call_command('testin_initiate', int(request.POST['models_to_initiate']))
                context['message'] = command_response
            elif request.POST['start_stop'] == "stop":
                for pid in [pid for pid in os.listdir('/proc') if pid.isdigit()]:
                    try:
                        with open(os.path.join('/proc', pid, 'cmdline'), 'rb') as f:
                            cmdline = f.read().decode('utf-8', errors='ignore')
                            # Check if 'llama-server' exists in the process execution arguments
                            if 'llama-server' in cmdline:
                                os.kill(int(pid), signal.SIGTERM)  # Graceful stop
                    except (FileNotFoundError, ProcessLookupError, PermissionError):
                        continue

        models_to_initiate = pd.DataFrame(model_intiate.objects.all().values())
        context['models_to_initiate'] = models_to_initiate.to_dict('records')
        context['django_models_list'] = models_dataset        
        return render(request, 'bots/initiate_model.html', context)

    def quick_add_local_model(request):
        if check_authentication(request) != None:
            return check_authentication(request)

        try:
            new_initiatie_model = model_intiate.objects.create(
                model_base_name = "1",
                name_nd_quant = request.POST['quant_link'],
                path_to_build = "/usr/local/bin/",
                server_type = 'llama.cpp',)
            

            messages.success(request, "Your Model Added!")
        except:
            messages.ERROR(request, "Please try again!")
        
        return redirect("/daemon/initiate_models/")


class manage_model_messages(View):
    def get(self, request, model_chats_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        context = {}
        if model_base_user_connection.objects.filter(chat_user=request.user).exists():
            user_base_connection_list = model_base_user_connection.objects.filter(chat_user=request.user)
            user_base_model_list = model_base.objects.filter(id__in=user_base_connection_list.values_list('model_base_id', flat=True))
            user_model_connection_list = model_connection.objects.filter(model_base_id__in = user_base_model_list.values_list('id', flat=True))
        
        if model_chats.objects.filter(chat_user=request.user).exists():
            model_chats_list = pd.DataFrame(model_chats.objects.filter(chat_user=request.user).values())
            model_connections = pd.DataFrame()
            for i_model_chat, e_model_chat in enumerate(model_chats_list['model_connection_name_id'].unique()):
                temp_connection = pd.DataFrame(model_connection.objects.filter(id=e_model_chat).values())
                model_connections = pd.concat([temp_connection, model_connections], axis=0)
            model_chats_list = pd.merge(model_chats_list, model_connections, left_on='model_connection_name_id', right_on='id', how='left')
            context['model_chats_list'] = model_chats_list.to_dict('records')
        else:
            messages.success(request, 'user does not have any model chats')
            return redirect('/daemon/new_model_chat/')
        
        if chat_messages.objects.filter(message_model_chats_id=model_chats_id).exists():
            chat_messages_list = chat_messages.objects.filter(message_model_chats_id=model_chats_id).values()            
            chat_messages_list_df = pd.DataFrame(chat_messages_list)
            chat_messages_list_df['chat_message'] = chat_messages_list_df['chat_message'].apply(markdown.markdown)
            context['chat_messages_list'] = chat_messages_list_df.to_dict('records')
        else:
            context['chat_messages_list'] = {"none": "none"}

        personalities_list = pd.DataFrame(model_personality.objects.all().values())
        context['personalities'] = personalities_list.to_dict('records')
        model_agent_list = pd.DataFrame(user_model_connection_list.values())
        temp_model_base = pd.DataFrame(user_base_model_list.values())
        model_agent_list = pd.merge(model_agent_list, temp_model_base, left_on='model_base_id', right_on='id', how='left')
        context['model_agent'] = model_agent_list.to_dict('records')
        chat_messages_form = create_chat_messages_form(request.GET or None)
        context['chat_messages_form'] = chat_messages_form
        context['tools'] = [{"icon":'<i class="bi-fast-forward-btn"></i>', "value":"fast"}, 
                            {"icon":'<i class="bi-cpu"></i>', "value":"thinking"}, 
                            {"icon":'<i class="bi-search"></i>', "value":"websearch"},
                            {"icon":'<i class="bi-arrow-down"></i>', "value":"local_files"},
                            {"icon":'<i class="bi-file-arrow-down"></i>', "value":"audio_files"}]
        context['model_chats_id'] = model_chats_id
        return render(request, 'bots/manage_model_chats.html', context)
    
    def post(self, request, model_chats_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        context = {}
        if model_base_user_connection.objects.filter(chat_user=request.user).exists():
            user_base_connection_list = model_base_user_connection.objects.filter(chat_user=request.user)
            user_base_model_list = model_base.objects.filter(id__in=user_base_connection_list.values_list('model_base_id', flat=True))
            user_model_connection_list = model_connection.objects.filter(model_base_id__in = user_base_model_list.values_list('id', flat=True))

        if model_chats.objects.filter(chat_user=request.user).exists():
            model_chats_list = pd.DataFrame(model_chats.objects.filter(chat_user=request.user).values())
            if model_chats_id in model_chats_list['id'].astype(str).to_list():
                model_chats_connection_id = model_chats_list[model_chats_list['id'].astype(str)==model_chats_id]['model_connection_name_id'][:]
                if model_connection.objects.filter(id=request.POST['model_agent']).exists():
                    run_model_connection = model_connection.objects.get(id=request.POST['model_agent'])
                else:
                    run_model_connection = model_connection.objects.get(id=model_chats_connection_id)

                if run_model_connection.model_base.id in user_base_model_list.values_list('id', flat=True):
                    model_base_conn = model_base_user_connection.objects.get(chat_user=request.user, model_base_id=run_model_connection.model_base.id)
                    temp_model_base = model_base.objects.get(id=model_base_conn.model_base.id)

                if model_personality.objects.filter(id=request.POST['personalities']).exists():
                    chat_personality = model_personality.objects.filter(id=request.POST['personalities']).values()
                else:
                    chat_personality = ""
                                
                chat_messages_form = create_chat_messages_form(data=request.POST or None)
                user_message = None

                if chat_messages_form.is_valid():
                    new_chat_messages = chat_messages_form.save(commit=False)
                    user_message = new_chat_messages.chat_message
                    new_chat_messages.created_date = timezone.now()
                    new_chat_messages.message_model_chats = model_chats.objects.get(id=model_chats_id)
                    new_chat_messages.chat_sender = 'user'
                    new_chat_messages.chat_meta = ''
                    new_chat_messages.save()
                
                chat_history = []
                if chat_messages.objects.filter(message_model_chats_id=model_chats_id).exists():
                    chat_history = pd.DataFrame(chat_messages.objects.filter(message_model_chats_id=model_chats_id).values())
                    check_chat_history = pd.DataFrame(chat_message_summarized.objects.filter(chat_message_id__in=chat_history['id'].to_list()).values())
                    if check_chat_history.empty:
                        checked_chat_history = chat_history                   
                    else:
                        check_chat_history = check_chat_history[check_chat_history['chat_summarized']==True]
                        checked_chat_history = chat_history[~chat_history['id'].isin(check_chat_history['chat_message_id'])]

                    if internal_document.objects.filter(document_name='user_chat_summary__chat_id__'+str(model_chats_id)).exists():
                        chat_summary_obj = internal_document.objects.get(document_name='user_chat_summary__chat_id__'+str(model_chats_id))        
                        if internal_document_version.objects.filter(internal_document=chat_summary_obj).exists():
                            internal_document_version_list = internal_document_version.objects.filter(internal_document=chat_summary_obj)
                            latest_doc_version = pd.DataFrame(internal_document_version_list.values())
                            latest_doc_version = latest_doc_version[latest_doc_version['document_version'] == latest_doc_version['document_version'].max()]
                            chat_summary_obj = latest_doc_version["document_text"].iloc[0]
                        
                    else:
                        chat_summary_obj = "" 

                run_model_reponse = send_message_to_model(user_message, user_request=request, chat_summary=chat_summary_obj, personality=chat_personality, 
                            chat_tool=request.POST['tools'], chat_history_list=checked_chat_history,
                            model_name=run_model_connection.model_name,
                            model_base=temp_model_base.model_base_url, 
                            model_api_key=model_base_conn.model_api_key, )
                                
                model_message_response = chat_messages.objects.create( date_created = timezone.now(),
                    message_model_chats = model_chats.objects.get(id=model_chats_id), chat_sender = 'model',
                    chat_meta = run_model_reponse.response_metadata, chat_message = run_model_reponse.content,)

            model_chats_list = pd.DataFrame(model_chats.objects.filter(chat_user=request.user).values())
            model_connections = pd.DataFrame()
            for i_model_chat, e_model_chat in enumerate(model_chats_list['model_connection_name_id'].unique()):
                temp_connection = pd.DataFrame(model_connection.objects.filter(id=e_model_chat).values())
                model_connections = pd.concat([temp_connection, model_connections], axis=0)
            model_chats_list = pd.merge(model_chats_list, model_connections, left_on='model_connection_name_id', right_on='id', how='left')
            context['model_chats_list'] = model_chats_list.to_dict('records')
        else:
            messages.success(request, 'user does not have any model chats')
            return redirect('/daemon/new_model_chat/')
        
        
        if chat_messages.objects.filter(message_model_chats_id=model_chats_id).exists():
            chat_messages_list = chat_messages.objects.filter(message_model_chats_id=model_chats_id).values()            
            chat_messages_list_df = pd.DataFrame(chat_messages_list)
            chat_messages_list_df['chat_message'] = chat_messages_list_df['chat_message'].apply(markdown.markdown)
            context['chat_messages_list'] = chat_messages_list_df.to_dict('records')
        else:
            context['chat_messages_list'] = {"none":"none"}

        personalities_list = pd.DataFrame(model_personality.objects.all().values())
        context['personalities'] = personalities_list.to_dict('records')
        model_agent_list = pd.DataFrame(user_model_connection_list.values())
        temp_model_base = pd.DataFrame(user_base_model_list.values())
        model_agent_list = pd.merge(model_agent_list, temp_model_base, left_on='model_base_id', right_on='id', how='left')
        context['model_agent'] = model_agent_list.to_dict('records')
        chat_messages_form = create_chat_messages_form(request.GET or None)
        context['chat_messages_form'] = chat_messages_form
        context['tools'] = [{"icon":'<i class="bi-fast-forward-btn"></i>', "value":"fast"}, 
                            {"icon":'<i class="bi-cpu"></i>', "value":"thinking"}, 
                            {"icon":'<i class="bi-search"></i>', "value":"websearch"},
                            {"icon":'<i class="bi-arrow-down"></i>', "value":"local_files"},
                            {"icon":'<i class="bi-file-arrow-down"></i>', "value":"audio_files"}]
        context['model_chats_id'] = model_chats_id
        return render(request, 'bots/manage_model_chats.html', context)
    
    def summarize_chat_button(request, model_chats_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        context = {}

        summarize_chat(model_chat_id=model_chats_id, request=request)
        return redirect(f'/daemon/model_chat_messages/{model_chats_id}')
    
    def chat_plan_button(request, model_chats_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        context = {}

        if request.POST.get('plan_prompt'):
            plan_prompt = request.POST['plan_prompt']
            temp_model_chat = model_chats.objects.get(id=model_chats_id)
            temp = create_chat_plan(model_chat_id=model_chats_id, plan_prompt=plan_prompt)
            temp_user = user_info.objects.get(user=request.user)
            new_project = project(project_name=temp_model_chat.chat_title, project_description=str(temp), pm_owner=temp_user)
            new_project.save()

            completed_forms_list = []
            for i, e_objective in enumerate(temp):
                task_forms_list = []
                temp_dict = e_objective['project_tasks']
                
                for i_2, e_task in enumerate(temp_dict):
                    e_task['task_project'] = new_project
                    temp_form = create_new_tasks(initial=e_task)
                    task_forms_list.append({"form":temp_form})

                completed_forms_list.append({f"objective":e_objective['project_objective'], "forms":task_forms_list, "temp_dict":temp_dict})

            context['completed_forms_list'] = completed_forms_list
            return render(request, 'bots/manage_model_chats.html', context)

        else:
            if request.method == 'POST':
                names = request.POST.getlist('task_name')
                descriptions = request.POST.getlist('task_description')
                start_dates = request.POST.getlist('start_date')
                soft_due_dates = request.POST.getlist('soft_due_date')
                hard_due_dates = request.POST.getlist('hard_due_date')
                statuses = request.POST.getlist('task_status')
                schedules = request.POST.getlist('task_schedule')
                task_projects = request.POST.getlist('task_project')

                # Combine them into a list of individual dictionaries
                tasks = []
                for name, desc, start, soft, hard, status, sched, proj in zip(names, descriptions, start_dates, soft_due_dates, hard_due_dates, statuses, schedules, task_projects):
                    task_data = {'task_name': name,
                        'task_description': desc,
                        'start_date': start,
                        'soft_due_date': soft,
                        'hard_due_date': hard,
                        'task_status': status,
                        'task_schedule': sched,
                        'task_project': project.objects.get(project_name=proj),}
                    tasks.append(task_data)
                    #print(task_data)    
            
            forms = []
            for form_prefix in tasks:
                print(form_prefix)

                temp_form = create_new_tasks(data=form_prefix)
                
                if temp_form.is_valid():
                    forms.append(temp_form)

            if all(form.is_valid() for form in forms):
                for form in forms:
                    form.save() 
            
                return redirect('/cadence/projects/')
            else:
                return redirect('/daemon/new_model_chat/')
    
    def get_api(request, model_chats_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        
        context = {}
        
        if model_chats.objects.filter(chat_user=request.user).exists():
            model_chats_list = pd.DataFrame(model_chats.objects.filter(chat_user=request.user).values())
            context['model_chats_list'] = model_chats_list.to_dict('records')
        else:
            messages.success(request, 'user does not have any model chats')
            return redirect('/daemon/new_model_chat/')
        
        if chat_messages.objects.filter(message_model_chats_id=model_chats_id).exists():
            chat_messages_list = pd.DataFrame(chat_messages.objects.filter(message_model_chats_id=model_chats_id).values())
            context['chat_messages_list'] = chat_messages_list.to_dict('records')

        chat_messages_form = create_chat_messages_form()
        context['chat_messages_form'] = chat_messages_form
        json_form = {'message':'This form is used to send messages to models',
                     'items':[
                         {'name': 'Chat Message Form', 
                          'description':'This form is used to create projects. All fields must be filled for the form to be submitted.', 
                          'form':chat_messages_form,
                          'format':{'Chat Message Form': {'chat_message':'message to send to model',}},
                          'context': context,}]}

        return JsonResponse(json_form)
    
    @csrf_exempt
    def post_api(request, model_chats_id):
        if check_authentication(request) != None:
            return check_authentication(request)
        data = json.loads(request.body.decode('utf-8'))
        new_message = data['Chat Message Form']

        context = {}

        if model_chats.objects.filter(chat_user=request.user).exists():
            model_chats_list = pd.DataFrame(model_chats.objects.filter(chat_user=request.user).values())
            if model_chats_id in model_chats_list['id'].astype(str).to_list():
                model_chats_connection_id = model_chats_list[model_chats_list['id'].astype(str)==model_chats_id]['model_connection_name_id'][:]
                run_model_connection = model_connection.objects.get(id=model_chats_connection_id)

                if all(key in new_message for key in ['chat_message',]):
                    chat_messages_form = create_chat_messages_form(new_message)
                
                    user_message = None

                    if chat_messages_form.is_valid():
                        new_chat_messages = chat_messages_form.save(commit=False)
                        user_message = new_chat_messages.chat_message
                        new_chat_messages.created_date = timezone.now()
                        new_chat_messages.message_model_chats = model_chats.objects.get(id=model_chats_id)
                        new_chat_messages.chat_sender = 'user'
                        new_chat_messages.chat_meta = ''
                        new_chat_messages.save()
                    
                    chat_history = []
                    if chat_messages.objects.filter(message_model_chats_id=model_chats_id).exists():
                        chat_history = pd.DataFrame(chat_messages.objects.filter(message_model_chats_id=model_chats_id).values())
                    
                    run_model_reponse = send_message_to_model(user_message, 
                            model_base=run_model_connection.model_base,
                            model_name=run_model_connection.model_name, 
                            model_api_key=run_model_connection.model_api_key,
                            chat_history_list=chat_history,)
                    
                    model_message_response = chat_messages.objects.create(
                        date_created = timezone.now(),
                        message_model_chats = model_chats.objects.get(id=model_chats_id),
                        chat_sender = 'model',
                        chat_meta = run_model_reponse.usage_metadata,
                        chat_message = run_model_reponse,)
                    
                    data = {'model_response':str(run_model_reponse)}
                    return JsonResponse(data)
                
                else:
                    data = {'message':'An error has occured, to send a message to a model, please ensure your request follows the format below.',
                    'format':{'Chat Message Form': {'chat_message':'message to send to model',}}}
                    return JsonResponse(data)
    