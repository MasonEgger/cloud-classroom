import time
from django.db import models
from django.conf import settings
import digitalocean
from digitalocean.baseapi import NotFoundError

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from users.models import User
from classes.models import Class
from users.models import Profile
from droplet.utils.do_utils import mkpasswd


class Droplet(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    class_id = models.ForeignKey(Class, on_delete=models.CASCADE)
    name = models.CharField(max_length=128, blank=True)
    droplet_id = models.CharField(max_length=64, blank=True)
    region = models.CharField(max_length=64, blank=True)
    image = models.CharField(max_length=64, blank=True)
    ip_addr = models.GenericIPAddressField(
        protocol="both", unpack_ipv4=False, null=True, blank=True
    )
    initial_password = models.CharField(max_length=512, blank=True)

    def __str__(self):
        return self.name


@receiver(pre_save, sender=Droplet)
def droplet_create(sender, instance, using, **kwargs):
    class_obj = instance.class_id

    user = "sammy"
    expire = True

    pwd = mkpasswd()
    data = cloud_config.format(user, user, pwd, expire)
    name = (
        class_obj.prefix
        + "-"
        + instance.owner.email.replace("@", "-AT-")
        + "-"
        + pwd.split(" ")[0]
    )

    droplet_data = {
        "token": settings.DO_TOKEN,
        "size_slug": class_obj.droplet_size,
        "region": class_obj.droplet_region,
        "name": name,
        "image": class_obj.droplet_image,
        "user_data": data,
        "tags": ["digitalocean_classroom", class_obj.prefix],
    }
    if class_obj.force_teacher_ssh_key is True:
        teachers = class_obj.teacher_set.all()
        ssh_keys = []
        for teacher in teachers:
            try:
                prof = Profile.objects.get(user=teacher.user)
                if prof.ssh_key != "":
                    ssh_keys.append(prof.ssh_key)
            except Profile.DoesNotExist:
                pass
        if len(ssh_keys) > 0:
            droplet_data["ssh_keys"] = ssh_keys

    droplet = digitalocean.Droplet(**droplet_data)
    droplet.create()
    # have to load the droplet to get the IP address
    while droplet.ip_address is None:
        time.sleep(1)
        try:
            droplet.load()
        except digitalocean.DataReadError:
            print("{0} waiting to load".format(droplet.name))

    instance.name = name
    instance.ip_addr = droplet.ip_address
    instance.initial_password = pwd
    instance.droplet_id = droplet.id
    instance.region = class_obj.droplet_region
    instance.image = droplet.image

    instance.class_id.droplet_count = instance.class_id.droplet_count + 1
    instance.class_id.save()


@receiver(post_delete, sender=Droplet)
def droplet_delete(sender, instance, using, **kwargs):
    droplet = digitalocean.Droplet(token=settings.DO_TOKEN, id=instance.droplet_id)
    try:
        droplet.destroy()
    except NotFoundError:
        pass

    instance.class_id.droplet_count = instance.class_id.droplet_count - 1
    instance.class_id.save()


cloud_config = """
#cloud-config
users:
  - name: {}
    groups: sudo
    shell: /bin/bash
    sudo: ['ALL=(ALL:ALL) ALL']
    lock-passwd: false
chpasswd:
  list: |
    {}:{}
  expire: {}
runcmd:
 - passwd -l root
"""
