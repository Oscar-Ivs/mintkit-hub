# subscriptions/forms.py
import re
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
                    "placeholder": "----- ----- ----- ----- -----",
                    "autocomplete": "off",
                    "spellcheck": "false",
                }
            )
        }

    def clean_principal_id(self):
        raw = (self.cleaned_data.get("principal_id") or "").strip().lower()

        # Allow paste with spaces / no hyphens and normalize
        cleaned = re.sub(r"[^a-z0-9]", "", raw)

        if len(cleaned) < 10:
            raise forms.ValidationError("PID looks too short. Paste the full Principal ID from MintKit Studio.")

        # Group into 5-char chunks: abcde-fghij-...
        grouped = "-".join(cleaned[i : i + 5] for i in range(0, len(cleaned), 5))

        # Basic sanity check (letters/numbers + hyphens)
        if not re.fullmatch(r"[a-z0-9-]+", grouped):
            raise forms.ValidationError("PID format looks invalid. Paste the full Principal ID from MintKit Studio.")

        return grouped
