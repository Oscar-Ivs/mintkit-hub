# storefronts/forms.py
from django import forms
from django.forms import inlineformset_factory

from .models import Storefront, StorefrontCard


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


class StorefrontCardForm(forms.ModelForm):
    class Meta:
        model = StorefrontCard
        fields = ["title", "price_label", "image_url", "buy_url", "description"]
        labels = {
            "title": "Card title",
            "price_label": "Price label (optional)",
            "image_url": "Thumbnail image URL",
            "buy_url": "Buy / details link",
            "description": "Short description (optional)",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


StorefrontCardFormSet = inlineformset_factory(
    Storefront,
    StorefrontCard,
    form=StorefrontCardForm,
    extra=3,        # always show up to 3 slots
    max_num=3,
    can_delete=True,
)
