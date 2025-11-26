from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import Http404

from accounts.models import Profile
from .models import Storefront
from .forms import StorefrontForm


@login_required
def my_storefront(request):
    """
    Create or edit the logged-in user's storefront.
    """
    profile, _ = Profile.objects.get_or_create(user=request.user)
    storefront, created = Storefront.objects.get_or_create(owner=profile)

    if request.method == 'POST':
        form = StorefrontForm(request.POST, instance=storefront)
        if form.is_valid():
            form.save()
            return redirect('my_storefront')
    else:
        form = StorefrontForm(instance=storefront)

    context = {
        'form': form,
        'storefront': storefront,
        'created': created,
    }
    return render(request, 'storefronts/my_storefront.html', context)


def storefront_detail(request, slug):
    """
    Public storefront page.
    - Visible to everyone if is_active == True.
    - Owner or staff can view even if inactive.
    """
    storefront = get_object_or_404(Storefront, slug=slug)

    if not storefront.is_active:
        # Allow owner or staff; otherwise 404
        if not request.user.is_authenticated:
            raise Http404("This storefront is not available.")
        profile = getattr(request.user, 'profile', None)
        if not (request.user.is_staff or (profile and storefront.owner == profile)):
            raise Http404("This storefront is not available.")

    context = {
        'storefront': storefront,
    }
    return render(request, 'storefronts/storefront_detail.html', context)
