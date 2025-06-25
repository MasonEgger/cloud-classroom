from django.conf import settings
from django.db import models

from classes.models import Class


class Teacher(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    classes = models.ManyToManyField(Class)
    droplet_limit = models.IntegerField()

    def __str__(self):
        return f"{self.user.last_name}, {self.user.first_name} - {self.user.email}"
