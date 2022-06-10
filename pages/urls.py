

from django.contrib import admin
from django.urls import path, include
from pages import views
urlpatterns = [
    path('', views.home, name='home'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('gallery/', views.gallery, name='gallery'),
    path('shop/', views.shop, name='shop'),
    path('coming_soon/', views.coming_soon, name='coming_soon')
]
