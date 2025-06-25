# LEGACY: This utility is deprecated
# Use Django's get_object_or_404(Class, id=class_id) instead

from django.shortcuts import get_object_or_404
from classes.models import Class


def class_exists(class_id):
    """
    DEPRECATED: Use get_object_or_404(Class, id=class_id) instead.
    
    This function returns None if class doesn't exist, which leads to
    inconsistent error handling. Django's get_object_or_404 is preferred.
    """
    try:
        clas = Class.objects.get(id=class_id)
    except Class.DoesNotExist:
        return None

    return clas


# Preferred approach for new code:
def get_class_or_404(class_id):
    """Get a class by ID or raise Http404 if not found."""
    return get_object_or_404(Class, id=class_id)
