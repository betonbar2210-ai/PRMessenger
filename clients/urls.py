from django.urls import path

from clients.apps import ClientsConfig
from clients.views import ClientsListView, ClientDetailView, ClientUpdateView, ClientCreateView

app_name = ClientsConfig.name

urlpatterns = [
    path("", ClientsListView.as_view(), name="clients_list"),
    path("<int:pk>/", ClientDetailView.as_view(), name="client_detail"),
    path("<int:pk>/update/", ClientUpdateView.as_view(), name="client_update"),
    path("create/", ClientCreateView.as_view(), name="client_create"),
    path("<int:pk>/delete/", ClientDetailView.as_view(), name="client_delete"),
]
