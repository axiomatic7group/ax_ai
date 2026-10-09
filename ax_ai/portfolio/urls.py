from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path("link_in_bio/<slug:user_info_id>", views.link_in_bio.see_link_in_bio, name="link_in_bio_view"),
    path("link_in_bio/", views.link_in_bio.as_view(), name="manage_link_in_bio_view"),
    path("faq/<slug:campaign_faq_id>", views.campaign_faq_view.as_view(), name="campaign_faq_view"),
    path("blog/<slug:blog_post_id>", views.campaign_faq_view.see_blog_post, name="campaign_blog_view"),
    path("service/<slug:project_id>", views.view_project.as_view(), name="service_view"),

    path("campaign/<slug:funnel_id>", views.view_campaign_funnel.as_view(), name="view_campaign_funnel_view"),
    path("campaign_all/<slug:funnel_id>", views.view_campaign_funnel.see_all_info, name="all_campaign_funnel_view"),
    path("create_campaign_funnel/", views.create_campaign_funnel.as_view(), name="create_campaign_funnel_view"),
    path("create_project/", views.create_new_projects.as_view(), name="create_new_project_view"),
    path("project/<slug:project_id>", views.view_project.as_view(), name="view_project_view"),
    path("", views.view_portfolio.as_view(), name="view_portfolio_view"),

]
