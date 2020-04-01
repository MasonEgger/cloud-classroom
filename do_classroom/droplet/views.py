from django.conf import settings
from classes.models import Class
from students.models import Student
from teachers.models import Teacher
from droplet.models import Droplet
from droplet.utils.do_utils import add_droplet, destroy, power_off, power_on
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class InvaildUserError(Exception):
    """Raised when a user is invalid"""

    pass


def is_student(user):
    try:
        student = Student.objects.get(user=user)
    except Student.DoesNotExist:
        student = None
    return student


def is_teacher(user):
    try:
        teacher = Teacher.objects.get(user=user)
    except Teacher.DoesNotExist:
        teacher = None
    return teacher


def get_user_role(user):
    results = {"is_student": False, "is_teacher": False, "user": None}
    student = is_student(user)
    teacher = is_teacher(user)

    if student is None and teacher is None:
        raise InvaildUserError

    if teacher is not None:
        results["user"] = teacher
        results["is_teacher"] = True
    elif teacher is not None and student is not None:
        results["user"] = teacher
        results["is_student"] = True
    else:
        results["user"] = student
        results["is_student"] = True

    return results


class create(APIView):
    """
    Create a droplet
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, class_id):
        params = {}
        user = request.user
        try:
            results = get_user_role(user)
        except InvaildUserError:
            params["message"] = "Invalid User"
            params["status"] = 404
            return Response(params, status=params["status"])
        request_user = results["user"]

        try:
            clas = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            params["message"] = "Invalid class"
            params["status"] = 404
            return Response(params, status=params["status"])

        if clas in request_user.classes.all():
            droplets = Droplet.objects.filter(owner=request_user.user)
            if len(droplets) >= clas.droplet_student_limit:
                params["status"] = 403
                params["message"] = "Max number of droplets reached"
            else:
                droplet_id = add_droplet(
                    settings.DO_TOKEN, clas, request_user.user
                )
                params["message"] = "Droplet created"
                params["status"] = 200
                params["droplet-id"] = droplet_id
        else:
            params["message"] = "User is not in the class"
            params["status"] = 400
        return Response(params, status=params["status"])


class delete(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, droplet_id):
        params = {}
        user = request.user
        try:
            results = get_user_role(user)
        except InvaildUserError:
            params["message"] = "Invalid User"
            params["status"] = 404
            return Response(params, status=params["status"])
        request_user = results["user"]

        try:
            droplet = Droplet.objects.get(droplet_id=droplet_id)
        except Droplet.DoesNotExist:
            params["message"] = "Invalid droplet"
            params["status"] = 404
            return Response(params, status=params["status"])
        if results["is_teacher"] is True:
            destroy(settings.DO_TOKEN, droplet_id)
            params["message"] = "Teacher deleted Droplet"
            params["status"] = 200
        else:
            droplets = Droplet.objects.filter(owner=request_user.user)
            if droplet in droplets:
                destroy(settings.DO_TOKEN, droplet_id)
                params["message"] = "Droplet deleted"
                params["status"] = 200
            else:
                params["message"] = "User does not own specified droplet"
                params["status"] = 403
        return Response(params, status=params["status"])


class view(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, droplet_id=None):
        params = {}
        user = request.user
        try:
            user_data = get_user_role(user)
        except InvaildUserError:
            params["message"] = "Invalid User"
            params["status"] = 404
            return Response(params, status=params["status"])
        request_user = user_data["user"]

        if droplet_id is None:
            droplets = Droplet.objects.filter(owner=request_user.user)
            params["droplets"] = []
            params["droplet_count"] = len(droplets)
            for droplet in droplets:
                params["droplets"].append(
                    {
                        "name": droplet.name,
                        "owner": str(droplet.owner),
                        "owner_email": droplet.owner.email,
                        "owner_id": droplet.owner.id,
                        "initial_password": droplet.initial_password,
                        "ip_addr": droplet.ip_addr,
                        "class": str(droplet.class_id),
                        "class_id": droplet.class_id.id,
                        "droplet_id": droplet.droplet_id,
                    }
                )
            params["status"] = 200
        else:
            try:
                droplet = Droplet.objects.get(droplet_id=droplet_id)
            except Droplet.DoesNotExist:
                params["message"] = "Droplet does not exist"
                params["status"] = 404
                return Response(params, status=params["status"])
            if user_data["is_teacher"] is True:
                teacher_classes = Class.objects.filter(teacher=request_user)
            if request_user == droplet.owner or (
                user_data["is_teacher"] is True
                and droplet.class_id in teacher_classes
            ):
                params["droplet"] = {
                    "name": droplet.name,
                    "owner": str(droplet.owner),
                    "owner_email": droplet.owner.email,
                    "owner_id": droplet.owner.id,
                    "initial_password": droplet.initial_password,
                    "ip_addr": droplet.ip_addr,
                    "class": str(droplet.class_id),
                    "class_id": droplet.class_id.id,
                    "droplet_id": droplet.droplet_id,
                }
                params["status"] = 200
            else:
                params[
                    "message"
                ] = "User doesn't have permission to view droplet"
                params["status"] = 403

        return Response(params, status=params["status"])


class view_class_droplets(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, class_id):
        params = {}
        user = request.user
        try:
            user_data = get_user_role(user)
        except InvaildUserError:
            params["message"] = "Invalid User"
            params["status"] = 404
            return Response(params, status=params["status"])
        request_user = user_data["user"]
        if user_data["is_teacher"] is not True:
            params["message"] = "Only teachers can view class droplets"
            params["status"] = 403
            return Response(params, status=params["status"])
        try:
            clas = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            params["message"] = "Invalid class"
            params["status"] = 404
            return Response(params, status=params["status"])
        if request_user != clas.teacher:
            params[
                "message"
            ] = "Only official class teachers can view class droplets"
            params["status"] = 403
            return Response(params, status=params["status"])

        droplets = Droplet.objects.filter(class_id=clas)
        params["droplets"] = []
        for droplet in droplets:
            params["droplets"].append(
                {
                    "name": droplet.name,
                    "owner": str(droplet.owner),
                    "owner_email": droplet.owner.email,
                    "owner_id": droplet.owner.id,
                    "initial_password": droplet.initial_password,
                    "ip_addr": droplet.ip_addr,
                    "class": str(droplet.class_id),
                    "class_id": droplet.class_id.id,
                    "droplet_id": droplet.droplet_id,
                }
            )

        return Response(params, status=params["status"])


class power_control(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, droplet_id, power_option):
        options = ["power-off", "power-on"]
        params = {}
        if power_option.lower() not in options:
            params[
                "message"
            ] = "Incorrect power option. Options are power-on and power-off"
            params["status"] = 400
            return Response(params, status=params["status"])
        user = request.user
        try:
            user_data = get_user_role(user)
        except InvaildUserError:
            params["message"] = "Invalid User"
            params["status"] = 404
            return Response(params, status=params["status"])
        request_user = user_data["user"]
        try:
            droplet = Droplet.objects.get(droplet_id=droplet_id)
        except Droplet.DoesNotExist:
            params["message"] = "Droplet does not exist"
            params["status"] = 404
            return Response(params, status=params["status"])

        if user_data["is_teacher"] is True:
            teacher_classes = Class.objects.filter(teacher=request_user)
        if request_user == droplet.owner or (
            user_data["is_teacher"] is True
            and droplet.class_id in teacher_classes
        ):
            if power_option == "power-off":
                power_off(settings.DO_TOKEN, droplet_id)
                params["message"] = "Droplet powered off"
                params["status"] = 200
            else:
                power_on(settings.DO_TOKEN, droplet_id)
                params["message"] = "Droplet powered on"
                params["status"] = 200
        else:
            params["message"] = "User does not own droplet"
            params["status"] = 403
        return Response(params)
