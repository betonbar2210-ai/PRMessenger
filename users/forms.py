from django import forms
from django.contrib.auth.forms import PasswordResetForm, UserCreationForm

from users.models import CustomUser


class UserRegistration(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = (
            "email",
            "username",
            "password1",
            "password2",
            "phone",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Email"}
        )
        self.fields["username"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Username"}
        )
        self.fields["password1"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Пароль"}
        )
        self.fields["password2"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Повторите пароль"}
        )
        self.fields["phone"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Телефон"}
        )


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ("email", "username", "phone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ("email", "username", "phone"):
            self.fields[field].widget.attrs.update({"class": "form-control"})
        self.fields["email"].disabled = True
        self.fields["email"].required = False


class VerifiedPasswordResetForm(PasswordResetForm):

    def get_users(self, email):
        return [
            user
            for user in super().get_users(email)
            if user.is_email_verified and not user.is_blocked
        ]
