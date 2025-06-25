from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .forms import WorkshopRegistrationForm
from .models import WorkshopCode


@require_http_methods(["GET", "POST"])
@csrf_protect
def workshop_register(request):
    """
    Workshop registration view for simple auth mode.
    Users can register using a workshop code.
    """
    if not settings.SIMPLE_AUTH_MODE:
        # Redirect to standard registration if not in simple auth mode
        return redirect('account_signup')
    
    if request.method == 'POST':
        form = WorkshopRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(
                    request, 
                    f"Registration successful! Your account is pending approval. "
                    f"You'll be able to login once an instructor approves your registration."
                )
                return redirect('authentication:workshop_register_success')
            except Exception as e:
                messages.error(request, f"Registration failed: {str(e)}")
    else:
        form = WorkshopRegistrationForm()
    
    return render(request, 'workshop/register.html', {
        'form': form,
        'title': 'Workshop Registration'
    })


def workshop_register_success(request):
    """Success page after workshop registration."""
    return render(request, 'workshop/register_success.html', {
        'title': 'Registration Pending'
    })


def workshop_register_info(request, code=None):
    """
    Display information about a workshop code.
    Can be used to show workshop details before registration.
    """
    workshop_code = None
    if code:
        try:
            workshop_code = WorkshopCode.objects.get(code=code.upper(), is_active=True)
        except WorkshopCode.DoesNotExist:
            messages.error(request, "Workshop code not found or inactive.")
    
    return render(request, 'workshop/info.html', {
        'workshop_code': workshop_code,
        'title': f'Workshop: {workshop_code.name}' if workshop_code else 'Workshop Information'
    })


@login_required
def check(request):
    """Check if user is authenticated."""
    return JsonResponse({"message": "authenticated"})


# Admin helper views for workshop management
@login_required
@require_http_methods(["POST"])
def approve_workshop_user(request, user_id):
    """
    Approve a workshop user (staff only).
    This can be called via HTMX from the admin interface.
    """
    if not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id, pending_approval=True)
        user.approve_user(request.user)
        
        if request.headers.get('HX-Request'):
            return render(request, 'admin/workshop_user_approved.html', {
                'user': user
            })
        else:
            messages.success(request, f"User {user.get_full_name()} has been approved.")
            return redirect('admin:users_user_changelist')
            
    except User.DoesNotExist:
        if request.headers.get('HX-Request'):
            return render(request, 'admin/workshop_user_error.html', {
                'error': 'User not found or not pending approval'
            })
        else:
            messages.error(request, "User not found or not pending approval.")
            return redirect('admin:users_user_changelist')


@login_required
@require_http_methods(["POST"])
def reject_workshop_user(request, user_id):
    """
    Reject a workshop user (staff only).
    This marks the user as inactive.
    """
    if not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id, pending_approval=True)
        user.is_active = False
        user.pending_approval = False
        user.save()
        
        if request.headers.get('HX-Request'):
            return render(request, 'admin/workshop_user_rejected.html', {
                'user': user
            })
        else:
            messages.warning(request, f"User {user.get_full_name()} has been rejected.")
            return redirect('admin:users_user_changelist')
            
    except User.DoesNotExist:
        if request.headers.get('HX-Request'):
            return render(request, 'admin/workshop_user_error.html', {
                'error': 'User not found or not pending approval'
            })
        else:
            messages.error(request, "User not found or not pending approval.")
            return redirect('admin:users_user_changelist')
