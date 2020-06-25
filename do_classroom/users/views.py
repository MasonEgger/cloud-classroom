from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from droplet.views import get_user_role
from students.models import Student
from classes.models import Class
from droplet.models import Droplet

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
