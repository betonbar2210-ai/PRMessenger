from django.db import models

from texts.models import Text
from clients.models import Client


class BulkMailing(models.Model):
    STATUS_CHOICES = [
        ('created', 'Создана'),
        ('started', 'Запущена'),
        ('completed', 'Завершена'),
    ]

    start_at = models.DateTimeField(
        verbose_name='Дата и время первой отправки',
        null=True,
        blank=True,
    )
    end_at = models.DateTimeField(
        verbose_name='Дата и время окончания отправки',
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='created',
        verbose_name='Статус',
    )
    message = models.ForeignKey(
        'Text',
        on_delete=models.CASCADE,
        related_name='mailings',
        verbose_name='Сообщение',
    )
    recipients = models.ManyToManyField(
        'Client',
        related_name='получатель',
        verbose_name='получатели',
    )

    class Meta:
        verbose_name = 'рассылка'
        verbose_name_plural = 'рассылки'
        ordering = ['-start_at', 'status']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['start_at']),
            models.Index(fields=['end_at']),
        ]

    def __str__(self):
        return f'{self.message} ({self.status})'


class BulkMailingAttempt(models.Model):
    STATUS_CHOICES = [
        ('success', 'Успешно'),
        ('failed', 'Не успешно'),
    ]

    attempted_at = models.DateTimeField(
        verbose_name='Дата и время попытки',
        auto_now_add=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='failed',
        verbose_name='Статус',
    )
    server_response = models.TextField(
        verbose_name='Ответ почтового сервера',
        blank=True,
        help_text='Текст ошибки/ответа от SMTP-сервера (может быть длинным)',
    )
    mailing = models.ForeignKey(
        BulkMailing,
        on_delete=models.CASCADE,
        related_name='attempts',
        verbose_name='Рассылка',
    )

    class Meta:
        verbose_name = 'попытка рассылки'
        verbose_name_plural = 'попытки рассылок'
        ordering = ['-attempted_at']
        indexes = [
            models.Index(fields=['mailing', '-attempted_at']),
            models.Index(fields=['status', '-attempted_at']),
            models.Index(fields=['attempted_at']),
        ]


    def __str__(self):
        return f'{self.get_status_display()} — {self.mailing} ({self.attempted_at})'
