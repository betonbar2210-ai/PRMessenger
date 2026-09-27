from django.conf import settings
from django.db import models


class Text(models.Model):
    title = models.CharField(
        max_length=100,
        verbose_name="Тема письма",
    )
    text = models.TextField(
        verbose_name="Тело письма",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="texts",
        verbose_name="Владелец",
    )

    class Meta:
        ordering = ["title"]
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"

    def __str__(self):
        return self.title
