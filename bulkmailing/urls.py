from django.urls import path

from bulkmailing.apps import BulkmailingConfig
from bulkmailing.views import (
    BulkMailingListView,
    BulkMailingDetailView,
    BulkMailingCreateView,
    BulkMailingUpdateView,
    BulkMailingDeleteView,
    BulkMailingSendView,
)

app_name = BulkmailingConfig.name

urlpatterns = [
    path("", BulkMailingListView.as_view(), name="bulkmailing_list"),
    path("create/", BulkMailingCreateView.as_view(), name="bulkmailing_create"),
    path("<int:pk>/", BulkMailingDetailView.as_view(), name="bulkmailing_detail"),
    path(
        "<int:pk>/update/",
        BulkMailingUpdateView.as_view(),
        name="bulkmailing_update",
    ),
    path(
        "<int:pk>/delete/",
        BulkMailingDeleteView.as_view(),
        name="bulkmailing_delete",
    ),
    path(
        "<int:pk>/send/",
        BulkMailingSendView.as_view(),
        name="bulkmailing_send",
    ),
]
