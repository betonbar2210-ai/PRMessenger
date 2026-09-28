from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from users.mixins import (
    OwnedObjectMixin,
    OwnerCreateMixin,
    OwnerScopedMixin,
    OwnerWriteMixin,
)

from .forms import ClientForm
from .models import Client


class ClientsListView(OwnerScopedMixin, ListView):
    model = Client
    template_name = "clients/clients_list.html"
    context_object_name = "clients"
    paginate_by = 25

    def get_queryset(self):
        return super().get_queryset().select_related("owner")


class ClientDetailView(OwnedObjectMixin, DetailView):
    model = Client
    template_name = "clients/client_detail.html"
    context_object_name = "client"


class ClientCreateView(OwnerCreateMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = "clients/client_form.html"
    success_url = reverse_lazy("clients:clients_list")
    context_object_name = "client"


class ClientUpdateView(OwnerWriteMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = "clients/client_form.html"
    success_url = reverse_lazy("clients:clients_list")
    context_object_name = "client"


class ClientDeleteView(OwnerWriteMixin, DeleteView):
    model = Client
    template_name = "clients/client_confirm_delete.html"
    success_url = reverse_lazy("clients:clients_list")
    context_object_name = "client"
