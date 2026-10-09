import pandas as pd
from bots.models import *
from django.core.management.base import BaseCommand, CommandError
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

import subprocess, requests

def send_message_to_model(promt_message,
                          chat_summary="",
                          model_base="http://127.0.0.1:8080",
                          model_name="local-model", 
                          model_api_key="dummy_key",  
                          chat_history_list=None,
                          run_tempereature=0.75):
    
    run_model = ChatOpenAI(
        base_url=model_base,
        api_key=model_api_key,
        model=model_name,
        temperature=run_tempereature,)
    
    personality = "You are an AI Agent being observed for performance and efficiency." \
    "Your primary objective is to summarize the context provided in the chat history." \
    "The summary you provide will be used to replace chat history goin forward and use your summary to substitute this." \
    "Be sure your summary is organized and detailed, be sure to specifically include any relevant facts, dates, names, places, ideas, etc." \
    "Create subcategories in your output to specify these if needed." \
    "From time to time you will also be asked to update an existing summary with new chat history, be sure to make changes as needed." \
    "Update old specific and relevant points you might have writtne down as their circumstnaces change." \
    "Be sure to keep track of ideas and thoughts and mention their progression as this summary will be used to provided feedback to the user about their chats." \
    "Remeber, you are being observed for your performance, be sure to follow instructions well and keep your repsonses brief and to the point."
    
    if isinstance(chat_history_list, pd.DataFrame):
        chat_history = []
        chat_history_list.sort_values('date_created')
        chat_history_list = chat_history_list.reset_index()
        for i_message, e_message in chat_history_list.iterrows():
            if e_message['chat_sender'] == "user":
                chat_history.append(HumanMessage(content=e_message['chat_message']))
            elif e_message['chat_sender'] == "model":
                chat_history.append(AIMessage(content=e_message['chat_message']))
    else:
        chat_history = []
    
    system_context = {'system': personality,'chat_history_summary':chat_summary}

    user_prompt = ChatPromptTemplate.from_messages([("system", "{system_context}"), MessagesPlaceholder(variable_name="chat_history"), ("human", "{promt_message}"),])
    chain = user_prompt | run_model
    response = chain.invoke({"promt_message": promt_message, "system_context": system_context, "chat_history":chat_history})
    return response


def summarize_chat(model_chat_id):

    if model_chats.objects.filter(id=model_chat_id).exists:
        model_chats_to_sum = pd.DataFrame(model_chats.objects.filter(id=model_chat_id).values())
        chat_model_connection = pd.DataFrame(model_connection.objects.filter(id=model_chats_to_sum['model_connection_name_id'].iloc[0]).values())
        chat_messages_to_sum = pd.DataFrame(chat_messages.objects.filter(message_model_chats_id=model_chat_id).values())
        
        check_chat_history = pd.DataFrame(chat_message_summarized.objects.filter(chat_message_id__in=chat_messages_to_sum['id'].to_list()))
        if check_chat_history.empty:
            checked_chat_history = chat_messages_to_sum
            chat_summary = ""           
        else:
            check_chat_history = check_chat_history[check_chat_history['chat_summarized']==True]
            checked_chat_history = chat_messages_to_sum[~chat_messages_to_sum['id'].isin(check_chat_history['chat_message_id'])]

            chat_summary = pd.DataFrame(model_chats_summary.objects.filter(model_chat_id=model_chat_id).values())

        user_message = "please summarize the chat history to be used for future reference as instructed"
    
        message_to_send = send_message_to_model(user_message,
                                                chat_summary=chat_summary,
                                                model_base=chat_model_connection['model_base'].iloc[0],
                                                model_name=chat_model_connection['model_name'].iloc[0], 
                                                model_api_key=chat_model_connection['model_api_key'].iloc[0],
                                                chat_history_list=checked_chat_history,)
        
        new_chat_summary = model_chats_summary( 
                                      model_chat= model_chats.objects.get(id=model_chat_id),
                                      chat_summary = message_to_send.content,
                                      chat_title = message_to_send.content[:75])
        new_chat_summary.save()
        
        checked_chat_history_check = pd.DataFrame()
        checked_chat_history_check['chat_message'] = [chat_messages.objects.get(id=x) for x in checked_chat_history['id']]
        checked_chat_history_check['date_summairzed'] = timezone.now()
        checked_chat_history_check['chat_summarized'] = True

        instances = [chat_message_summarized(**row) for row in checked_chat_history_check.to_dict('records')]
        chat_message_summarized.objects.bulk_create(instances)

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('chat_to_summarize', type=int)

    def handle(self, *args, **options):
        chat_to_summarize = options['chat_to_summarize']
        summarize_chat(chat_to_summarize)
        