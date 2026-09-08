from django.views.generic import ListView, DetailView
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from .models import Client


class ClientsListView(ListView):
    model = Client
    template_name = "clients/client_list.html"
    context_object_name = "clients"


class ClientDetailView(DetailView):
    model = Client
    template_name = "clients/client_detail.html"
    context_object_name = "client"


class ClientCreateView(CreateView):
    model = Client
    template_name = "clients/client_form.html"
    fields = "__all__"
    success_url = reverse_lazy("clients:client_list")
    context_object_name = "client"


class ClientUpdateView(UpdateView):
    model = Client
    template_name = "clients/client_form.html"
    fields = "__all__"
    success_url = reverse_lazy("clients:client_list")
    context_object_name = "client"


class ClientDeleteView(DeleteView):
    model = Client
    template_name = "clients/client_confirm_delete.html"
    success_url = reverse_lazy("clients:client_list")
    context_object_name = "client"
