from django.contrib import admin
from .models import BulkMailing

@admin.register(BulkMailing)
class BulkMailingAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'start_at', 'end_at', 'text_subject', 'clients_count')
    list_filter = ('status',)
    search_fields = ('text__subject',)
    list_per_page = 25

    @admin.display(description='Тема сообщения')
    def text_subject(self, obj):
        return obj.text.subject if hasattr(obj.text, 'subject') else str(obj.text)

    @admin.display(description='Кол-во получателей')
    def clients_count(self, obj):
        return obj.clients.count()
