from django.urls import path


from texts.apps import TextsConfig
from texts.views import TextsListView, TextDetailView, TextCreateView, TextUpdateView, TextDeleteView

app_name = TextsConfig.name

urlpatterns = [
    path("", TextsListView.as_view(), name="texts_list"),
    path("<int:pk>/", TextDetailView.as_view(), name="text_detail"),
    path("create/", TextCreateView.as_view(), name="text_create"),
    path("<int:pk>/update/", TextUpdateView.as_view(), name="text_update"),
    path("<int:pk>/delete/", TextDeleteView.as_view(), name="text_delete"),
]