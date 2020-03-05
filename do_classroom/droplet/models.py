from django.db import models

from classes.models import Class
from students.models import Student


class Droplet(models.Model):
    owner = models.ForeignKey(Student, on_delete=models.DO_NOTHING)
    class_id = models.ForeignKey(Class, on_delete=models.DO_NOTHING)
    droplet_id = models.CharField(max_length=64)
    name = models.CharField(max_length=128)
    region = models.CharField(max_length=64)
    image = models.CharField(max_length=64)
    ip_addr = models.GenericIPAddressField(
        protocol="both", unpack_ipv4=False
    )
    initial_password = models.CharField(max_length=512)

    def __str__(self):
        return self.name

