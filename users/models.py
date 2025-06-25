from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from sshpubkeys import SSHKey

# Token creation will be handled by django-allauth or custom implementation


def validate_ssh_key(value):
    """Validate that the provided value is a valid SSH public key."""
    ssh = SSHKey(value)
    try:
        ssh.parse()
    except Exception as e:
        msg = "The provided key is invalid"
        raise ValidationError(msg) from e


# Token creation handled by django-allauth


class MyUserManager(BaseUserManager):
    """
    A custom user manager to deal with emails as unique identifiers for auth
    instead of usernames. The default that's used is "UserManager"
    """

    def _create_user(self, email, password, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            msg = "The Email must be set"
            raise ValueError(msg)
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            msg = "Superuser must have is_staff=True."
            raise ValueError(msg)
        if extra_fields.get("is_superuser") is not True:
            msg = "Superuser must have is_superuser=True."
            raise ValueError(msg)
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, null=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=150)
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    
    # Workshop-related fields
    pending_approval = models.BooleanField(
        default=False,
        help_text=_("User is pending approval in workshop mode")
    )
    registration_method = models.CharField(
        max_length=20,
        choices=[
            ('email', 'Email Registration'),
            ('workshop_code', 'Workshop Code Registration'),
        ],
        default='email',
        help_text=_("How the user registered")
    )
    workshop_code_used = models.ForeignKey(
        'authentication.WorkshopCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registered_users',
        help_text=_("Workshop code used for registration")
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the user was approved (for workshop registrations)")
    )
    approved_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_users',
        help_text=_("Who approved this user")
    )
    
    USERNAME_FIELD = "email"
    objects = MyUserManager()

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.last_name}, {self.first_name}"

    def get_short_name(self):
        return self.email
    
    def approve_user(self, approved_by_user):
        """Approve a workshop user."""
        from django.utils import timezone
        self.pending_approval = False
        self.approved_at = timezone.now()
        self.approved_by = approved_by_user
        self.save()
    
    @property
    def is_workshop_user(self):
        """Check if user registered via workshop code."""
        return self.registration_method == 'workshop_code'
    
    @property
    def can_login(self):
        """Check if user can login (not pending approval)."""
        return self.is_active and not self.pending_approval


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    ssh_key = models.CharField(
        max_length=4096, validators=[validate_ssh_key], null=True, blank=True
    )

    def __str__(self):
        return self.user.email


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()
