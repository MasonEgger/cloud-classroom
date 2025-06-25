from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    pass

# NOTE: Legacy python-digitalocean library imports removed
# Use services.digitalocean.DigitalOceanClient for async API operations

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
    size_slug = models.CharField(
        max_length=64,
        blank=True,
        help_text="The DigitalOcean size slug for the droplet",
    )
    status = models.CharField(
        max_length=32,
        default="new",
        help_text="The current status of the droplet (new, active, off, archive, etc.)",
    )
    destroyed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the droplet was destroyed in DigitalOcean",
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Droplet"
        verbose_name_plural = "Droplets"

    def __str__(self) -> str:
        return self.name or f"Droplet {self.id}"


# NOTE: Droplet lifecycle management is handled by the ClassroomService
# in services/classroom.py using async DigitalOcean API calls


# NOTE: cloud_config template removed - use services.classroom.CloudInitTemplate instead
