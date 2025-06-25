# LEGACY: This URL configuration is for deprecated DRF API endpoints
# These URLs are commented out in do_classroom/urls.py and replaced by HTMX views
from django.urls import path
# from rest_framework.authtoken import views as authviews  # DRF not available

from . import views

app_name = "users"

urlpatterns = [
    path("view/<int:class_id>", views.view.as_view(), name="view"),
    # DRF auth token endpoint - disabled during migration to HTMX
    # path(
    #     "obtain-auth-token/",
    #     authviews.obtain_auth_token,
    #     name="obtain-auth-token",
    # ),
    path("register/", views.register.as_view(), name="register"),
]
