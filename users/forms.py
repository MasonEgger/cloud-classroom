from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from users.models import User


class CustomUserCreationForm(UserCreationForm):

    ssh_key = forms.CharField()

    class Meta(UserCreationForm):
        model = User
        fields = ("email", "first_name", "last_name")


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")
