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
        # Keep "logo" here so the custom widget above is used.
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
                    "placeholder": "e.g. MintKit - create digital cards in seconds",
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
            "is_active": "Tick this when you're ready for customers to see your page.",
            "logo": "Upload a logo that appears above the preview and on your public page.",
        }


class StorefrontCardForm(forms.ModelForm):
    """
    Single card inside the inline formset.

    Image URL + buy URL are encouraged but treated as optional,
    so a card can be saved with just a title if needed.
    """

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allow cards with just a title; URLs are optional here.
        self.fields["image_url"].required = False
        self.fields["buy_url"].required = False


StorefrontCardFormSet = inlineformset_factory(
    Storefront,
    StorefrontCard,
    form=StorefrontCardForm,
    extra=3,        # show THREE card slots (Card 1–3) by default
    max_num=3,      # and never more than three
    can_delete=True,
)
