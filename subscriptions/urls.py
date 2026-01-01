# subscriptions/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("start-trial/", views.start_trial, name="start_trial"),
]
