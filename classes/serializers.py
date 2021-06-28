from rest_framework import serializers
from .models import Class


class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = (
            "id",
            "name",
            "droplet_count",
            "prefix",
            "droplet_image",
            "droplet_size",
            "droplet_region",
            "droplet_student_limit",
            "droplet_ipv6",
            "droplet_user_data",
            "force_teacher_ssh_key",
            "allow_registration",
            "registration_password",
        )
        extra_kwargs = {
            "name": {"required": True},
            "droplet_count": {"required": False},
            "prefix": {"required": False},
            "droplet_image": {"required": True},
            "droplet_size": {"required": True},
            "droplet_region": {"required": True},
            "droplet_student_limit": {"required": False},
            "droplet_ipv6": {"required": False},
            "droplet_user_data": {"required": False},
            "force_teacher_ssh_key": {"required": False},
            "allow_registration": {"required": False},
            "registration_password": {"required": False},
        }

