from django.db import models


class Client(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name="Ф. И. О.",
    )
    email = models.EmailField(
        unique=True,
        verbose_name="Email",
    )
    comment = models.TextField(
        blank=True,
        verbose_name="Комментарий",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Получатель рассылки"
        verbose_name_plural = "Получатели рассылки"

    def __str__(self):
        return self.name
