from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from droplet.views import get_user_role
from students.models import Student
from classes.models import Class
from droplet.models import Droplet
from users.models import User
from django.db.utils import IntegrityError
from rest_framework.authtoken.models import Token

# Create your views here.


class view(APIView):
    """
    Create a droplet
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, class_id):
        params = {}
        request_user = request.user

        user_data = get_user_role(request_user)
        if user_data[0] is False:
            return Response(user_data[1], status=user_data[1]["status"])

        user_data = user_data[1]
        user = user_data["user"]
        if user_data["is_teacher"] is False:
            params["message"] = "Non teachers cannot view users"
            params["status"] = 403
            return Response(params, status=params["status"])

        try:
            clas = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            params["message"] = "Invalid class"
            params["status"] = 404
            return Response(params, status=params["status"])

        if clas in user.classes.all():
            params["students"] = []
            students = Student.objects.filter(classes=clas)
            for student in students:
                droplet_count = Droplet.objects.filter(
                    owner=student.user
                ).filter(class_id=class_id)
                student_data = {
                    "first_name": student.user.first_name,
                    "last_name": student.user.last_name,
                    "droplet_count_for_class": len(droplet_count),
                    "email": student.user.email,
                    "student_id": student.id,
                    "user_id": 3,
                }
                params["students"].append(student_data)
            params["status"] = 200
        else:
            params["message"] = "Teacher is not in the class"
            params["status"] = 400
        return Response(params, status=params["status"])


class register(APIView):
    """
    Create a droplet
    """

    def post(self, request):
        params = {}

        if (
            (email := request.data.get("email"))
            and (password := request.data.get("password"))
            and (class_name := request.data.get("class"))
            and (passcode := request.data.get("passcode"))
            and (first_name := request.data.get("first_name"))
            and (last_name := request.data.get("last_name"))
        ):
            clas = Class.objects.filter(name=class_name, prefix=passcode)
            if len(clas) != 1:
                params[
                    "message"
                ] = "Class with that name and passcode was not found"
                params["status"] = 404
                return Response(params, status=params.get("status", 200))

            if clas[0].allow_registration is False:
                params[
                    "message"
                ] = "Class is not allowing registration at this time."
                params["status"] = 403
                return Response(params, status=params.get("status", 200))

            try:
                user = User.objects.create(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=passcode,
                )
            except IntegrityError:
                params[
                    "message"
                ] = "User with that email address already exists"
                params["status"] = 403
                return Response(params, status=params.get("status", 200))

            user.save()
            student = Student.objects.create(user=user)
            student.classes.set(clas)
            student.save()

            token = Token.objects.get(user=user)
            params["api_token"] = token.key
            params["status"] = 200
        else:
            params[
                "message"
            ] = "Missing arguments. email, password, first_name, last_name, class, and passcode are required"
            params["status"] = 400

        return Response(params, status=params.get("status", 200))
