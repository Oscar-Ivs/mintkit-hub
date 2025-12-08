# storefronts/forms.py
from django import forms
from .models import Storefront


class StorefrontForm(forms.ModelForm):
    """
    Form used by business owners to edit their storefront.
    We intentionally do NOT expose 'profile' or 'slug' here:
    - 'profile' is set from the logged-in user's Profile in the view
    - 'slug' is auto-generated from the business name / headline in the model
    """

    class Meta:
        model = Storefront
        # Fields that the user can edit via the dashboard
        fields = [
            "logo",             # dedicated storefront logo
            "headline",         # short title at the top of the page
            "description",      # longer description text
            "contact_details",  # how customers reach the business
            "is_active",        # whether the storefront is publicly visible
        ]
        widgets = {
            "headline": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Beauty Studio MintKit",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe your services, style, and anything customers should know.",
                }
            ),
            "contact_details": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Phone, email, social links, opening hours...",
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
        }
        help_texts = {
            "headline": "Shown as the main title of your storefront.",
            "description": "This appears as the main body text on your storefront page.",
            "contact_details": "These details help customers contact or find you.",
            "is_active": "Tick this when you’re ready for customers to see your page.",
        }
