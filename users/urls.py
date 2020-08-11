from django.urls import path
from rest_framework.authtoken import views as authviews
from . import views

app_name = "users"

urlpatterns = [
    path("view/<int:class_id>", views.view.as_view(), name="view"),
    path(
        "obtain-auth-token/",
        authviews.obtain_auth_token,
        name="obtain-auth-token",
    ),
    path("register/", views.register.as_view(), name="register"),
]
