from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from classes.models import Class
from students.models import Student
from teachers.models import Teacher


class get_classes(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        params = {}
        user = request.user
        if request.method == "GET":
            student = _is_student(user)
            teacher = _is_teacher(user)

            if student is not None:
                params["student_classes"] = []
                for c in student.classes.all():
                    params["student_classes"].append(
                        {"class_id": c.id, "class_name": c.name}
                    )
            if teacher is not None:
                params["teacher_classes"] = []
                for c in Class.objects.filter(teacher=teacher):
                    params["teacher_classes"].append(
                        {"class_id": c.id, "class_name": c.name}
                    )

        return Response(params, status=200)


class get_class(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, class_id):
        params = {}
        user = request.user
        try:
            c = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            params["message"] = "Invalid class"
            return Response(params, status=404)

        student = _is_student(user)
        teacher = _is_teacher(user)

        if student is not None and c in student.classes.all():
            params["teacher"] = (
                c.teacher.user.last_name + ", " + c.teacher.user.first_name
            )
            params["name"] = c.name
            params["droplet_image"] = c.droplet_image
            params["droplet_size"] = c.droplet_size
            params["droplet_region"] = c.droplet_region
            params["droplet_limit"] = c.droplet_student_limit
        if teacher is not None and teacher == c.teacher:
            params["created_at"] = c.created_at
            params["prefix"] = c.prefix
            params["priv_net"] = c.droplet_priv_net
            params["ipv6"] = c.droplet_ipv6
            params["user_data"] = c.droplet_user_data

        return Response(params, status=200)


# local helper functions
def _is_student(user):
    try:
        student = Student.objects.get(user=user)
    except Student.DoesNotExist:
        student = None
    return student


def _is_teacher(user):
    try:
        teacher = Teacher.objects.get(user=user)
    except Teacher.DoesNotExist:
        teacher = None
    return teacher
