from django.contrib import admin
from .models import Text


@admin.register(Text)
class TextAdmin(admin.ModelAdmin):
    list_display = ["title", "text"]
    search_fields = ["title", "text"]
    list_filter = ["title"]
