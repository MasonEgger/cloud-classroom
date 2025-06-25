from __future__ import annotations

from django.urls import path

from . import views

app_name = "authentication"

urlpatterns = [
    # Workshop registration URLs
    path('workshop/register/', views.workshop_register, name='workshop_register'),
    path('workshop/register/success/', views.workshop_register_success, name='workshop_register_success'),
    path('workshop/info/', views.workshop_register_info, name='workshop_info'),
    path('workshop/info/<str:code>/', views.workshop_register_info, name='workshop_info_code'),
    
    # Admin workshop management URLs (HTMX)
    path('admin/approve-user/<int:user_id>/', views.approve_workshop_user, name='approve_workshop_user'),
    path('admin/reject-user/<int:user_id>/', views.reject_workshop_user, name='reject_workshop_user'),
    
    # Authentication check
    path('check/', views.check, name='check'),
]
