from django.urls import path
from . import views

app_name = "classes"

urlpatterns = [
    path('', views.get_classes.as_view(), name='get_classes'),
    path('<int:class_id>', views.get_class.as_view(), name='get_class')
]
