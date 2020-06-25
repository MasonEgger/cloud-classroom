from django.conf import settings
from classes.models import Class
from students.models import Student
from teachers.models import Teacher
from droplet.models import Droplet
from users.models import User
from droplet.utils.do_utils import add_droplet, destroy, power_off, power_on
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from multiprocessing import Process


class create(APIView):

    permission_classes = (IsAuthenticated,)

    def get(self, request, class_id, count=1):
        """
        Create a droplet inside a specific class
        """
        params = {}
        request_user = request.user

        user_data = get_user_role(request_user)
        if user_data[0] is False:
            return Response(user_data[1], status=user_data[1]["status"])

        user_data = user_data[1]
        user = user_data["user"]

        if count < 1 or count > 20:
            params[
                "message"
            ] = "Invalid amount for count. Can't be less than 1 or greater than 20"
            params["status"] = 400
            return Response(params, status=params["status"])
        try:
            clas = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            params["message"] = "Invalid class"
            params["status"] = 404
            return Response(params, status=params["status"])

        if clas in user.classes.all():
            droplets = Droplet.objects.filter(owner=user.user)
            if user_data["is_teacher"]:
                if count + len(droplets) > user.droplet_limit:
                    params["status"] = 403
                    params["message"] = "Max number of droplets reached"
                    return Response(params, status=params["status"])
            else:
                if len(droplets) + count > clas.droplet_student_limit:
                    params["status"] = 403
                    params["message"] = "Max number of droplets reached"
                    return Response(params, status=params["status"])

            # params["droplet-id"] = []

            params["droplet_info"] = []
            for i in range(0, count):
                params["droplet_info"].append(
                    add_droplet(settings.DO_TOKEN, clas, user.user)
                )
            clas.droplet_count = clas.droplet_count + count
            clas.save()
            params["message"] = "Droplet(s) created"
            params["status"] = 200
            # params["droplet-id"].append(droplet_id)
        else:
            params["message"] = "User is not in the class"
            params["status"] = 400
        return Response(params, status=params["status"])


class delete(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, droplet_id):
        params = {}
        request_user = request.user
        user_data = get_user_role(request_user)
        if user_data[0] is False:
            return Response(user_data[1], status=user_data[1]["status"])

        user_data = user_data[1]
        user = user_data["user"]

        try:
            droplet = Droplet.objects.get(droplet_id=droplet_id)
        except Droplet.DoesNotExist:
            params["message"] = "Invalid droplet"
            params["status"] = 404
            return Response(params, status=params["status"])
        if user_data["is_teacher"] is True:
            destroy(settings.DO_TOKEN, droplet_id)
            params["message"] = "Teacher deleted Droplet"
            params["status"] = 200
        else:
            droplets = Droplet.objects.filter(owner=user.user)
            if droplet in droplets:
                destroy(settings.DO_TOKEN, droplet_id)
                params["message"] = "Droplet deleted"
                params["status"] = 200
            else:
                params["message"] = "User does not own specified droplet"
                params["status"] = 403
        return Response(params, status=params["status"])


class delete_all(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, class_id=None):
        params = {}
        request_user = request.user
        user_data = get_user_role(request_user)
        if user_data[0] is False:
            return Response(user_data[1], status=user_data[1]["status"])

        user_data = user_data[1]
        user = user_data["user"]

        droplets = Droplet.objects.filter(owner=user.user)

        if len(droplets) == 0:
            params["message"] = "User has no droplets associated with them"
            params["status"] = 200
            return Response(params, status=params["status"])

        for droplet in droplets:
            p = Process(
                target=destroy, args=(settings.DO_TOKEN, droplet.droplet_id),
            )
            p.start()
        p.join()

        params["message"] = "{0} droplets deleted".format(len(droplets))
        params["num_droplets_deleted"] = len(droplets)
        params["status"] = 200

        return Response(params, status=params["status"])


class view(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, droplet_id=None):
        params = {}
        request_user = request.user
        user_data = get_user_role(request_user)
        if user_data[0] is False:
            return Response(user_data[1], status=user_data[1]["status"])

        user_data = user_data[1]
        user = user_data["user"]

        if droplet_id is None:
            droplets = Droplet.objects.filter(owner=user.user)
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
                teacher_classes = Class.objects.filter(teacher=user)
            if user == droplet.owner or (
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
        request_user = request.user
        user_data = get_user_role(request_user)
        if user_data[0] is False:
            return Response(user_data[1], status=user_data[1]["status"])

        user_data = user_data[1]
        user = user_data["user"]
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
        if user != clas.teacher:
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
        request_user = request.user
        user_data = get_user_role(request_user)
        if user_data[0] is False:
            return Response(user_data[1], status=user_data[1]["status"])

        user_data = user_data[1]
        user = user_data["user"]

        try:
            droplet = Droplet.objects.get(droplet_id=droplet_id)
        except Droplet.DoesNotExist:
            params["message"] = "Droplet does not exist"
            params["status"] = 404
            return Response(params, status=params["status"])

        if user_data["is_teacher"] is True:
            teacher_classes = Class.objects.filter(teacher=user)
        if user == droplet.owner or (
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


class assign(APIView):
    """
    Assign a droplet to a user
    """

    permission_classes = (IsAuthenticated,)

    def get(
        self, request, droplet_id, user_id, class_id,
    ):
        params = {}
        request_user = request.user
        user_data = get_user_role(request_user)
        if user_data[0] is False:
            return Response(user_data[1], status=user_data[1]["status"])

        user_data = user_data[1]
        user = user_data["user"]

        if user_data["is_teacher"] is False:
            params["message"] = "Only Teachers can assign resources"
            params["status"] = 403
            return Response(params, status=params["status"])

        try:
            droplet = Droplet.objects.get(droplet_id=droplet_id)
        except Droplet.DoesNotExist:
            params["message"] = "Droplet does not exist"
            params["status"] = 404
            return Response(params, status=params["status"])

        user_is_student = False
        user_is_teacher = False

        student = None
        teacher = None
        try:
            usr = User.objects.get(id=user_id)
        except User.DoesNotExist:
            params["message"] = "Invalid user"
            params["status"] = 400
            return Response(params, status=params["status"])

        try:
            student = Student.objects.get(user=usr)
            user_is_student = True
        except Student.DoesNotExist:
            pass

        try:
            teacher = Teacher.objects.get(user=usr)
            user_is_teacher = True
        except Teacher.DoesNotExist:
            pass

        if user_is_student is False and user_is_teacher is False:
            params["message"] = "Invalid user"
            params["status"] = 404
            return Response(params, status=params["status"])

        try:
            clas = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            params["message"] = "Invalid Class"
            params["status"] = 404
            return Response(params, status=params["status"])

        if clas not in user.classes.all():
            params[
                "message"
            ] = "Only the official class teacher can assign droplets"
            params["status"] = 403
            return Response(params, status=params["status"])

        recipient = None
        if teacher is None:
            recipient = student
        else:
            recipient = teacher

        if clas not in recipient.classes.all():
            params["message"] = "Recipient is not in specified class"
            params["status"] = 400
            return Response(params, status=params["status"])

        droplet.owner = recipient.user
        droplet.save()

        params["message"] = "Droplet successfully reassigned"
        params["status"] = 200
        return Response(params, status=params["status"])


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
    results = {"is_student": False, "is_teacher": False, "user": None}
    student = is_student(user)
    teacher = is_teacher(user)

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

    return (True, results)
