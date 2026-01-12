from django.urls import path
from . import views

urlpatterns = [
    path("v/<uuid:token>/", views.card_viewer, name="card_viewer"),
    path("api/studio/send-card-email/", views.send_card_email_api, name="send_card_email_api"),
]
