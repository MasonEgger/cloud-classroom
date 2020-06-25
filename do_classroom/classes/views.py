from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from classes.models import Class
from students.models import Student
from teachers.models import Teacher


class list_classes(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        params = {}
        user = request.user
        if request.method == "GET":
            student, is_in_class = _is_student(user)
            teacher, teaches_class = _is_teacher(user)

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

        student, is_in_class = _is_student(user, c)
        teacher, teaches_class = _is_teacher(user, c)

        if is_in_class is True or teaches_class is True:
            print(c.teacher_set.all())
            params["teacher(s)"] = []
            for teach in c.teacher_set.all():
                params["teacher(s)"].append(
                    teach.user.last_name + ", " + teach.user.first_name
                )
            params["name"] = c.name
            params["droplet_image"] = c.droplet_image
            params["droplet_size"] = c.droplet_size
            params["droplet_region"] = c.droplet_region
            params["droplet_limit"] = c.droplet_student_limit
        if teaches_class is True:
            params["created_at"] = c.created_at
            params["prefix"] = c.prefix
            params["priv_net"] = c.droplet_priv_net
            params["ipv6"] = c.droplet_ipv6
            params["user_data"] = c.droplet_user_data

        return Response(params, status=200)


class create_class(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        params = {}
        x = request.data.get("class_id", None)
        params["test"] = x
        return Response(params, status=200)


# local helper functions
def _is_student(user, class_obj=None):
    is_in_class = None
    try:
        student = Student.objects.get(user=user)
    except Student.DoesNotExist:
        student = None
    else:
        if class_obj in student.classes.all():
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
        if class_obj in teacher.classes.all():
            teaches_class = True
        else:
            teaches_class = False
    return teacher, teaches_class
