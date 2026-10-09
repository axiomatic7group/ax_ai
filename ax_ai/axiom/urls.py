from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('manage_document_version/<slug:internal_doc_id>', views.manage_document_versions.as_view(), name='manage_document_version_html'),
    path('create_internal_document/', views.manage_internal_documents.as_view(), name='manage_internal_documents_html'),

    path('project_runs/', views.manage_project_runs.as_view(), name='manage_project_runs_html'),

    path('project_template/', views.create_project_template.as_view(), name='create_project_template_html'),
    path('build_project_template/<slug:project_template_id>', views.build_project_template.as_view(), name='build_project_template_html'),
    path('run_project_template/<slug:project_template_id>', views.run_project_template.as_view(), name='run_project_template_html'),
    path('copy_project_template/<slug:project_template_id>', views.copy_project_template.as_view(), name='copy_project_template_html'),
]