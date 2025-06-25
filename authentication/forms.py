from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import WorkshopCode

User = get_user_model()


class WorkshopRegistrationForm(forms.Form):
    """
    Simple registration form for workshop mode.
    Users enter a workshop code and basic information.
    """
    workshop_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500',
            'placeholder': 'Enter workshop code'
        }),
        help_text="Enter the workshop code provided by your instructor"
    )
    
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500',
            'placeholder': 'First name'
        })
    )
    
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500',
            'placeholder': 'Last name'
        })
    )
    
    preferred_username = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500',
            'placeholder': 'Preferred username (optional)'
        }),
        help_text="This will be used as your username in the system"
    )
    
    def clean_workshop_code(self):
        """Validate that the workshop code exists and is valid."""
        code = self.cleaned_data['workshop_code'].upper()
        
        try:
            workshop_code = WorkshopCode.objects.get(code=code)
        except WorkshopCode.DoesNotExist:
            raise ValidationError("Invalid workshop code. Please check with your instructor.")
        
        if not workshop_code.can_register:
            if workshop_code.is_expired:
                raise ValidationError("This workshop code has expired.")
            elif not workshop_code.is_active:
                raise ValidationError("This workshop code is no longer active.")
            elif workshop_code.max_registrations and workshop_code.registration_count >= workshop_code.max_registrations:
                raise ValidationError("This workshop has reached its maximum number of participants.")
            else:
                raise ValidationError("Registration is not available for this workshop code.")
        
        return workshop_code
    
    def clean_preferred_username(self):
        """Validate that the preferred username is available."""
        username = self.cleaned_data.get('preferred_username')
        if username:
            # Check if username is already taken (we'll use email field for this)
            if User.objects.filter(email__icontains=username).exists():
                # Generate a unique variant
                counter = 1
                base_username = username
                while User.objects.filter(email__icontains=f"{base_username}{counter}").exists():
                    counter += 1
                username = f"{base_username}{counter}"
        
        return username
    
    def save(self):
        """Create a new user with the provided information."""
        workshop_code = self.cleaned_data['workshop_code']
        first_name = self.cleaned_data['first_name']
        last_name = self.cleaned_data['last_name']
        preferred_username = self.cleaned_data.get('preferred_username')
        
        # Generate email from preferred username or names
        if preferred_username:
            email = f"{preferred_username}@workshop.local"
        else:
            # Generate email from first and last name
            email = f"{first_name.lower()}.{last_name.lower()}@workshop.local"
        
        # Ensure email is unique by adding numbers if needed
        base_email = email
        counter = 1
        while User.objects.filter(email=email).exists():
            username_part = base_email.split('@')[0]
            domain_part = base_email.split('@')[1]
            email = f"{username_part}{counter}@{domain_part}"
            counter += 1
        
        # Create the user
        user = User.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=User.objects.make_random_password(12)  # Generate random password
        )
        
        # Set workshop-specific fields
        user.registration_method = 'workshop_code'
        user.workshop_code_used = workshop_code
        user.pending_approval = True  # Requires approval in workshop mode
        user.is_active = False  # Not active until approved
        user.save()
        
        return user


class WorkshopCodeCreationForm(forms.ModelForm):
    """Form for creating workshop codes in the admin interface."""
    
    class Meta:
        model = WorkshopCode
        fields = ['name', 'description', 'max_registrations', 'expires_at', 'class_link']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.created_by = kwargs.pop('created_by', None)
        super().__init__(*args, **kwargs)
        
        # Set default expiration to 24 hours from now
        if not self.instance.pk:
            self.fields['expires_at'].initial = timezone.now() + timezone.timedelta(hours=24)
    
    def save(self, commit=True):
        workshop_code = super().save(commit=False)
        if self.created_by:
            workshop_code.created_by = self.created_by
        if commit:
            workshop_code.save()
        return workshop_code