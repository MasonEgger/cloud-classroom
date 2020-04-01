from django.db import models
from django.contrib.auth.models import User
from classes.models import Class
from django.conf import settings


class Teacher(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING
    )
    classes = models.ManyToManyField(Class)
    droplet_limit = models.IntegerField()

    def __str__(self):
        return "{0}, {1} - {2}".format(
            self.user.last_name, self.user.first_name, self.user.email
        )

