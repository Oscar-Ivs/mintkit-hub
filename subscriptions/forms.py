# subscriptions/forms.py
import re
from urllib.parse import urlparse

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

    def clean_principal_id(self):
        raw = (self.cleaned_data.get("principal_id") or "").strip()

        # If someone pastes a URL, try to extract the first hostname label
        if raw.lower().startswith("http"):
            try:
                host = urlparse(raw).hostname or ""
                if host:
                    raw = host.split(".")[0]
            except Exception:
                pass

        pid = raw.strip().lower().replace(" ", "")

        if len(pid) < 5:
            raise forms.ValidationError("PID looks too short. Paste the full Principal ID from MintKit Studio.")

        if not re.fullmatch(r"[a-z0-9-]+", pid):
            raise forms.ValidationError("PID contains invalid characters. Use only letters, numbers, and hyphens.")

        if "-" not in pid:
            raise forms.ValidationError("PID format looks wrong. It usually contains hyphens (e.g. abcde-fghij-...).")

        return pid
