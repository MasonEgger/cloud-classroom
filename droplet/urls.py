from django.urls import path
from . import views

app_name = "droplet"

urlpatterns = [
    path(
        "assign/<int:droplet_id>/<int:user_id>/<int:class_id>",
        views.assign.as_view(),
        name="assign",
    ),
    path("create/<int:class_id>", views.create.as_view(), name="create"),
    path("create/<int:class_id>/<int:count>", views.create.as_view(), name="create",),
    path("delete/<int:droplet_id>", views.delete.as_view(), name="delete"),
    path("delete-all", views.delete_all.as_view(), name="delete_all"),
    path(
        "power-control/<int:droplet_id>/<str:power_option>",
        views.power_control.as_view(),
        name="power_control",
    ),
    path("view", views.view.as_view(), name="view"),
    path("view/<int:droplet_id>", views.view.as_view(), name="view"),
    path(
        "view/class/<int:class_id>",
        views.view_my_class_droplets.as_view(),
        name="view_my_class_droplets",
    ),
    path(
        "view-class-droplets/<int:class_id>",
        views.view_class_droplets.as_view(),
        name="view_class_droplets",
    ),
    path(
        "class-droplet-count/<int:class_id>",
        views.class_droplet_count.as_view(),
        name="class_droplet_count",
    ),
]
