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
            "prefix",
            # Keep adding optional fields here and in extra_kwargs
        ]
        extra_kwargs = {
            "droplet_student_limit": {"required": False},
            "prefix": {"required": False},
        }

