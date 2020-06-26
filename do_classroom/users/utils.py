from students.models import Student
from teachers.models import Teacher


def _is_student(user, class_obj=None):
    is_in_class = None
    try:
        student = Student.objects.get(user=user)
    except Student.DoesNotExist:
        student = None
    else:
        if class_obj is not None and class_obj in student.classes.all():
            is_in_class = True
        else:
            is_in_class = False

    return student, is_in_class


def _is_teacher(user, class_obj=None):
    teaches_class = None
    try:
        teacher = Teacher.objects.get(user=user)
    except Teacher.DoesNotExist:
        teacher = None
    else:
        print(class_obj)
        print(teacher.classes.all())
        if class_obj is not None and class_obj in teacher.classes.all():
            teaches_class = True
        else:
            teaches_class = False
    return teacher, teaches_class


def get_user_role(user, class_id=None):
    """
    Determine if the user is a valid student or teacher. Teacher takes a
    higher precedence so if the account is both it will return the teacher
    instance of the user.

    If the account is invalid this function returns a tuple of (False, dict)
    where the dict contains the necessary HTTP messaging.

    If the account is a valid teacher/student this fuction returns a tuple of
    (True, dict), where the dict returns the user object as well as boolean
    attributes describing if the user `is_teacher` and `is_student`.
    """
    results = {
        "is_student": False,
        "is_teacher": False,
        "user": None,
        "teaches_class": False,
        "is_in_class": False,
    }
    student, is_in_class = _is_student(user, class_id)
    teacher, teaches_class = _is_teacher(user, class_id)

    if student is None and teacher is None:
        return (False, {"message": "Invalid User", "status": 404})

    if teacher is not None:
        results["user"] = teacher
        results["is_teacher"] = True
        if student is not None:

            results["is_student"] = True
    else:
        results["user"] = student
        results["is_student"] = True

    results["is_in_class"] = is_in_class
    results["teaches_class"] = teaches_class

    return (True, results)
