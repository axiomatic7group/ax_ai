from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path('plan_chat_messages/<slug:model_chats_id>/', views.manage_model_messages.chat_plan_button, name='chat_plan_button'),

    path('quick_add_local_model/', views.initiate_models.quick_add_local_model, name='quick_add_local_model'),
    path('initiate_models/', views.initiate_models.as_view(), name='initiate_models'),

    path('model_chat_messages_post_api/<slug:model_chats_id>/', views.manage_model_messages.post_api, name='manage_model_messages_post_api'),
    path('model_chat_messages_ge_api/<slug:model_chats_id>/', views.manage_model_messages.get_api, name='manage_model_messages_get_api'),
    path('model_chat_messages/<slug:model_chats_id>/', views.manage_model_messages.as_view(), name='manage_model_messages'),

    path('summarize_chat_messages/<slug:model_chats_id>/', views.manage_model_messages.summarize_chat_button, name='summarize_chat_button'),

    path('delete_model_personality/<slug:model_personality_id>/', views.create_model_personality.delete_model_personality, name='delete_model_personality'),
    path('new_model_personality_api_post/', views.create_model_personality.post_api, name='create_model_personality_post_api'),
    path('new_model_personality_api_get/', views.create_model_personality.get_api, name='create_model_personality_get_api'),
    path('new_model_personality/', views.create_model_personality.as_view(), name='create_model_personality'),
    
    path('delete_model_chat/<slug:model_chats_id>/', views.create_model_chats.delete_model_chats, name='delete_model_chats'),
    path('new_model_chat_api_post/', views.create_model_chats.post_api, name='create_model_chat_post_api'),
    path('new_model_chat_api_get/', views.create_model_chats.get_api, name='create_model_chat_get_api'),
    path('new_model_chat/', views.create_model_chats.as_view(), name='create_model_chat'),

    path('delete_model/<slug:model_connection_id>/', views.create_model_connection.delete_model_connection, name='delete_model_connection'),
    path('new_model_api_post/', views.create_model_connection.post_api, name='create_model_connection_post_api'),
    path('new_model_api_get/', views.create_model_connection.get_api, name='create_model_connection_get_api'),
    path('new_model/', views.create_model_connection.as_view(), name='create_model_connection'),

    ]