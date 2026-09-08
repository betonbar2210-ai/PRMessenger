from django.db import models


class Text(models.Model):
    title = models.CharField(max_length=100)
    text = models.TextField()

    class Meta:
        ordering = ["title"]
        verbose_name = "text"
        verbose_name_plural = "texts"

    def __str__(self):
        return self.title