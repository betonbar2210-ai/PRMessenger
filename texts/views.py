from django.views.generic import ListView, DetailView
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from .models import Text


class TextsListView(ListView):
    model = Text
    template_name = "texts/texts_list.html"
    context_object_name = "texts"


class TextDetailView(DetailView):
    model = Text
    template_name = "texts/texts_detail.html"
    context_object_name = "text"


class TextCreateView(CreateView):
    model = Text
    template_name = "texts/texts_form.html"
    fields = ["title", "text"]
    success_url = reverse_lazy("texts:texts_list")
    context_object_name = "text"


class TextUpdateView(UpdateView):
    model = Text
    template_name = "texts/texts_form.html"
    fields = ["title", "text"]
    success_url = reverse_lazy("texts:texts_list")
    context_object_name = "text"


class TextDeleteView(DeleteView):
    model = Text
    template_name = "texts/texts_confirm_delete.html"
    success_url = reverse_lazy("texts:texts_list")
    context_object_name = "text"
