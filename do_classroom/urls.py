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
from drf_spectacular.views import SpectacularSwaggerView, SpectacularAPIView

from rest_framework import permissions


urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("auth.urls"), name="auth"),
    path("droplets/", include("droplet.urls"), name="droplet"),
    path("classes/", include("classes.urls"), name="classes"),
    path("resources/", include("resources.urls"), name="resources"),
    path("users/", include("users.urls"), name="users"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("", SpectacularSwaggerView.as_view(url_name="schema"), name="docs",),
]
