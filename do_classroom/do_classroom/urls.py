"""do_classroom URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls.static import static
from do_classroom import settings
from django.urls import path, include
from django.views.generic import TemplateView

from rest_framework import permissions


urlpatterns = [
    path("", TemplateView.as_view(template_name="index.html")),
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("auth.urls"), name="auth"),
    path("api/v1/droplets/", include("droplet.urls"), name="droplet"),
    path("api/v1/classes/", include("classes.urls"), name="classes"),
    path("api/v1/resources/", include("resources.urls"), name="resources"),
    path("api/v1/users/", include("users.urls"), name="users"),
    path(
        "api/v1/swagger/", TemplateView.as_view(template_name="index.html")
    ),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
