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



from django.contrib import admin
from django.urls import path, include

from . import views


from django.contrib.sitemaps.views import sitemap

from .sitemaps import StaticViewSitemap, BlogSitemap, FAQSitemap, FunnelSitemap, ServicesSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'blog': BlogSitemap,
    'faq': FAQSitemap,
    'funnels': FunnelSitemap,
    'services': ServicesSitemap,
}





urlpatterns = [
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

    path('apps/stock_dashboard/', include("stock_dashboard.urls")),
    
    path('daemon/', include("bots.urls")),
    path('synapse/', include("synapse.urls")),
    path('axiom/', include("axiom.urls")),
    path('cadence/', include("pm.urls")),
    path('admin/', admin.site.urls),

    path('portfolio/', include("portfolio.urls")),
    path('login/', views.authenticate_users.as_view(), name='login_html'),
    path('signup/', views.create_new_user.as_view(), name='signup_html'),
    path('contact/', views.contact_us.as_view(), name='contact_us_html'),
    path('about/', views.about_us.about_us, name='about_us_html'),
    path('privacy/', views.about_us.privacy, name='privacy_html'),
    path('terms/', views.about_us.terms, name='terms_html'),
    path('llms/', views.about_us.llms, name='llms_html'),
    path('', views.home_page.as_view(), name='home_page_html'),
]
