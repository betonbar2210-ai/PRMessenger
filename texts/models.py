from django.db import models


class Text(models.Model):
    title = models.CharField(
        max_length=100,
        verbose_name="Тема письма",
    )
    text = models.TextField(
        verbose_name="Тело письма",
    )

    class Meta:
        ordering = ["title"]
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"

    def __str__(self):
        return self.title
