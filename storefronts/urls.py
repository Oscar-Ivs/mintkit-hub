# storefronts/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("my/", views.my_storefront, name="my_storefront"),
    path("explore/", views.explore_storefronts, name="explore_storefronts"),
    path("<slug:slug>/", views.storefront_detail, name="storefront_detail"),
]
