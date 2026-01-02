# subscriptions/forms.py
from django import forms
from .models import MintKitAccess


class MintKitAccessForm(forms.ModelForm):
    """Form to store the MintKit Principal ID (PID) for a profile."""

    class Meta:
        model = MintKitAccess
        fields = ["principal_id"]
        labels = {"principal_id": "MintKit Principal ID (PID)"}
        widgets = {
            "principal_id": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Paste PID from MintKit Studio (top-right)",
                    "autocomplete": "off",
                }
            )
        }
