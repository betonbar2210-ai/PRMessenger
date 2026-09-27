from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class CustomUser(AbstractUser):
    ROLE_USER = "user"
    ROLE_MANAGER = "manager"
    ROLE_CHOICES = [
        (ROLE_USER, "Пользователь"),
        (ROLE_MANAGER, "Менеджер"),
    ]

    email = models.EmailField(unique=True)
    phone = PhoneNumberField(blank=True, null=True)
    is_email_verified = models.BooleanField(
        default=False,
        verbose_name="Email подтверждён",
    )
    is_blocked = models.BooleanField(
        default=False,
        verbose_name="Заблокирован",
    )
    blocked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата и время блокировки",
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default=ROLE_USER,
        verbose_name="Роль",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"

    def __str__(self):
        return self.email or self.username

    @property
    def is_manager(self) -> bool:
        return self.is_superuser or self.role == self.ROLE_MANAGER
