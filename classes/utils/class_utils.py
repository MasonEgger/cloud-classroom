from classes.models import Class


def class_exists(class_id):
    # Create a class utility to extract this "Does class exist code"
    try:
        clas = Class.objects.get(id=class_id)
    except Class.DoesNotExist:
        return None

    return clas

