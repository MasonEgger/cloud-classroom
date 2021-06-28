from django.urls import path
from . import views

urlpatterns = [
    path("", views.ClassList.as_view()),
    path("<int:pk>/", views.ClassDetail.as_view()),
]
