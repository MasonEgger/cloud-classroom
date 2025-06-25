"""Cloud Classroom URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
"""

from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    # Admin interface
    path("admin/", admin.site.urls),
    # Django-allauth authentication URLs
    path("accounts/", include("allauth.urls")),
    # Application URLs
    path("auth/", include("authentication.urls")),
    path("classroom/", include("classroom.urls")),
    # TODO: Fix DRF imports in these apps
    # path("droplets/", include("droplet.urls")),
    # path("classes/", include("classes.urls")),
    # path("resources/", include("resources.urls")),
    # path("users/", include("users.urls")),
    # Home page
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
]

# Add development URLs
if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
        path("__reload__/", include("django_browser_reload.urls")),
        path("silk/", include("silk.urls", namespace="silk")),
    ]

    # Serve media files in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
