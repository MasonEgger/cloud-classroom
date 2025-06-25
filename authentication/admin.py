
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.conf import settings
from django.utils import timezone

from .models import WorkshopCode


@admin.register(WorkshopCode)
class WorkshopCodeAdmin(admin.ModelAdmin):
    """Admin interface for managing workshop codes."""
    
    list_display = [
        'code', 
        'name', 
        'registration_count_display',
        'max_registrations',
        'is_active', 
        'is_expired_display',
        'created_at',
        'created_by'
    ]
    list_filter = [
        'is_active',
        'created_at',
        ('expires_at', admin.DateFieldListFilter),
        'created_by'
    ]
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['code', 'created_at', 'registration_count_display']
    
    fieldsets = (
        ('Workshop Information', {
            'fields': ('code', 'name', 'description')
        }),
        ('Registration Settings', {
            'fields': ('is_active', 'max_registrations', 'expires_at')
        }),
        ('Advanced Settings', {
            'fields': ('class_link',),
            'classes': ('collapse',),
            'description': 'Only relevant when MULTI_CLASS_MODE is enabled'
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'registration_count_display'),
            'classes': ('collapse',)
        })
    )
    
    def registration_count_display(self, obj):
        """Display registration count with link to view users."""
        count = obj.registration_count
        if count > 0:
            url = reverse('admin:users_user_changelist') + f'?workshop_code_used__id__exact={obj.id}'
            return format_html('<a href="{}">{} registrations</a>', url, count)
        return '0 registrations'
    registration_count_display.short_description = 'Registrations'
    
    def is_expired_display(self, obj):
        """Display expiration status with color coding."""
        if obj.expires_at is None:
            return format_html('<span style="color: green;">Never expires</span>')
        elif obj.is_expired:
            return format_html('<span style="color: red;">Expired</span>')
        else:
            return format_html('<span style="color: orange;">Expires {}</span>', 
                             obj.expires_at.strftime('%m/%d/%Y %H:%M'))
    is_expired_display.short_description = 'Expiration'
    
    def save_model(self, request, obj, form, change):
        """Set the created_by field when creating new workshop codes."""
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Filter by created_by if user is not superuser."""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(created_by=request.user)
        return qs
    
    def has_change_permission(self, request, obj=None):
        """Allow users to edit their own workshop codes."""
        if obj is None:
            return True
        if request.user.is_superuser:
            return True
        return obj.created_by == request.user
    
    def has_delete_permission(self, request, obj=None):
        """Allow users to delete their own workshop codes."""
        if obj is None:
            return True
        if request.user.is_superuser:
            return True
        return obj.created_by == request.user
    
    actions = ['deactivate_codes', 'extend_expiration']
    
    def deactivate_codes(self, request, queryset):
        """Bulk action to deactivate workshop codes."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Successfully deactivated {updated} workshop codes.')
    deactivate_codes.short_description = 'Deactivate selected workshop codes'
    
    def extend_expiration(self, request, queryset):
        """Bulk action to extend expiration by 24 hours."""
        for code in queryset:
            code.extend_expiration(24)
        self.message_user(request, f'Extended expiration for {queryset.count()} workshop codes by 24 hours.')
    extend_expiration.short_description = 'Extend expiration by 24 hours'
