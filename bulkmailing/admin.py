from django.contrib import admin
from .models import BulkMailing, BulkMailingAttempt


@admin.register(BulkMailing)
class BulkMailingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "start_at",
        "end_at",
        "message_title",
        "recipients_count",
    )
    list_filter = ("status",)
    search_fields = ("message__title",)
    list_per_page = 25

    @admin.display(description="Тема сообщения")
    def message_title(self, obj):
        return obj.message.title

    @admin.display(description="Кол-во получателей")
    def recipients_count(self, obj):
        return obj.recipients.count()


@admin.register(BulkMailingAttempt)
class BulkMailingAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "mailing", "attempted_at", "status", "server_response")
    list_filter = ("status",)
    search_fields = ("server_response", "mailing__id")
    list_per_page = 25
