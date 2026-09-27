from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from users.apps import UsersConfig
from users.views import (
    ConfirmEmailView,
    EmailConfirmationSentView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
    ProfileUpdateView,
    RegisterView,
    ResendConfirmationView,
    ToggleUserBlockView,
    UserListView,
)

app_name = UsersConfig.name

urlpatterns = [
    path("login/", LoginView.as_view(template_name="users/login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    path("profile/", ProfileUpdateView.as_view(), name="profile"),
    path(
        "confirm-email/<str:token>/",
        ConfirmEmailView.as_view(),
        name="confirm_email",
    ),
    path(
        "email-confirmation-sent/",
        EmailConfirmationSentView.as_view(),
        name="email_confirmation_sent",
    ),
    path(
        "resend-confirmation/",
        ResendConfirmationView.as_view(),
        name="resend_confirmation",
    ),
    path("password-reset/", PasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset/done/",
        PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("users/", UserListView.as_view(), name="user_list"),
    path(
        "users/<int:pk>/block/",
        ToggleUserBlockView.as_view(),
        name="user_toggle_block",
    ),
]
