from django.db import models
import string, random


def prefix_generator(size=8):
    return "".join(
        random.choice(string.ascii_lowercase + string.digits)
        for i in range(size)
    )


class Class(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    destroyed_at = models.DateTimeField(null=True, blank=True)
    name = models.CharField(max_length=200)
    droplet_count = models.IntegerField(default=1)
    prefix = models.CharField(max_length=15, default=prefix_generator)

    droplet_image = models.CharField(max_length=50)
    droplet_size = models.CharField(max_length=25)
    droplet_region = models.CharField(max_length=50)
    droplet_student_limit = models.IntegerField(default=1)
    droplet_priv_net = models.BooleanField(default=False)
    droplet_ipv6 = models.BooleanField(default=False)
    droplet_user_data = models.TextField(null=True, blank=True)

    def _is_active(self):
        if not self.destroyed_at:
            return True

    is_active = property(_is_active)

    def __str__(self):
        return self.name
