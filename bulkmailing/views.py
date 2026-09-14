from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, TemplateView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from clients.models import Client
from bulkmailing.models import BulkMailing, BulkMailingAttempt
from bulkmailing.services import send_due_mailings

LOGIN_URL = "admin:login"


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "bulkmailing/home.html"
    login_url = LOGIN_URL

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        send_due_mailings()
        context["total_mailings"] = BulkMailing.objects.count()
        context["active_mailings"] = BulkMailing.objects.filter(
            status=BulkMailing.STATUS_STARTED
        ).count()
        context["unique_clients"] = Client.objects.values("email").distinct().count()
        return context


class BulkMailingForm(forms.ModelForm):
    class Meta:
        model = BulkMailing
        fields = "__all__"
        widgets = {
            "start_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "end_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "recipients": forms.CheckboxSelectMultiple(
                attrs={"class": "form-check-input"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                continue
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} form-control".strip()


class BulkMailingListView(LoginRequiredMixin, ListView):
    model = BulkMailing
    template_name = "bulkmailing/bulkmailing_list.html"
    context_object_name = "bulkmailings"
    login_url = LOGIN_URL

    def get_queryset(self):
        send_due_mailings()
        return super().get_queryset()


class BulkMailingDetailView(LoginRequiredMixin, DetailView):
    model = BulkMailing
    template_name = "bulkmailing/bulkmailing_detail.html"
    context_object_name = "bulkmailing"
    login_url = LOGIN_URL

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        send_due_mailings()
        self.object.refresh_from_db()
        context["attempts"] = self.object.attempts.select_related("mailing")
        return context


class BulkMailingCreateView(LoginRequiredMixin, CreateView):
    model = BulkMailing
    form_class = BulkMailingForm
    template_name = "bulkmailing/bulkmailing_form.html"
    success_url = reverse_lazy("bulkmailing:bulkmailing_list")
    login_url = LOGIN_URL


class BulkMailingUpdateView(LoginRequiredMixin, UpdateView):
    model = BulkMailing
    form_class = BulkMailingForm
    template_name = "bulkmailing/bulkmailing_form.html"
    success_url = reverse_lazy("bulkmailing:bulkmailing_list")
    login_url = LOGIN_URL


class BulkMailingDeleteView(LoginRequiredMixin, DeleteView):
    model = BulkMailing
    template_name = "bulkmailing/bulkmailing_confirm_delete.html"
    success_url = reverse_lazy("bulkmailing:bulkmailing_list")
    login_url = LOGIN_URL


class BulkMailingSendView(LoginRequiredMixin, View):
    login_url = LOGIN_URL

    def post(self, request, pk):
        mailing = get_object_or_404(BulkMailing, pk=pk)
        success_count, failed_count = send_mailing(mailing)
        messages.info(
            request,
            f"Отправлено успешно: {success_count}, ошибок: {failed_count}",
        )
        return HttpResponseRedirect(
            reverse("bulkmailing:bulkmailing_detail", args=[mailing.pk])
        )
