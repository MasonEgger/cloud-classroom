from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Profile
from users.forms import CustomUserCreationForm, CustomUserChangeForm
from users.models import User

# from users.models import User


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
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_superuser",
        "is_active",
    )
    list_filter = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_superuser",
        "is_active",
    )
    fieldsets = (
        (None, {"fields": ("email", "first_name", "last_name", "password")}),
        (
            "Permissions",
            {"fields": ("is_staff", "is_superuser", "is_active")},
        ),
    )
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

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(
            request, obj
        )


admin.site.register(User, CustomUserAdmin)
