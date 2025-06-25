from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from users.models import User


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm):
        model = User
        fields = ("email", "first_name", "last_name")


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")
