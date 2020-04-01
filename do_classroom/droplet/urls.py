from django.urls import path
from . import views

app_name = "droplet"

urlpatterns = [
    path("create/<int:class_id>", views.create.as_view(), name="create"),
    path("delete/<int:droplet_id>", views.delete.as_view(), name="delete"),
    path(
        "power-control/<int:droplet_id>/<str:power_option>",
        views.power_control.as_view(),
        name="power_control",
    ),
    path("view", views.view.as_view(), name="view"),
    path("view/<int:droplet_id>", views.view.as_view(), name="view"),
    path(
        "view_class_droplets/<int:class_id>",
        views.view_class_droplets.as_view(),
        name="view_class_droplets",
    ),
]
