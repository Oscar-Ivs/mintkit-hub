# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

from .models import Profile

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Email address is required.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("business_name", "contact_email", "logo")



class ProfileForm(forms.ModelForm):
    """
    Let a logged-in user edit their business profile.
    """

    logo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control"}),
        label="Profile image (optional)",
    )

    class Meta:
        model = Profile
        fields = ["business_name", "contact_email", "logo"]
        widgets = {
            "business_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Beauty Studio MintKit"}),
            "contact_email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "you@example.com"}),
        }
        labels = {
            "business_name": "Business name",
            "contact_email": "Contact email",
        }
        help_texts = {
            "business_name": "This will be shown on your storefront and in emails.",
            "contact_email": "Where MintKit-related messages should be sent.",
            "logo": "Upload an image used on the dashboard and in listings.",
        }

class AccountEmailForm(forms.ModelForm):
    """
    Update the auth user email (shows in Django admin Users).
    """

    class Meta:
        model = User
        fields = ("email",)
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@example.com"}),
        }
        labels = {
            "email": "Account email (login)",
        }

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Email address is required.")

        # Allow keeping the same email; block duplicates for other users
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email