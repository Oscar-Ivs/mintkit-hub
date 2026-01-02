# subscriptions/urls.py
from django.urls import path
from . import views
from django import forms

from .models import MintKitAccess

urlpatterns = [
    path("start-trial/", views.start_trial, name="start_trial"),
]
