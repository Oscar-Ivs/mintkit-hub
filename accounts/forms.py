# accounts/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Profile


class CustomUserCreationForm(UserCreationForm):
    """
    Registration form that includes an email field.
    Used by accounts/views.py register() view.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "you@example.com"}),
        help_text="Used for welcome emails and account notifications.",
        label="Email",
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email", "").strip()
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """
    Let a logged-in user edit their business profile.
    The user field is not exposed; it is set automatically in the view.
    """

    # Override the default ClearableFileInput so the "Currently / Clear" UI is not shown.
    logo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control"}),
        label="Profile image (optional)",
    )

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
        }
        help_texts = {
            "business_name": "This will be shown on your storefront and in emails.",
            "contact_email": "Where MintKit-related messages should be sent.",
            "logo": "Upload an image that will be used on your dashboard and in Explore-style listings.",
        }
