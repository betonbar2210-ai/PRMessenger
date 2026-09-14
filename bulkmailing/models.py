from django.db import models

from texts.models import Text
from clients.models import Client


class BulkMailing(models.Model):
    STATUS_CREATED = "created"
    STATUS_STARTED = "started"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_CREATED, "Создана"),
        (STATUS_STARTED, "Запущена"),
        (STATUS_COMPLETED, "Завершена"),
    ]

    start_at = models.DateTimeField(
        verbose_name="Дата и время первой отправки",
        null=True,
        blank=True,
    )
    end_at = models.DateTimeField(
        verbose_name="Дата и время окончания отправки",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
        verbose_name="Статус",
    )
    message = models.ForeignKey(
        Text,
        on_delete=models.CASCADE,
        related_name="mailings",
        verbose_name="Сообщение",
    )
    recipients = models.ManyToManyField(
        Client,
        related_name="mailings",
        verbose_name="Получатели",
    )

    class Meta:
        verbose_name = "Рассылка"
        verbose_name_plural = "Рассылки"
        ordering = ["-start_at", "status"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["start_at"]),
            models.Index(fields=["end_at"]),
        ]

    def __str__(self):
        return f"{self.message} ({self.status})"


class BulkMailingAttempt(models.Model):
    objects = None
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_SUCCESS, "Успешно"),
        (STATUS_FAILED, "Не успешно"),
    ]

    attempted_at = models.DateTimeField(
        verbose_name="Дата и время попытки",
        auto_now_add=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_FAILED,
        verbose_name="Статус",
    )
    server_response = models.TextField(
        verbose_name="Ответ почтового сервера",
        blank=True,
        help_text="Текст ошибки/ответа от SMTP-сервера (может быть длинным)",
    )
    mailing = models.ForeignKey(
        BulkMailing,
        on_delete=models.CASCADE,
        related_name="attempts",
        verbose_name="Рассылка",
    )

    class Meta:
        verbose_name = "попытка рассылки"
        verbose_name_plural = "попытки рассылок"
        ordering = ["-attempted_at"]
        indexes = [
            models.Index(fields=["mailing", "-attempted_at"]),
            models.Index(fields=["status", "-attempted_at"]),
            models.Index(fields=["attempted_at"]),
        ]

    def __str__(self):
        return f"{self.get_status_display()} — {self.mailing} ({self.attempted_at})"
