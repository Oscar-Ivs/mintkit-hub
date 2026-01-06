# subscriptions/urls.py
from django.urls import path
from . import views
from .webhooks import stripe_webhook

urlpatterns = [
    path("start-trial/", views.start_trial, name="start_trial"),

    path("checkout/success/", views.checkout_success, name="subscriptions_checkout_success"),
    path("checkout/cancel/", views.checkout_cancel, name="subscriptions_checkout_cancel"),

    path("checkout/<str:plan_code>/", views.checkout, name="subscriptions_checkout"),

    path("portal/", views.billing_portal, name="subscriptions_billing_portal"),
    path("webhook/", stripe_webhook, name="subscriptions_stripe_webhook"),
]
