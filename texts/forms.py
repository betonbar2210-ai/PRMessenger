from django import forms

from .models import Text


class TextForm(forms.ModelForm):
    class Meta:
        model = Text
        fields = ("title", "text")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})
