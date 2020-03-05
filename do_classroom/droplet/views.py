from django.conf import settings
from classes.models import Class
from students.models import Student
from teachers.models import Teacher
from droplet.models import Droplet
from droplet.utils.do_utils import add_droplet, destroy
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


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


class create(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, class_id):
        params = {}
        user = request.user
        student = is_student(user)

        try:
            clas = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            params["message"] = "Invalid class"
            return Response(params, status=404)

        if clas in student.classes.all():
            droplets = Droplet.objects.filter(owner=student)
            if len(droplets) >= clas.droplet_student_limit:
                params["status"] = 403
                params["message"] = "Max number of droplets reached"
            else:
                add_droplet(settings.DO_TOKEN, clas, student)
                params["message"] = "Droplet created"
                params["status"] = 200
        else:
            params["message"] = "Student is not in class"
            params["status"] = 400
        return Response(params)


class delete(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, droplet_id):
        params = {}
        user = request.user
        student = is_student(user)
        droplet = Droplet.objects.get(droplet_id=droplet_id)
        droplets = Droplet.objects.filter(owner=student)
        if droplet in droplets:
            destroy(settings.DO_TOKEN, droplet_id)
            params["message"] = "Droplet deleted"
            params["status"] = 200
        else:
            params["message"] = "User does not own specified droplet"
            params["status"] = 403
        return Response(params)


class view(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, droplet_id=None):
        params = {}
        user = request.user
        student = is_student(user)
        teacher = is_teacher(user)
        if student is None and teacher is None:
            params["message"] = "User is not a student nor teacher"
            params["status"] = 403
        elif droplet_id is None:
            droplets = Droplet.objects.filter(owner=student)
            params["droplets"] = []
            params["droplet_count"] = len(droplets)
            for droplet in droplets:
                params["droplets"].append(
                    {
                        "name": droplet.name,
                        "owner": str(droplet.owner),
                        "owner_email": droplet.owner.user.email,
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
            teacher_classes = Class.objects.filter(teacher=teacher)
            if (
                student == droplet.owner
                or droplet.class_id in teacher_classes
            ):
                params["droplet"] = {
                    "name": droplet.name,
                    "owner": str(droplet.owner),
                    "owner_email": droplet.owner.user.email,
                    "owner_id": droplet.owner.id,
                    "initial_password": droplet.initial_password,
                    "ip_addr": droplet.ip_addr,
                    "class": str(droplet.class_id),
                    "class_id": droplet.class_id.id,
                    "droplet_id": droplet.droplet_id,
                }
                params["status"] = 200

        return Response(params)


class view_class_droplets(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, class_id):
        params = {}
        user = request.user
        teacher = is_teacher(user)
        try:
            clas = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            params["message"] = "Invalid class"
            params["status"] = 404
            return Response(params, status=params["status"])
        if teacher is None or teacher != clas.teacher:
            params[
                "message"
            ] = "Only the class teacher can view class droplets"
            params["status"] = 403
            return Response(params, status=params["status"])

        droplets = Droplet.objects.filter(class_id=clas)
        params["droplets"] = []
        for droplet in droplets:
            params["droplets"].append(
                {
                    "name": droplet.name,
                    "owner": str(droplet.owner),
                    "owner_email": droplet.owner.user.email,
                    "owner_id": droplet.owner.id,
                    "initial_password": droplet.initial_password,
                    "ip_addr": droplet.ip_addr,
                    "class": str(droplet.class_id),
                    "class_id": droplet.class_id.id,
                    "droplet_id": droplet.droplet_id,
                }
            )

        return Response(params, status=params.get("status", 200))
