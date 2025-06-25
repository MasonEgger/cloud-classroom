from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.conf import settings
from django.utils import timezone

from users.forms import CustomUserChangeForm, CustomUserCreationForm
from users.models import User

from .models import Profile


class ProfileInline(admin.StackedInline):
    """This brings in the Profile class. This is data that doesn't need
    to be added to the Admin model, but should be associated with a user.
    Current only item is SSH Key
    """

    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"
    fk_name = "user"


class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    
    # Enhanced list display for workshop mode
    list_display = (
        "email",
        "first_name",
        "last_name",
        "registration_method",
        "workshop_status_display",
        "is_staff",
        "is_superuser",
        "is_active",
    )
    
    # Enhanced filters for workshop management
    list_filter = (
        "registration_method",
        "pending_approval",
        "is_staff",
        "is_superuser",
        "is_active",
        "workshop_code_used",
        ("approved_at", admin.DateFieldListFilter),
    )
    
    # Enhanced fieldsets including workshop fields
    fieldsets = (
        (None, {"fields": ("email", "first_name", "last_name", "password")}),
        (
            "Permissions",
            {"fields": ("is_staff", "is_superuser", "is_active")},
        ),
        (
            "Workshop Registration" if settings.SIMPLE_AUTH_MODE else "Registration Info",
            {
                "fields": (
                    "registration_method",
                    "workshop_code_used",
                    "pending_approval",
                    "approved_at",
                    "approved_by",
                ),
                "classes": ("collapse",) if not settings.SIMPLE_AUTH_MODE else (),
            },
        ),
    )
    
    readonly_fields = ["approved_at", "approved_by"]
    
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                    "is_active",
                ),
            },
        ),
    )
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email", "first_name", "last_name")
    
    # Workshop-specific admin methods
    def workshop_status_display(self, obj):
        """Display workshop approval status with action buttons."""
        if obj.registration_method != 'workshop_code':
            return '-'
        
        if obj.pending_approval:
            approve_url = reverse('authentication:approve_workshop_user', args=[obj.id])
            reject_url = reverse('authentication:reject_workshop_user', args=[obj.id])
            return format_html(
                '<span style="color: orange;">Pending</span><br>'
                '<a href="{}" style="color: green; margin-right: 10px;">Approve</a>'
                '<a href="{}" style="color: red;">Reject</a>',
                approve_url, reject_url
            )
        elif obj.approved_at:
            return format_html(
                '<span style="color: green;">Approved</span><br>'
                '<small>by {} on {}</small>',
                obj.approved_by.get_full_name() if obj.approved_by else 'Unknown',
                obj.approved_at.strftime('%m/%d/%Y %H:%M')
            )
        else:
            return format_html('<span style="color: gray;">Not workshop user</span>')
    
    workshop_status_display.short_description = 'Workshop Status'
    
    # Bulk actions for workshop management
    actions = ['approve_workshop_users', 'reject_workshop_users']
    
    def approve_workshop_users(self, request, queryset):
        """Bulk approve workshop users."""
        workshop_users = queryset.filter(
            registration_method='workshop_code',
            pending_approval=True
        )
        count = 0
        for user in workshop_users:
            user.approve_user(request.user)
            count += 1
        
        self.message_user(
            request,
            f'Successfully approved {count} workshop users.'
        )
    approve_workshop_users.short_description = 'Approve selected workshop users'
    
    def reject_workshop_users(self, request, queryset):
        """Bulk reject workshop users."""
        workshop_users = queryset.filter(
            registration_method='workshop_code',
            pending_approval=True
        )
        count = workshop_users.update(
            is_active=False,
            pending_approval=False
        )
        
        self.message_user(
            request,
            f'Successfully rejected {count} workshop users.'
        )
    reject_workshop_users.short_description = 'Reject selected workshop users'
    
    def get_queryset(self, request):
        """Add workshop-related annotations."""
        qs = super().get_queryset(request)
        return qs.select_related('workshop_code_used', 'approved_by')
    
    def changelist_view(self, request, extra_context=None):
        """Add workshop statistics to the changelist view."""
        extra_context = extra_context or {}
        
        if settings.SIMPLE_AUTH_MODE:
            total_users = User.objects.count()
            workshop_users = User.objects.filter(registration_method='workshop_code').count()
            pending_approvals = User.objects.filter(pending_approval=True).count()
            
            extra_context.update({
                'workshop_stats': {
                    'total_users': total_users,
                    'workshop_users': workshop_users,
                    'pending_approvals': pending_approvals,
                }
            })
        
        return super().changelist_view(request, extra_context)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)


admin.site.register(User, CustomUserAdmin)
