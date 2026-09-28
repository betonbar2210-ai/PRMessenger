from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from users.mixins import (
    OwnedObjectMixin,
    OwnerCreateMixin,
    OwnerScopedMixin,
    OwnerWriteMixin,
)

from .forms import TextForm
from .models import Text


class TextsListView(OwnerScopedMixin, ListView):
    model = Text
    template_name = "texts/texts_list.html"
    context_object_name = "texts"
    paginate_by = 25

    def get_queryset(self):
        return super().get_queryset().select_related("owner")


class TextDetailView(OwnedObjectMixin, DetailView):
    model = Text
    template_name = "texts/texts_detail.html"
    context_object_name = "text"


class TextCreateView(OwnerCreateMixin, CreateView):
    model = Text
    form_class = TextForm
    template_name = "texts/texts_form.html"
    success_url = reverse_lazy("texts:texts_list")
    context_object_name = "text"


class TextUpdateView(OwnerWriteMixin, UpdateView):
    model = Text
    form_class = TextForm
    template_name = "texts/texts_form.html"
    success_url = reverse_lazy("texts:texts_list")
    context_object_name = "text"


class TextDeleteView(OwnerWriteMixin, DeleteView):
    model = Text
    template_name = "texts/texts_confirm_delete.html"
    success_url = reverse_lazy("texts:texts_list")
    context_object_name = "text"
