from django import forms
from django.core.exceptions import ValidationError

from .models import BulkMailing


class BulkMailingForm(forms.ModelForm):
    class Meta:
        model = BulkMailing
        fields = ("start_at", "end_at", "periodicity", "message", "recipients")
        widgets = {
            "start_at": forms.DateTimeInput(
                attrs={"type": "datetime-local", "step": "60"}, format="%Y-%m-%dT%H:%M"
            ),
            "end_at": forms.DateTimeInput(
                attrs={"type": "datetime-local", "step": "60"}, format="%Y-%m-%dT%H:%M"
            ),
            "periodicity": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "recipients": forms.CheckboxSelectMultiple(
                attrs={"class": "form-check-input"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_at = cleaned_data.get("start_at")
        end_at = cleaned_data.get("end_at")
        if start_at and end_at and end_at <= start_at:
            raise ValidationError(
                {"end_at": "Дата окончания должна быть позже даты начала."}
            )
        return cleaned_data

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        if owner is not None and not owner.is_manager:
            from clients.models import Client
            from texts.models import Text

            self.fields["message"].queryset = Text.objects.filter(owner=owner)
            self.fields["recipients"].queryset = Client.objects.filter(owner=owner)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                continue
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} form-control".strip()
