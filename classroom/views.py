"""
Modern classroom management views using HTMX and async services.
"""

from __future__ import annotations

import asyncio
from typing import Any

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView
from django_htmx.http import HttpResponseClientRedirect

from classes.models import Class
from droplet.models import Droplet
from services.classroom import ClassroomService, ClassroomError
from services.digitalocean import DOError
from services.utils import AsyncServiceMixin, handle_service_error, run_async_in_sync
from students.models import Student
from teachers.models import Teacher
from users.utils import get_user_role


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view that routes users based on their role."""
    
    template_name = "classroom/dashboard.html"
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
        # Determine user role and redirect appropriately
        is_valid, user_info = get_user_role(self.request.user)
        
        context.update({
            "user_info": user_info if is_valid else {},
            "is_valid_user": is_valid,
        })
        
        return context


@method_decorator(login_required, name="dispatch")
class TeacherDashboardView(AsyncServiceMixin, View):
    """Teacher dashboard for managing classes and droplets."""
    
    def get(self, request: HttpRequest) -> HttpResponse:
        """Render teacher dashboard."""
        is_valid, user_info = get_user_role(request.user)
        
        if not is_valid or not user_info.get("is_teacher"):
            return render(request, "classroom/permission_denied.html", {
                "message": "Access denied. Teacher account required."
            })
        
        try:
            # Get teacher's classes and related droplets
            teacher = user_info["teacher_object"]
            classes = teacher.classes.all().prefetch_related("droplets", "students")
            
            # Get summary statistics
            total_classes = classes.count()
            total_droplets = sum(cls.droplets.count() for cls in classes)
            active_droplets = sum(
                cls.droplets.filter(destroyed_at__isnull=True).count() 
                for cls in classes
            )
            
            context = {
                "teacher": teacher,
                "classes": classes,
                "stats": {
                    "total_classes": total_classes,
                    "total_droplets": total_droplets,
                    "active_droplets": active_droplets,
                    "destroyed_droplets": total_droplets - active_droplets,
                },
            }
            
            return render(request, "classroom/teacher_dashboard.html", context)
            
        except Exception as e:
            return handle_service_error(e)


@method_decorator(login_required, name="dispatch")
class StudentDashboardView(AsyncServiceMixin, View):
    """Student dashboard for managing personal droplets."""
    
    def get(self, request: HttpRequest) -> HttpResponse:
        """Render student dashboard."""
        is_valid, user_info = get_user_role(request.user)
        
        if not is_valid or not user_info.get("is_student"):
            return render(request, "classroom/permission_denied.html", {
                "message": "Access denied. Student account required."
            })
        
        try:
            student = user_info["student_object"]
            
            # Get student's classes and droplets
            classes = student.classes.all()
            droplets = Droplet.objects.filter(
                owner=request.user,
                destroyed_at__isnull=True
            ).select_related("class_id")
            
            context = {
                "student": student,
                "classes": classes,
                "droplets": droplets,
                "stats": {
                    "total_classes": classes.count(),
                    "active_droplets": droplets.count(),
                    "can_create_droplets": any(
                        cls.droplets.filter(owner=request.user).count() < cls.droplet_student_limit
                        for cls in classes
                    ),
                },
            }
            
            return render(request, "classroom/student_dashboard.html", context)
            
        except Exception as e:
            return handle_service_error(e)


@login_required
@require_http_methods(["GET"])
def class_detail_view(request: HttpRequest, class_id: int) -> HttpResponse:
    """Detailed view of a specific class."""
    classroom = get_object_or_404(Class, id=class_id)
    is_valid, user_info = get_user_role(request.user, classroom)
    
    if not is_valid:
        return render(request, "classroom/permission_denied.html", {
            "message": "Access denied. You are not enrolled in this class."
        })
    
    # Get droplets for this class
    droplets = classroom.droplets.filter(destroyed_at__isnull=True).select_related("owner")
    
    # Check if user can manage this class (is teacher)
    can_manage = user_info.get("is_teacher") and user_info.get("teaches_class")
    
    # Get user's droplets in this class
    user_droplets = droplets.filter(owner=request.user) if user_info.get("is_student") else []
    
    context = {
        "classroom": classroom,
        "droplets": droplets,
        "user_droplets": user_droplets,
        "can_manage": can_manage,
        "is_teacher": user_info.get("is_teacher", False),
        "is_student": user_info.get("is_student", False),
        "can_create_droplet": (
            user_info.get("is_student") and 
            len(user_droplets) < classroom.droplet_student_limit
        ),
    }
    
    return render(request, "classroom/class_detail.html", context)


@method_decorator(login_required, name="dispatch")
class CreateDropletView(AsyncServiceMixin, View):
    """Handle droplet creation with HTMX."""
    
    def post(self, request: HttpRequest, class_id: int) -> HttpResponse:
        """Create a new droplet for the student."""
        classroom = get_object_or_404(Class, id=class_id)
        is_valid, user_info = get_user_role(request.user, classroom)
        
        if not is_valid or not user_info.get("is_student") or not user_info.get("is_in_class"):
            return JsonResponse({
                "error": "Permission denied", 
                "message": "You are not enrolled in this class."
            }, status=403)
        
        student = user_info["student_object"]
        
        # Check droplet limit
        existing_droplets = Droplet.objects.filter(
            owner=request.user,
            class_id=classroom,
            destroyed_at__isnull=True
        ).count()
        
        if existing_droplets >= classroom.droplet_student_limit:
            return JsonResponse({
                "error": "Limit exceeded",
                "message": f"You can only have {classroom.droplet_student_limit} droplet(s) per class."
            }, status=400)
        
        try:
            # Create droplet using async service
            async def create_droplet_async():
                async with ClassroomService() as service:
                    return await service.create_droplet_for_student(classroom, student)
            
            django_droplet, connection_info = self.run_async(create_droplet_async())
            
            # Return HTMX response with new droplet info
            if request.htmx:
                return render(request, "classroom/partials/droplet_card.html", {
                    "droplet": django_droplet,
                    "connection_info": connection_info,
                    "classroom": classroom,
                })
            else:
                return JsonResponse({
                    "success": True,
                    "droplet_id": django_droplet.id,
                    "connection_info": connection_info,
                })
                
        except (ClassroomError, DOError) as e:
            if request.htmx:
                return render(request, "classroom/partials/error_message.html", {
                    "error": str(e),
                })
            else:
                return handle_service_error(e)


@method_decorator(login_required, name="dispatch")
class DropletActionView(AsyncServiceMixin, View):
    """Handle droplet power actions (start, stop, reboot, delete)."""
    
    def post(self, request: HttpRequest, droplet_id: int) -> HttpResponse:
        """Perform action on droplet."""
        droplet = get_object_or_404(Droplet, id=droplet_id)
        action = request.POST.get("action")
        
        # Check permissions
        is_valid, user_info = get_user_role(request.user, droplet.class_id)
        can_modify = (
            droplet.owner == request.user or  # Student owns droplet
            (user_info.get("is_teacher") and user_info.get("teaches_class"))  # Teacher manages class
        )
        
        if not can_modify:
            return JsonResponse({
                "error": "Permission denied",
                "message": "You cannot modify this droplet."
            }, status=403)
        
        if action not in ["power_on", "power_off", "shutdown", "reboot", "delete"]:
            return JsonResponse({
                "error": "Invalid action",
                "message": f"Action '{action}' is not supported."
            }, status=400)
        
        try:
            async def perform_action_async():
                async with ClassroomService() as service:
                    if action == "delete":
                        await service.delete_droplet(droplet)
                        return {"action": "deleted", "droplet_id": droplet.id}
                    else:
                        result = await service.power_action_droplet(droplet, action)
                        # Sync status after action
                        updated_droplet = await service.sync_droplet_status(droplet)
                        return {
                            "action": action,
                            "droplet_id": droplet.id,
                            "status": updated_droplet.status,
                            "action_result": result,
                        }
            
            result = self.run_async(perform_action_async())
            
            if request.htmx:
                if action == "delete":
                    # Return empty content to remove the droplet card
                    response = HttpResponse("")
                    response["HX-Trigger"] = "dropletDeleted"
                    return response
                else:
                    # Re-render the droplet card with updated status
                    return render(request, "classroom/partials/droplet_card.html", {
                        "droplet": droplet,
                        "classroom": droplet.class_id,
                    })
            else:
                return JsonResponse({"success": True, **result})
                
        except (ClassroomError, DOError) as e:
            if request.htmx:
                return render(request, "classroom/partials/error_message.html", {
                    "error": str(e),
                })
            else:
                return handle_service_error(e)


@login_required
@require_http_methods(["GET"])
def droplet_connection_info(request: HttpRequest, droplet_id: int) -> HttpResponse:
    """Get connection information for a droplet."""
    droplet = get_object_or_404(Droplet, id=droplet_id)
    
    # Check permissions
    is_valid, user_info = get_user_role(request.user, droplet.class_id)
    can_view = (
        droplet.owner == request.user or  # Student owns droplet
        (user_info.get("is_teacher") and user_info.get("teaches_class"))  # Teacher manages class
    )
    
    if not can_view:
        return JsonResponse({
            "error": "Permission denied",
            "message": "You cannot view this droplet's connection info."
        }, status=403)
    
    connection_info = {
        "ip_address": droplet.ip_addr,
        "username": "student",
        "password": droplet.initial_password,
        "ssh_command": f"ssh student@{droplet.ip_addr}" if droplet.ip_addr else None,
        "status": getattr(droplet, "status", "unknown"),
    }
    
    if request.htmx:
        return render(request, "classroom/partials/connection_info.html", {
            "droplet": droplet,
            "connection_info": connection_info,
        })
    else:
        return JsonResponse({"success": True, "connection_info": connection_info})


@login_required
@require_http_methods(["GET"])
def class_resources_view(request: HttpRequest) -> HttpResponse:
    """Get available DigitalOcean resources for class configuration."""
    is_valid, user_info = get_user_role(request.user)
    
    if not is_valid or not user_info.get("is_teacher"):
        return JsonResponse({
            "error": "Permission denied",
            "message": "Teacher access required."
        }, status=403)
    
    try:
        async def get_resources_async():
            async with ClassroomService() as service:
                regions = await service.client.list_regions()
                sizes = await service.client.list_sizes()
                images = await service.client.list_images()
                
                return {
                    "regions": [{"slug": r.slug, "name": r.name} for r in regions if r.available],
                    "sizes": [
                        {
                            "slug": s.slug,
                            "memory": s.memory,
                            "vcpus": s.vcpus,
                            "disk": s.disk,
                            "price_monthly": s.price_monthly,
                        }
                        for s in sizes if s.available
                    ],
                    "images": [
                        {
                            "slug": i.slug,
                            "name": i.name,
                            "distribution": i.distribution,
                        }
                        for i in images if i.public and "ubuntu" in i.distribution.lower()
                    ],
                }
        
        resources = run_async_in_sync(get_resources_async())
        
        if request.htmx:
            return render(request, "classroom/partials/resource_options.html", {
                "resources": resources,
            })
        else:
            return JsonResponse({"success": True, "resources": resources})
            
    except (ClassroomError, DOError) as e:
        return handle_service_error(e)