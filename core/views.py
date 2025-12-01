# core/views.py
from django.shortcuts import render, redirect


def home(request):
    """
    Public landing page for MintKit Hub.
    """
    return render(request, "core/home.html")


def about(request):
    """
    Simple About page stub.
    """
    return render(request, "core/about.html")


def pricing(request):
    """
    Simple Pricing page stub.
    Later we'll add actual plan details.
    """
    return render(request, "core/pricing.html")


def faq(request):
    """
    Simple FAQ page stub.
    """
    return render(request, "core/faq.html")


def studio(request):
    """
    Redirect helper to MintKit Studio.

    For now it's just a placeholder.
    Later, when studio.mintkit.co.uk is mapped,
    you can update STUDIO_URL to that domain.
    """
    STUDIO_URL = "https://studio.mintkit.co.uk/"  # change when ready
    return redirect(STUDIO_URL)
