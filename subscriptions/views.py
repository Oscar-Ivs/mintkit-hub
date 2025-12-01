# subscriptions/views.py
from django.shortcuts import render


def subscriptions_home(request):
    """
    Placeholder page for subscription management.
    Later we'll show current plan, upgrade options, billing history, etc.
    """
    return render(request, "subscriptions/subscriptions_home.html")
