from django.views.generic import ListView, DetailView
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from .models import BulkMailing


class BulkMailingListView(ListView):
    model = BulkMailing
    template_name = "bulkmailing/bulkmailing_list.html"
    context_object_name = "bulkmailings"


class BulkMailingDetailView(DetailView):
    model = BulkMailing
    template_name = "bulkmailing/bulkmailing_detail.html"


class BulkMailingCreateView(CreateView):
    model = BulkMailing
    template_name = "bulkmailing/bulkmailing_form.html"
    fields = "__all__"
    success_url = reverse_lazy("bulkmailing:bulkmailing_list")


class BulkMailingUpdateView(UpdateView):
    model = BulkMailing
    template_name = "bulkmailing/bulkmailing_form.html"
    fields = "__all__"
    success_url = reverse_lazy("bulkmailing:bulkmailing_list")


class BulkMailingDeleteView(DeleteView):
    model = BulkMailing
    template_name = "bulkmailing/bulkmailing_confirm_delete.html"
    success_url = reverse_lazy("bulkmailing:bulkmailing_list")
