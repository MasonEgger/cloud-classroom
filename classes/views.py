from rest_framework.views import APIView
from rest_framework.response import Response
from django.forms.models import model_to_dict
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from classes.models import Class
from classes.serializers import ClassSerializer
from students.models import Student
from teachers.models import Teacher
from users.utils import get_user_role


class get_classes(APIView):
    """
    This method returns all of the classes that:
    * A student is enrolled in
    * A teacher teaches
    """

    def get(self, request):
        data = get_user_role(request.user)

        params = {"classes": {}}

        if data[0] is False:
            params["message"] = "No classes found"
            params["status"] = 404
            del params["classes"]
            return Response(params, status=params["status"])

        user_data = data[1]

        if user_data["is_student"] is True:
            student = user_data["student_object"]
            classes = list(student.classes.all())
            student_classes = []
            for clas in classes:
                student_classes.append({"name": clas.name, "id": clas.id})
            params["classes"]["student"] = student_classes
        if user_data["is_teacher"] is True:
            teacher = user_data["teacher_object"]
            classes = list(teacher.classes.all())
            teacher_classes = []
            for clas in classes:
                teacher_classes.append({"name": clas.name, "id": clas.id})
            params["classes"]["teacher"] = teacher_classes

        if (
            params["classes"].get("student", None) is None
            and params["classes"].get("teacher", None) is None
        ):
            params["message"] = "No classes found"
            params["status"] = 404
            del params["classes"]

        params["status"] = 200

        return Response(params, status=params.get("status", 200))


class get_open_classes(APIView):
    """
    This method returns all of the classes that are currently open for
    registration
    """

    def get(self, request):
        classes = Class.objects.all()
        params = {}
        if len(classes) == 0:
            params["message"] = "No classes found"
            params["status"] = 404
        else:
            params["classes"] = []
            for clas in classes:
                if clas.allow_registration is True:
                    params["classes"].append(
                        {"name": clas.name, "id": clas.id}
                    )
            if not params["classes"]:
                params["status"] = 404
                params["message"] = "No classes open for registration"
                del params["classes"]
            else:
                params["status"] = 200
        return Response(params, params.get("status", 200))


class enrolled(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, class_id):
        params = {}
        request_user = request.user
        user_data = get_user_role(request_user)[1]

        if user_data["is_student"] is False:
            params[
                "message"
            ] = "User is not a student, therefore cannot be enrolled in a class"
            params["status"] = 401
            return Response(params, params["status"])

        try:
            c = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            params["message"] = "Invalid class"
            params["status"] = 404
            return Response(params, params["status"])

        if c in user_data["user"].classes.all():
            params["message"] = "Student is enrolled."
            params["status"] = 200
        else:
            params["message"] = "Student is not enrolled."
            params["status"] = 401

        return Response(params, params["status"])


class enroll(APIView):
    permission_classes = (IsAuthenticated,)

    # Modify to post, bring in passcode, figure out why teaches_class
    # from utils doesn't work.
    def post(self, request):
        params = {}
        request_user = request.user
        class_id = request.data.get("class_id", None)
        passcode = request.data.get("passcode", None)

        if class_id is None or passcode is None:
            params["message"] = "Missing parameters class_id or passcode"
            params["status"] = 400
            return Response(params, params["status"])

        try:
            class_id = int(class_id)
        except ValueError:
            params["message"] = "class_id must be numerical"
            params["status"] = 400
            return Response(params, params["status"])

        try:
            c = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            params["message"] = "Invalid class"
            params["status"] = 404
            return Response(params, params["status"])

        if c.allow_registration is False:
            params["message"] = "Class not configured for registration"
            params["status"] = 403
            return Response(params, params["status"])

        user_data = get_user_role(request_user, c)[1]

        print(user_data)

        if user_data["teaches_class"] is True:
            params[
                "message"
            ] = "User teaches this class, therefore cannot enroll"
            params["status"] = 401
            return Response(params, params["status"])

        if user_data["is_in_class"] is True:
            params["message"] = "User is already enrolled in this class"
            params["status"] = 401
            return Response(params, params["status"])

        if user_data["is_student"] is False:
            if user_data["user"] is None:
                student = Student.objects.create(user=request_user)
                student.classes.add(c)
                student.save()
                params["message"] = "User was enrolled in class"
                params["status"] = 200
            elif user_data["is_teacher"] is True:
                student = Student.objects.create(user=user_data["user"].user)
                student.classes.add(c)
                student.save()
                params["message"] = "User was enrolled in class"
                params["status"] = 200
        else:
            student = Student.objects.get(user=user_data["user"].user)
            student.classes.add(c)
            student.save()
            params["message"] = "User was enrolled in class"
            params["status"] = 200

        return Response(params, params["status"])


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


################################################################################
# Admin Methods                                                                #
################################################################################

class create_class(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def post(self, request):
        params = {}

        clas = ClassSerializer(data=request.data)
        if clas.is_valid() is True:
            class_obj = clas.save()
            params["message"] = "Class successfully created"
            params["status"] = 200
            params["info"] = model_to_dict(class_obj)
        else:
            params["message"] = "Invalid parameters passed"
            params["status"] = 400
            params["errors"] = clas.errors
        return Response(params, status=params.get("status", 200))

class list_classes(APIView):
    """
    This method returns all of the classes. This is an Admin Only Feature
    """

    permission_classes = (IsAuthenticated, IsAdminUser)

    def get(self, request):
        classes = Class.objects.all()
        params = {}
        if len(classes) == 0:
            params["message"] = "No classes found"
            params["status"] = 404
        else:
            params["classes"] = []
            for clas in classes:
                params["classes"].append(model_to_dict(clas))

            params["status"] = 200
        return Response(params, params.get("status", 200))

class update_class(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def post(self, request):
        params = {}

        class_id = request.data.get("id")
        try:
            class_obj = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            params["message"] = f"Class with id {class_id} does not exist"
            params["status"] = 404
        else:
            class_dict = model_to_dict(class_obj)
            # Droplet count not updating....why?
            class_dict.update(request.data)
            clas = ClassSerializer(class_obj, data=class_dict)
            if clas.is_valid() is True:
                class_obj_save = clas.save()
                params["status"] = 200
                params["message"] = "Class was updated successfully"
                params["info"] = model_to_dict(class_obj_save)
            else:
                params[
                    "message"
                ] = "Invalid parameters passed. You must data for every class field."
                params["status"] = 400
                params["errors"] = clas.errors
        return Response(params, status=params.get("status", 200))

class delete_class(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def delete(self, request, class_id):
        params = {}
        try:
            class_obj = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            params["message"] = f"Class with id {class_id} does not exist"
            params["status"] = 404
        else:
            class_obj.delete()
            params["message"] = "Class was successfully deleted"
            params["status"] = 200
        
        return Response(params, status=params.get("status", 200))


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
