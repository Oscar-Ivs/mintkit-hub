from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from .models import Profile
from storefronts.models import Storefront
from .forms import ProfileForm



def register(request):
    """
    Simple registration view using Django's built-in UserCreationForm.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your account has been created. You can now log in.")
            return redirect('login')
    else:
        form = UserCreationForm()

    context = {
        'form': form,
    }
    return render(request, 'accounts/register.html', context)


def logout_view(request):
    """
    Log the user out and redirect to the homepage.
    """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')

@login_required
def dashboard(request):
    profile = request.user.profile
    storefront = Storefront.objects.filter(profile=profile).first()
    context = {
        "profile": profile,
        "storefront": storefront,
    }
    return render(request, "accounts/dashboard.html", context)

@login_required
def edit_profile(request):
    """
    Allow the logged-in user to edit their business profile.
    """
    profile = request.user.profile  # created automatically by the signal

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your business profile has been updated.")
            return redirect("dashboard")
    else:
        form = ProfileForm(instance=profile)

    context = {
        "form": form,
        "profile": profile,
    }
    return render(request, "accounts/edit_profile.html", context)
