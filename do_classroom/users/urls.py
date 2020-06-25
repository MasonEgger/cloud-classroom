from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    path("view/<int:class_id>", views.view.as_view(), name="view"),
]
