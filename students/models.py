from django.db import models
from django.contrib.auth.models import User
from classes.models import Class
from django.conf import settings


class Student(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    classes = models.ManyToManyField(Class)

    def __str__(self):
        return "{0}, {1}".format(self.user.last_name, self.user.first_name)
