from .models import Class
from .serializers import ClassSerializer
from rest_framework import permissions
from rest_framework import generics


class ClassList(generics.ListCreateAPIView):
    queryset = Class.objects.all()
    permission_classes = [permissions.IsAdminUser]
    serializer_class = ClassSerializer


class ClassDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Class.objects.all()
    permission_classes = [permissions.IsAdminUser]
    serializer_class = ClassSerializer
