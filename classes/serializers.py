from rest_framework import serializers
from classes.models import Class, prefix_generator


class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = [
            "name",
            "droplet_image",
            "droplet_size",
            "droplet_region",
            "droplet_student_limit",
            "droplet_ipv6",
            "prefix",
            "droplet_user_data",
            "droplet_priv_net",
            "allow_registration",
            "force_teacher_ssh_key",
            # Keep adding optional fields here and in extra_kwargs
        ]
        extra_kwargs = {
            "droplet_student_limit": {"required": False},
            "prefix": {"required": False},
            "droplet_ipv6": {"required": False},
            "droplet_user_data": {"required": False},
            "droplet_priv_net": {"required": False},
            "allow_registration": {"required": False},
            "force_teacher_ssh_key": {"required": False},
        }

