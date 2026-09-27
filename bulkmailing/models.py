from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from texts.models import Text
from clients.models import Client


class BulkMailing(models.Model):
    STATUS_CREATED = "created"
    STATUS_STARTED = "started"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = [
        (STATUS_CREATED, _("Создана")),
        (STATUS_STARTED, _("Запущена")),
        (STATUS_COMPLETED, _("Завершена")),
    ]

    start_at = models.DateTimeField(
        verbose_name=_("Дата и время первой отправки"),
        null=True,
        blank=True,
    )
    end_at = models.DateTimeField(
        verbose_name=_("Дата и время окончания отправки"),
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
        verbose_name=_("Статус"),
    )
    message = models.ForeignKey(
        Text,
        on_delete=models.CASCADE,
        related_name="mailings",
        verbose_name=_("Сообщение"),
    )
    recipients = models.ManyToManyField(
        Client,
        related_name="mailings",
        verbose_name=_("Получатели"),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mailings",
        verbose_name=_("Владелец"),
    )
    is_disabled = models.BooleanField(
        default=False,
        verbose_name=_("Отключена менеджером"),
    )
    disabled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Дата и время отключения"),
    )

    class Meta:
        verbose_name = _("Рассылка")
        verbose_name_plural = _("Рассылки")
        ordering = ["-start_at", "status"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["start_at"]),
            models.Index(fields=["end_at"]),
            models.Index(fields=["owner", "status"]),
        ]

    def __str__(self):
        return f"{self.message} ({self.get_status_display()})"


class BulkMailingAttempt(models.Model):
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_SUCCESS, _("Успешно")),
        (STATUS_FAILED, _("Не успешно")),
    ]

    attempted_at = models.DateTimeField(
        verbose_name=_("Дата и время попытки"),
        auto_now_add=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_FAILED,
        verbose_name=_("Статус"),
    )
    server_response = models.TextField(
        verbose_name=_("Ответ почтового сервера"),
        blank=True,
        help_text=_("Текст ошибки/ответа от SMTP-сервера (может быть длинным)"),
    )
    error_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_("Код ошибки SMTP"),
    )
    mailing = models.ForeignKey(
        BulkMailing,
        on_delete=models.CASCADE,
        related_name="attempts",
        verbose_name=_("Рассылка"),
    )
    recipient = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="mailing_attempts",
        verbose_name=_("Получатель"),
    )

    class Meta:
        verbose_name = _("Попытка рассылки")
        verbose_name_plural = _("Попытки рассылок")
        ordering = ["-attempted_at"]
        indexes = [
            models.Index(fields=["mailing", "-attempted_at"]),
            models.Index(fields=["status", "-attempted_at"]),
            models.Index(fields=["attempted_at"]),
        ]

    def __str__(self):
        return f"{self.get_status_display()} — {self.mailing} ({self.attempted_at})"
