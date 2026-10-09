from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('stock_view/', views.function_management_dashboard.as_view(), name='stock_view_html'),
    path('stock_view/<slug:stock_ticker>', views.function_management_dashboard.as_view(), name='stock_view_html'),

]