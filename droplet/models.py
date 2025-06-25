from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    pass

# TODO: Replace with async DigitalOcean API client
# import digitalocean
# from digitalocean.baseapi import NotFoundError

from classes.models import Class
from users.models import User

# from droplet.utils.do_utils import mkpasswd


class Droplet(models.Model):
    """Model representing a DigitalOcean droplet managed by the classroom system."""

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="droplets",
        help_text="The user who owns this droplet",
    )
    class_id = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name="droplets",
        help_text="The class this droplet belongs to",
    )
    name = models.CharField(
        max_length=128, blank=True, help_text="The name of the droplet in DigitalOcean"
    )
    droplet_id = models.CharField(
        max_length=64, blank=True, help_text="The DigitalOcean droplet ID"
    )
    region = models.CharField(
        max_length=64,
        blank=True,
        help_text="The DigitalOcean region where the droplet is located",
    )
    image = models.CharField(
        max_length=64,
        blank=True,
        help_text="The DigitalOcean image used for the droplet",
    )
    ip_addr = models.GenericIPAddressField(
        protocol="both",
        unpack_ipv4=False,
        null=True,
        blank=True,
        help_text="The public IP address of the droplet",
    )
    initial_password = models.CharField(
        max_length=512,
        blank=True,
        help_text="The initial password for the droplet user",
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Droplet"
        verbose_name_plural = "Droplets"

    def __str__(self) -> str:
        return self.name or f"Droplet {self.id}"


# TODO: Implement async DigitalOcean droplet management
# These signals will be replaced with proper async operations using Temporal workflows

# @receiver(pre_save, sender=Droplet)
# def droplet_create(sender, instance, using, **kwargs):
#     """Create a DigitalOcean droplet when a Droplet model is saved."""
#     # Implementation will be moved to async service layer
#     pass

# @receiver(post_delete, sender=Droplet)
# def droplet_delete(sender, instance, using, **kwargs):
#     """Delete a DigitalOcean droplet when a Droplet model is deleted."""
#     # Implementation will be moved to async service layer
#     pass


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
