

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
    path('south-west-fashion-week/',views.swfw_portal, name="swfw_portal"),
    # path('nominate/', views.nominate, name='nominate'),
    # path('nominate_redirect/', views.nominate_redirect, name='nominate_redirect'),
    path('dashboard/',views.dashboard,name="dashboard"),
    path('login/', views.login, name="login"),
    path('modify_nomination_status/<int:id>',views.modify_nomination_status,name="modify_nomination_status"),
    path('election_status/<int:id>',views.election_status,name="election_status"),
    # path('election_results',views.election_results, name="election_results"),
    path('choose_category', views.choose_category, name="choose_category"),
    # path('vote', views.vote, name="vote"),
    path('vote_page/<id>', views.vote_page, name="vote_page"),

    path("events/<slug:slug>/", views.event_detail, name="event_detail"),
    path(
        "events/<slug:slug>/checkout/init/",
        views.vote_checkout_init,
        name="vote_checkout_init",
    ),
    path("paystack/verify/", views.paystack_verify, name="paystack_verify"),
    path("paystack/webhook/", views.paystack_webhook, name="paystack_webhook"),
    path("events/<slug:event_slug>/candidate/login/", views.candidate_login, name="candidate_login"),
    path("events/<slug:event_slug>/candidate/results/", views.candidate_results, name="candidate_results"),
    path("events/<slug:event_slug>/candidate/logout/", views.candidate_logout, name="candidate_logout"),


]
