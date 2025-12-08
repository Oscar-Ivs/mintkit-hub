# accounts/forms.py
from django import forms

from .models import Profile


class ProfileForm(forms.ModelForm):
    """
    Let a logged-in user edit their business profile.
    We don't expose the user field; that's set automatically in the view.
    """

    class Meta:
        model = Profile
        fields = [
            "business_name",
            "contact_email",
            "logo",
        ]
        widgets = {
            "business_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Beauty Studio MintKit",
                }
            ),
            "contact_email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "you@example.com",
                }
            ),
        }
        labels = {
            "business_name": "Business name",
            "contact_email": "Contact email",
            "logo": "Logo (optional)",
        }
        help_texts = {
            "business_name": "This will be shown on your storefront and in emails.",
            "contact_email": "Where MintKit-related messages should be sent.",
            "logo": "Upload a small logo to show on your dashboard and storefront.",
        }
