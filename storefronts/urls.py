from django.urls import path
from . import views

urlpatterns = [
    path('my/', views.my_storefront, name='my_storefront'),
    path('<slug:slug>/', views.storefront_detail, name='storefront_detail'),
]
