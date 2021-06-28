from rest_framework import serializers
from django.contrib.auth import get_user_model

UserModel = get_user_model()


class UserSerializer(serializers.ModelSerializer):

    auth_token = serializers.StringRelatedField(many=False)

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = UserModel.objects.create_user(
            email=validated_data["email"],
            password=password,
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
        )
        user.set_password(password)
        user.save()

        return user

    class Meta:

        model = UserModel
        # Tuple of serialized model fields (see link [2])
        fields = (
            "id",
            "email",
            "password",
            "first_name",
            "last_name",
            "ssh_key",
            "auth_token",
        )
        extra_kwargs = {
            "email": {"required": True},
            "password": {"required": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
            "ssh_key": {"required": False},
            "auth_token": {"required": False},
        }

