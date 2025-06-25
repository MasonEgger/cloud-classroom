
import secrets
import string
from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_workshop_code():
    """Generate a random 8-character alphanumeric workshop code."""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))


class WorkshopCode(models.Model):
    """
    Workshop codes for simple registration in workshop mode.
    
    When SIMPLE_AUTH_MODE is enabled, users can register using these codes
    instead of going through email verification.
    """
    code = models.CharField(
        max_length=20, 
        unique=True, 
        default=generate_workshop_code,
        help_text="Unique code that participants use to register"
    )
    name = models.CharField(
        max_length=200,
        help_text="Name of the workshop or event"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the workshop"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this code can be used for registration"
    )
    max_registrations = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of registrations allowed (leave blank for unlimited)"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_workshop_codes',
        help_text="User who created this workshop code"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this code expires (leave blank for no expiration)"
    )
    
    # Link to class (only relevant when MULTI_CLASS_MODE is True)
    class_link = models.ForeignKey(
        'classes.Class',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Associated class (only used in multi-class mode)"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Workshop Code"
        verbose_name_plural = "Workshop Codes"
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def is_expired(self):
        """Check if the workshop code has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def is_valid(self):
        """Check if the workshop code is valid for use."""
        return self.is_active and not self.is_expired
    
    @property
    def registration_count(self):
        """Get the number of users who have registered with this code."""
        return self.registered_users.count()
    
    @property
    def can_register(self):
        """Check if new registrations are allowed with this code."""
        if not self.is_valid:
            return False
        
        if self.max_registrations:
            return self.registration_count < self.max_registrations
        
        return True
    
    def deactivate(self):
        """Deactivate this workshop code."""
        self.is_active = False
        self.save()
    
    def extend_expiration(self, hours=24):
        """Extend the expiration time by the specified number of hours."""
        if self.expires_at:
            self.expires_at = self.expires_at + timezone.timedelta(hours=hours)
        else:
            self.expires_at = timezone.now() + timezone.timedelta(hours=hours)
        self.save()
