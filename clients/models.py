from django.db import models


class Client(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    comment = models.TextField()

    class Meta:
        ordering = ["name"]
        verbose_name = "client"
        verbose_name_plural = "clients"


    def __str__(self):
        return self.name
