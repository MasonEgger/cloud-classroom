from django.shortcuts import render

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


# Check for a valid token
class check(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        return Response({"message":"authenticated"})

