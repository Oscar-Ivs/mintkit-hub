# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("pricing/", views.pricing, name="pricing"),
    path("faq/", views.faq, name="faq"),
    path("studio/", views.studio, name="studio"),
]
