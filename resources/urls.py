from django.urls import path
from . import views

app_name = "resources"

urlpatterns = [path("", views.list_resources.as_view(), name="")]
