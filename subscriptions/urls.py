# subscriptions/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.subscriptions_home, name="subscriptions_home"),
]
