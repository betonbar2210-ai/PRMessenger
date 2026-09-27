from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from clients.models import Client
from users.mixins import (
    ManagerRequiredMixin,
    OwnedObjectMixin,
    OwnerCreateMixin,
    OwnerScopedMixin,
    OwnerWriteMixin,
)

from .forms import BulkMailingForm
from .models import BulkMailing, BulkMailingAttempt
from .services import MailingWindowError, send_mailing
from config.settings import LOGIN_URL


def scoped_mailings(user):
    qs = BulkMailing.objects.all()
    if not user.is_manager:
        qs = qs.filter(owner=user)
    return qs


def home_counts(user) -> dict:
    mailings = scoped_mailings(user)
    clients = (
        Client.objects.all() if user.is_manager else Client.objects.filter(owner=user)
    )
    return {
        "total_mailings": mailings.count(),
        "active_mailings": mailings.filter(status=BulkMailing.STATUS_STARTED).count(),
        "unique_clients": clients.values("email").distinct().count(),
    }


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "bulkmailing/home.html"
    login_url = LOGIN_URL

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(home_counts(self.request.user))
        return context


class BulkMailingListView(OwnerScopedMixin, ListView):
    model = BulkMailing
    template_name = "bulkmailing/bulkmailing_list.html"
    context_object_name = "bulkmailings"
    owner_field = "owner"
    paginate_by = 25

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("message", "owner")
            .annotate(recipients_count=Count("recipients"))
        )


class BulkMailingDetailView(OwnedObjectMixin, DetailView):
    model = BulkMailing
    template_name = "bulkmailing/bulkmailing_detail.html"
    context_object_name = "bulkmailing"
    owner_field = "owner"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attempts = BulkMailingAttempt.objects.filter(
            mailing=self.object
        ).select_related("recipient")
        context["attempts"] = attempts
        context["stats"] = self.object.attempts.aggregate(
            success=Count("pk", filter=Q(status=BulkMailingAttempt.STATUS_SUCCESS)),
            failed=Count("pk", filter=Q(status=BulkMailingAttempt.STATUS_FAILED)),
        )
        return context


class BulkMailingCreateView(OwnerCreateMixin, CreateView):
    model = BulkMailing
    form_class = BulkMailingForm
    template_name = "bulkmailing/bulkmailing_form.html"
    success_url = reverse_lazy("bulkmailing:bulkmailing_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user
        return kwargs


class BulkMailingUpdateView(OwnerWriteMixin, UpdateView):
    model = BulkMailing
    form_class = BulkMailingForm
    template_name = "bulkmailing/bulkmailing_form.html"
    success_url = reverse_lazy("bulkmailing:bulkmailing_list")
    owner_field = "owner"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user
        return kwargs


class BulkMailingDeleteView(OwnerWriteMixin, DeleteView):
    model = BulkMailing
    template_name = "bulkmailing/bulkmailing_confirm_delete.html"
    success_url = reverse_lazy("bulkmailing:bulkmailing_list")
    owner_field = "owner"


class BulkMailingSendView(OwnedObjectMixin, View):
    login_url = LOGIN_URL

    def post(self, request, pk):
        queryset = BulkMailing.objects.all()
        if not request.user.is_manager:
            queryset = queryset.filter(owner=request.user)
        mailing = get_object_or_404(queryset, pk=pk)
        if mailing.owner != request.user:
            raise PermissionDenied

        # Кнопка отправляет рассылку независимо от расписания, но забрать её
        # может только один процесс: если планировщик уже отправляет её или
        # рассылка уже ушла/отключена, повторной отправки не будет.
        try:
            outcome = send_mailing(mailing)
        except MailingWindowError as exc:
            # Время вызова обработчика не разрешено — демонстрируем ошибку.
            messages.error(request, "; ".join(exc.messages))
        else:
            if outcome is None:
                messages.warning(
                    request,
                    "Рассылка уже отправляется, уже отправлена или отключена.",
                )
            else:
                success_count, failed_count = outcome
                messages.info(
                    request,
                    f"Отправлено успешно: {success_count}, ошибок: {failed_count}",
                )
        return HttpResponseRedirect(
            reverse("bulkmailing:bulkmailing_detail", args=[mailing.pk])
        )


class BulkMailingToggleDisableView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        mailing = get_object_or_404(BulkMailing, pk=pk)
        if mailing.is_disabled:
            mailing.is_disabled = False
            mailing.disabled_at = None
            text = "Рассылка включена."
        else:
            mailing.is_disabled = True
            mailing.disabled_at = timezone.now()
            text = "Рассылка отключена."
        mailing.save(update_fields=["is_disabled", "disabled_at"])
        messages.info(request, text)
        return HttpResponseRedirect(
            reverse("bulkmailing:bulkmailing_detail", args=[mailing.pk])
        )
