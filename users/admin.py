from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from users.models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "username",
        "role",
        "is_email_verified",
        "is_blocked",
        "is_active",
    )
    list_filter = ("role", "is_email_verified", "is_blocked", "is_active", "is_staff")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("email",)
    readonly_fields = ("last_login", "date_joined", "blocked_at")
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Личные данные", {"fields": ("first_name", "last_name", "phone")}),
        (
            "Права доступа",
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_blocked",
                    "blocked_at",
                    "is_email_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Важные даты", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2"),
            },
        ),
    )
