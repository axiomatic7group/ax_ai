from django.contrib import admin
from django.urls import path, include
from . import views
#get_deliverable_data
urlpatterns = [

    path('delete_stakeholder_to_project_api_post/<slug:stakeholder_project_id>/', views.add_stakeholder_project.delete_stakeholder_project, name='delete_stakeholder_project'),
    path('add_stakeholder_to_project_api_post/', views.add_stakeholder_project.post_api, name='add_stakeholder_to_project_api_post'),
    path('add_stakeholder_to_project_api_get/', views.add_stakeholder_project.get_api, name='add_stakeholder_to_project_api_get'),
    path('add_stakeholder_to_project/', views.add_stakeholder_project.as_view(), name='add_stakeholder_to_project_html'),


    path('task_attachements/<slug:project_name>/<slug:task_id>/', views.task_management.create_task_attachements, name='task_attachements'),

    path('task_comments_post_api/<slug:project_name>/<slug:task_id>/', views.task_management.create_task_comments_post_api, name='task_comments_post_api'),
    path('task_comments_get_api/<slug:project_name>/<slug:task_id>/', views.task_management.create_task_comments_get_api, name='task_comments_get_api'),
    path('task_comments/<slug:project_name>/<slug:task_id>/', views.task_management.create_task_comments, name='task_comments'),

    path('delete_task_prerequisite_api_post/<slug:task_prerequisite_id>/', views.create_prerequisites.delete_task_prerequisite, name='delete_task_prerequisite'),
    path('add_task_prerequisite_api_post/', views.create_prerequisites.post_api, name='add_task_prerequisite_api_post'),
    path('add_task_prerequisite_api_get/', views.create_prerequisites.get_api, name='add_task_prerequisite_api_get'),
    path('add_task_prerequisite/', views.create_prerequisites.as_view(), name='add_task_prerequisite_html'),

    path('user_message_view/<slug:message_sender>', views.user_message_view.as_view(), name='user_message_view'),

    path('delete_user_message_api_post/<slug:user_message_id>/', views.add_user_message.delete_user_messages, name='delete_user_message'),
    path('add_user_message_api_post/', views.add_user_message.post_api, name='add_user_message_api_post'),
    path('add_user_message_api_get/', views.add_user_message.get_api, name='add_user_message_api_get'),
    path('add_user_messages/', views.add_user_message.as_view(), name='add_user_message_html'),

    path('delete_task_status_list_api_post/<slug:task_status_list_id>/', views.add_task_status.delete_task_status_list, name='delete_task_status_list'),
    path('add_task_status_list_api_post/', views.add_task_status.post_api, name='add_task_status_list_api_post'),
    path('add_task_status_list_api_get/', views.add_task_status.get_api, name='add_task_status_list_api_get'),
    path('add_task_status_list/', views.add_task_status.as_view(), name='add_task_status_list_html'),

    path('projects/<slug:project_name>/<slug:task_id>/', views.manage_projects.get_project_task_data, name='get_project_task_data'),
    path('deliverables/<slug:deliverable_id>/', views.manage_projects.get_deliverable_data, name='get_deliverable_data'),
    path('projects/<slug:project_name>/', views.manage_projects.get_project_data, name='get_project_data'),
    path('projects/', views.manage_projects.as_view(), name='manage_projects'),

    path('delete_deliverable_grouping_api_post/<slug:deliverable_grouping_id>/', views.add_deliverable_grouping.delete_deliverable_grouping, name='delete_deliverable_grouping'),
    path('add_deliverable_grouping_api_post/', views.add_deliverable_grouping.post_api, name='add_deliverable_grouping_api_post'),
    path('add_deliverable_grouping_api_get/', views.add_deliverable_grouping.get_api, name='add_deliverable_grouping_api_get'),
    path('add_deliverable_grouping/', views.add_deliverable_grouping.as_view(), name='add_deliverable_grouping_html'),

    path('delete_project_grouping_api_post/<slug:project_grouping_id>/', views.add_project_grouping.delete_project_grouping, name='delete_project_grouping'),
    path('add_project_grouping_api_post/', views.add_project_grouping.post_api, name='add_project_grouping_api_post'),
    path('add_project_grouping_api_get/', views.add_project_grouping.get_api, name='add_project_grouping_api_get'),
    path('add_project_grouping/', views.add_project_grouping.as_view(), name='add_project_grouping_html'),

    path('delete_deliverable_group_api_post/<slug:deliverable_group_id>/', views.add_deliverable_group.delete_deliverable_group, name='delete_deliverable_group'),
    path('add_deliverable_group_api_post/', views.add_deliverable_group.post_api, name='add_deliverable_group_api_post'),
    path('add_deliverable_group_api_get/', views.add_deliverable_group.get_api, name='add_deliverable_group_api_get'),
    path('add_deliverable_group/', views.add_deliverable_group.as_view(), name='add_deliverable_group_html'),

    path('delete_project_group_api_post/<slug:project_group_id>/', views.add_project_group.delete_project_group, name='delete_project_group'),
    path('add_project_group_api_post/', views.add_project_group.post_api, name='add_project_group_api_post'),
    path('add_project_group_api_get/', views.add_project_group.get_api, name='add_project_group_api_get'),
    path('add_project_group/', views.add_project_group.as_view(), name='add_project_group_html'),

    path('delete_stakeholder_to_deliverable_api_post/<slug:stakeholder_deliverable_id>/', views.add_stakeholder_deliverable.delete_stakeholder_deliverable, name='delete_stakeholder_deliverable'),
    path('add_stakeholder_to_deliverable_api_post/', views.add_stakeholder_deliverable.post_api, name='add_stakeholder_to_deliverable_api_post'),
    path('add_stakeholder_to_deliverable_api_get/', views.add_stakeholder_deliverable.get_api, name='add_stakeholder_to_deliverable_api_get'),
    path('add_stakeholder_to_deliverable/', views.add_stakeholder_deliverable.as_view(), name='add_stakeholder_to_deliverable_html'),

    path('delete_task_staff_api_post/<slug:task_staff_id>/', views.add_task_staff.delete_task_staff, name='delete_task_staff'),
    path('add_task_staff_api_post/', views.add_task_staff.post_api, name='add_task_staff_api_post'),
    path('add_task_staff_api_get/', views.add_task_staff.get_api, name='add_task_staff_api_get'),
    path('add_task_staff/', views.add_task_staff.as_view(), name='add_task_staff_html'),

    path('complete_tasks/<slug:task_id>/', views.delete_tasks.complete_task, name='complete_task'),
    path('delete_tasks/<slug:task_id>/', views.delete_tasks.delete_task, name='delete_tasks'),

    path('create_tasks_api_post/', views.create_tasks.post_api, name='create_tasks_api_post'),
    path('create_tasks_api_get/', views.create_tasks.get_api, name='create_tasks_api_get'),
    path('create_tasks/', views.create_tasks.as_view(), name='create_tasks_html'),
    
    path('delete_deliverable/<slug:deliverable_id>/', views.create_deliverable.delete_deliverable, name='delete_deliverable'),
    path('create_deliverable_api_post/', views.create_deliverable.post_api, name='create_deliverable_api_post'),
    path('create_deliverable_api_get/', views.create_deliverable.get_api, name='create_deliverable_api_get'),
    path('create_deliverable/', views.create_deliverable.as_view(), name='create_deliverable_html'),
    
    path('create_project_api_post/', views.create_project.post_api, name='create_project_api_post'),
    path('create_project_api_get/', views.create_project.get_api, name='create_project_api_get'),
    path('create_project/', views.create_project.as_view(), name='create_project_html'),

    path('delete_project_api_post/', views.delete_project.post_api, name='delete_project_api_post'),
    path('delete_project_api_get/', views.delete_project.get_api, name='delete_project_api_get'),
    path('delete_project/', views.delete_project.as_view(), name='delete_project_html'),

]