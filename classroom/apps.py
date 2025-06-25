"""
Classroom app configuration.
"""

from django.apps import AppConfig


class ClassroomConfig(AppConfig):
    """Configuration for the classroom management app."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "classroom"