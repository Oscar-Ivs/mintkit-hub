from django.shortcuts import render

def home(request):
    """Public landing page for MintKit Hub."""
    return render(request, 'core/home.html')
