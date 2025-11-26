from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm


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
