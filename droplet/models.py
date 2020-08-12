from django.db import models

from classes.models import Class
from students.models import Student
from users.models import User
from django.conf import settings
import digitalocean
from digitalocean.baseapi import NotFoundError

from django.db.models.signals import post_delete
from django.dispatch import receiver


class Droplet(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    class_id = models.ForeignKey(Class, on_delete=models.CASCADE)
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

@receiver(post_delete, sender=Droplet)
def droplet_delete(sender, instance, using, **kwargs):
    droplet = digitalocean.Droplet(token=settings.DO_TOKEN, id=instance.droplet_id)
    try:
        droplet.destroy()
    except NotFoundError:
        pass

    instance.class_id.droplet_count = (
        instance.class_id.droplet_count - 1
    )
    instance.class_id.save()