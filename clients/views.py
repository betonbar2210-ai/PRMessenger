from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from .models import Client


class ClientsListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = "clients/clients_list.html"
    context_object_name = "clients"
    login_url = "admin:login"


class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = "clients/client_detail.html"
    context_object_name = "client"
    login_url = "admin:login"


class ClientCreateView(LoginRequiredMixin, CreateView):
    model = Client
    template_name = "clients/client_form.html"
    fields = "__all__"
    success_url = reverse_lazy("clients:clients_list")
    context_object_name = "client"
    login_url = "admin:login"


class ClientUpdateView(LoginRequiredMixin, UpdateView):
    model = Client
    template_name = "clients/client_form.html"
    fields = "__all__"
    success_url = reverse_lazy("clients:clients_list")
    context_object_name = "client"
    login_url = "admin:login"


class ClientDeleteView(LoginRequiredMixin, DeleteView):
    model = Client
    template_name = "clients/client_confirm_delete.html"
    success_url = reverse_lazy("clients:clients_list")
    context_object_name = "client"
    login_url = "admin:login"
