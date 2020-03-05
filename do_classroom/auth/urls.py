from django.conf.urls import include, url
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = [
    url(r'check', views.check.as_view()),
]
