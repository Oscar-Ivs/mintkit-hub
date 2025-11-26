from django import forms
from .models import Storefront


class StorefrontForm(forms.ModelForm):
    class Meta:
        model = Storefront
        fields = ['name', 'headline', 'description', 'is_active']
