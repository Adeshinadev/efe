

from django.contrib import admin
from django.urls import path, include
from pages import views
urlpatterns = [
    path('', views.home, name='home'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('gallery/', views.gallery, name='gallery'),
    path('shop/', views.shop, name='shop'),
    path('coming_soon/', views.coming_soon, name='coming_soon'),
    path('efe_portal/',views.efe_portal, name="efe_portal"),
    path('nominate/', views.nominate, name='nominate'),
    path('nominate_redirect/', views.nominate_redirect, name='nominate_redirect'),
    path('dashboard/',views.dashboard,name="dashboard"),
    path('login', views.login, name="login"),
    path('modify_nomination_status/<int:id>',views.modify_nomination_status,name="modify_nomination_status"),
    path('election_status/<int:id>',views.election_status,name="election_status"),
    path('nomination_result',views.nomination_result, name="nomination_result")
]
