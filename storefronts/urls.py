# storefronts/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("my/", views.my_storefront, name="my_storefront"),
    path("explore/", views.explore_storefronts, name="explore_storefronts"),

    # Layout editor endpoints (owner dashboard)
    # IMPORTANT: app is already under /storefront/ so do not prefix with "storefront/" again.
    path(
        "<int:storefront_id>/layout/load/",
        views.storefront_layout_load,
        name="storefront_layout_load",
    ),
    path(
        "<int:storefront_id>/layout/save/",
        views.storefront_layout_save,
        name="storefront_layout_save",
    ),

    # Public storefront page
    path("<slug:slug>/", views.storefront_detail, name="storefront_detail"),

    # Public featured card detail page
    path("<slug:slug>/cards/<int:card_id>/", views.storefront_card_detail, name="storefront_card_detail"),

]
