from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "owner", "comment")
    search_fields = ("name", "email", "comment", "owner__email")
    list_select_related = ("owner",)
    list_per_page = 25
    raw_id_fields = ("owner",)
