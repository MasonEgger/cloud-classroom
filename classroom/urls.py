"""
URL configuration for classroom management.
"""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "classroom"

urlpatterns = [
    # Dashboard views
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("teacher/", views.TeacherDashboardView.as_view(), name="teacher_dashboard"),
    path("student/", views.StudentDashboardView.as_view(), name="student_dashboard"),
    
    # Class management
    path("class/<int:class_id>/", views.class_detail_view, name="class_detail"),
    path("resources/", views.class_resources_view, name="class_resources"),
    
    # Droplet management
    path("class/<int:class_id>/create-droplet/", views.CreateDropletView.as_view(), name="create_droplet"),
    path("droplet/<int:droplet_id>/action/", views.DropletActionView.as_view(), name="droplet_action"),
    path("droplet/<int:droplet_id>/connection/", views.droplet_connection_info, name="droplet_connection"),
]