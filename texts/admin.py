from django.contrib import admin

from .models import Text


@admin.register(Text)
class TextAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "text")
    search_fields = ("title", "text", "owner__email")
    list_select_related = ("owner",)
    list_per_page = 25
    raw_id_fields = ("owner",)
