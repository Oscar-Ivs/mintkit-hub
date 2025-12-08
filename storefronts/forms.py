# storefronts/forms.py
from django import forms

from .models import Storefront


class StorefrontForm(forms.ModelForm):
    """
    Form for editing the public storefront text (and optional logo).
    """

    # Same trick as for Profile: remove ClearableFileInput.
    logo = forms.ImageField(
        required=False,
        widget=forms.FileInput(
            attrs={
                "class": "form-control",
            }
        ),
        label="Storefront logo (optional)",
    )

    class Meta:
        model = Storefront
        # Adjust this list if your model has slightly different fields,
        # but keep "logo" in here so the widget override is used.
        fields = [
            "headline",
            "description",
            "contact_details",
            "is_active",
            "logo",
        ]
        widgets = {
            "headline": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. MintKit – create digital cards in seconds",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
            "contact_details": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }
        labels = {
            "headline": "Storefront headline",
            "description": "Description",
            "contact_details": "Contact details",
            "is_active": "Make my storefront public",
            # label for logo is set above on logo=…
        }
        help_texts = {
            "headline": "Shown as the main title on your public storefront.",
            "description": "Appears as the main body text on your storefront page.",
            "contact_details": "These details help customers contact or find you.",
            "is_active": "Tick this when you’re ready for customers to see your page.",
            "logo": "Upload a logo that appears above the preview and on your public page.",
        }
