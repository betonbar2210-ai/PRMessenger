import logging

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    PasswordResetCompleteView as BasePasswordResetCompleteView,
    PasswordResetConfirmView as BasePasswordResetConfirmView,
    PasswordResetDoneView as BasePasswordResetDoneView,
    PasswordResetView as BasePasswordResetView,
)
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import View
from django.views.generic.edit import CreateView, UpdateView

from config.settings import LOGIN_URL
from users.forms import UserProfileForm, UserRegistration, VerifiedPasswordResetForm
from users.mixins import ManagerRequiredMixin
from users.models import CustomUser
from users.services import (
    build_confirm_url,
    read_confirm_token,
    send_confirmation_email,
)

logger = logging.getLogger(__name__)


class RegisterView(CreateView):

    form_class = UserRegistration
    template_name = "users/register.html"
    success_url = reverse_lazy("users:email_confirmation_sent")

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.is_active = False
        self.object.is_email_verified = False
        self.object.save()
        form.save_m2m()
        sent = send_confirmation_email(
            self.object, build_confirm_url(self.request, self.object)
        )
        if not sent:
            messages.warning(
                self.request,
                "Письмо с подтверждением отправить не удалось. "
                "Запросите повторную отправку на странице входа.",
            )
        return HttpResponseRedirect(self.get_success_url())


class EmailConfirmationSentView(View):
    template_name = "users/email_confirmation_sent.html"

    def get(self, request):
        return render(request, self.template_name)


class ConfirmEmailView(View):
    template_name = "users/email_confirm.html"

    def get(self, request, token):
        user = read_confirm_token(token)
        if user is None:
            return render(request, self.template_name, {"invalid": True}, status=400)
        if user.is_email_verified:
            return render(request, self.template_name, {"already": True, "user": user})
        user.is_email_verified = True
        user.is_active = True
        user.save(update_fields=["is_email_verified", "is_active"])
        login(request, user, backend="users.backends.EmailBackend")
        messages.success(request, "Email подтверждён. Аккаунт активирован.")
        return redirect("home")


class ResendConfirmationView(View):
    template_name = "users/email_confirmation_sent.html"

    def post(self, request):
        email = (request.POST.get("email") or "").strip()
        user = CustomUser.objects.filter(email__iexact=email).first()
        if user is not None and not user.is_email_verified:
            send_confirmation_email(user, build_confirm_url(request, user))
        # Ответ одинаков независимо от того, существует ли адрес.
        messages.info(
            request, "Если аккаунт требует подтверждения — письмо отправлено."
        )
        return redirect("users:resend_confirmation")

    def get(self, request):
        return render(request, self.template_name)


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = UserProfileForm
    template_name = "users/profile_form.html"
    success_url = reverse_lazy("home")
    login_url = LOGIN_URL

    def get_object(self, queryset=None) -> CustomUser:
        return self.request.user


class PasswordResetView(BasePasswordResetView):
    form_class = VerifiedPasswordResetForm
    template_name = "users/password_reset_form.html"
    email_template_name = "users/password_reset_email.txt"
    success_url = reverse_lazy("users:password_reset_done")
    login_url = LOGIN_URL


class PasswordResetDoneView(BasePasswordResetDoneView):
    template_name = "users/password_reset_done.html"


class PasswordResetConfirmView(BasePasswordResetConfirmView):
    template_name = "users/password_reset_confirm.html"
    success_url = reverse_lazy("users:password_reset_complete")


class PasswordResetCompleteView(BasePasswordResetCompleteView):
    template_name = "users/password_reset_complete.html"


class UserListView(ManagerRequiredMixin, View):

    template_name = "users/user_list.html"
    login_url = LOGIN_URL

    def get(self, request):
        users = CustomUser.objects.annotate(
            clients_count=Count("clients", distinct=True),
            mailings_count=Count("mailings", distinct=True),
        ).order_by("email")
        return render(
            request,
            self.template_name,
            {
                "users": users,
                "can_block": True,
            },
        )


class ToggleUserBlockView(ManagerRequiredMixin, View):

    login_url = LOGIN_URL

    def post(self, request, pk):
        target = get_object_or_404(CustomUser, pk=pk)
        if target == request.user:
            raise PermissionDenied
        # Менеджер не может блокировать суперпользователей.
        if target.is_superuser and not request.user.is_superuser:
            raise PermissionDenied
        if target.is_blocked:
            target.is_blocked = False
            target.blocked_at = None
            messages.info(request, f"Пользователь {target.email} разблокирован.")
        else:
            target.is_blocked = True
            target.blocked_at = timezone.now()
            messages.info(request, f"Пользователь {target.email} заблокирован.")
        target.save(update_fields=["is_blocked", "blocked_at"])
        return redirect("users:user_list")
