from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('function_management_dashboard/', views.function_management_dashboard.as_view(), name='function_management_dashboard_html'),

    path('delete_input_value_to_connections_function/<slug:input_value_to_connections_function_id>/', views.manage_input_value_to_connections_function.delete_input_value_to_connections_function, name='delete_input_value_to_connections_function'),
    path('add_input_value_to_connections_function_api_post/', views.manage_input_value_to_connections_function.post_api, name='add_input_value_to_connections_function_api_post'),
    path('add_input_value_to_connections_function_api_get/', views.manage_input_value_to_connections_function.get_api, name='add_input_value_to_connections_function_api_get'),
    path('add_input_value_to_connections_function/', views.manage_input_value_to_connections_function.as_view(), name='add_input_value_to_connections_function_html'),

    path('delete_connection_function_saved_inputs/<slug:connection_function_saved_inputs_id>/', views.manage_connection_function_saved_inputs.delete_connection_function_saved_inputs, name='delete_connection_function_saved_inputs'),
    path('add_connection_function_saved_inputs_api_post/', views.manage_connection_function_saved_inputs.post_api, name='add_connection_function_saved_inputs_api_post'),
    path('add_connection_function_saved_inputs_api_get/', views.manage_connection_function_saved_inputs.get_api, name='add_connection_function_saved_inputs_api_get'),
    path('add_connection_function_saved_inputs/', views.manage_connection_function_saved_inputs.as_view(), name='add_connection_function_saved_inputs_html'),

    path('delete_local_function_files/<slug:local_function_files_id>/', views.manage_local_function_files.delete_local_function_files, name='delete_local_function_files'),
    path('add_local_function_files_api_post/', views.manage_local_function_files.post_api, name='add_local_function_files_api_post'),
    path('add_local_function_files_api_get/', views.manage_local_function_files.get_api, name='add_local_function_files_api_get'),
    path('add_local_function_files/', views.manage_local_function_files.as_view(), name='add_local_function_files_html'),

    path('delete_local_data_files/<slug:local_data_files_id>/', views.manage_local_data_files.delete_local_data_files, name='delete_local_data_files'),
    path('add_local_data_files_api_post/', views.manage_local_data_files.post_api, name='add_local_data_files_api_post'),
    path('add_local_data_files_api_get/', views.manage_local_data_files.get_api, name='add_local_data_files_api_get'),
    path('add_local_data_files/', views.manage_local_data_files.as_view(), name='add_local_data_files_html'),

    path('delete_datatable_dictionary/<slug:datatable_dictionary_id>/', views.manage_datatable_dictionary.delete_datatable_dictionary, name='delete_datatable_dictionary'),
    path('add_datatable_dictionary_api_post/', views.manage_datatable_dictionary.post_api, name='add_datatable_dictionary_api_post'),
    path('add_datatable_dictionary_api_get/', views.manage_datatable_dictionary.get_api, name='add_datatable_dictionary_api_get'),
    path('add_datatable_dictionary/', views.manage_datatable_dictionary.as_view(), name='add_datatable_dictionary_html'),

    path('delete_dictionary_keys/<slug:dictionary_keys_id>/', views.manage_dictionary_keys.delete_dictionary_keys, name='delete_dictionary_keys'),
    path('add_dictionary_keys_api_post/', views.manage_dictionary_keys.post_api, name='add_dictionary_keys_api_post'),
    path('add_dictionary_keys_api_get/', views.manage_dictionary_keys.get_api, name='add_dictionary_keys_api_get'),
    path('add_multiple_dictionary_keys/', views.manage_dictionary_keys.multiple_dictionary_keys, name='multiple_dictionary_keys_html'),
    path('add_dictionary_keys/', views.manage_dictionary_keys.as_view(), name='add_dictionary_keys_html'),

    path('delete_datatable_groups/<slug:datatable_groups_id>/', views.manage_datatable_groups.delete_datatable_groups, name='delete_datatable_groups'),
    path('add_datatable_groups_api_post/', views.manage_datatable_groups.post_api, name='add_datatable_groups_api_post'),
    path('add_datatable_groups_api_get/', views.manage_datatable_groups.get_api, name='add_datatable_groups_api_get'),
    path('add_datatable_groups/', views.manage_datatable_groups.as_view(), name='add_datatable_groups_html'),

    path('delete_connection_functions/<slug:connection_functions_id>/', views.manage_connection_functions.delete_connection_functions, name='delete_connection_functions'),
    path('add_connection_functions_api_post/', views.manage_connection_functions.post_api, name='add_connection_functions_api_post'),
    path('add_connection_functions_api_get/', views.manage_connection_functions.get_api, name='add_connection_functions_api_get'),
    path('add_connection_functions/', views.manage_connection_functions.as_view(), name='add_connection_functions_html'),

    path('delete_api_connection/<slug:api_connection_id>/', views.manage_api_connection.delete_api_connection, name='delete_api_connection'),
    path('add_api_connection_api_post/', views.manage_api_connection.post_api, name='add_api_connection_api_post'),
    path('add_api_connection_api_get/', views.manage_api_connection.get_api, name='add_api_connection_api_get'),
    path('add_api_connection/', views.manage_api_connection.as_view(), name='add_api_connection_html'),

    path('delete_datatable_connection/<slug:datatable_connection_id>/', views.manage_datatable_connection.delete_datatable_connection, name='delete_datatable_connection'),
    path('add_datatable_connection_api_post/', views.manage_datatable_connection.post_api, name='add_datatable_connection_api_post'),
    path('add_datatable_connection_api_get/', views.manage_datatable_connection.get_api, name='add_datatable_connection_api_get'),
    path('add_datatable_connection/', views.manage_datatable_connection.as_view(), name='add_datatable_connection_html'),

    path('delete_database_user_connection/<slug:database_user_connection_id>/', views.manage_database_user_connection.delete_database_user_connection, name='delete_database_user_connection'),
    path('add_database_user_connection_api_post/', views.manage_database_user_connection.post_api, name='add_database_user_connection_api_post'),
    path('add_database_user_connection_api_get/', views.manage_database_user_connection.get_api, name='add_database_user_connection_api_get'),
    path('add_database_user_connection/', views.manage_database_user_connection.as_view(), name='add_database_user_connection_html'),

    path('delete_database_connection/<slug:database_connection_id>/', views.manage_database_connection.delete_database_connection, name='delete_database_connection'),
    path('add_database_connection_api_post/', views.manage_database_connection.post_api, name='add_database_connection_api_post'),
    path('add_database_connection_api_get/', views.manage_database_connection.get_api, name='add_database_connection_api_get'),
    path('add_database_connection/', views.manage_database_connection.as_view(), name='add_database_connection_html'),

    #path('delete_api_post/', views.delete_user.post_api, name='delete_user_api'),
    #path('delete_api_get/', views.delete_user.get_api, name='delete_api'),
    #path('delete/', views.delete_user.as_view(), name='delete_html'),

    #path('signup_api_post/', views.create_new_user.post_api, name='create_user_api'),
    #path('signup_api_get/', views.create_new_user.get_api, name='signup_api'),
    #path('signup/', views.create_new_user.as_view(), name='signup_html'),

]