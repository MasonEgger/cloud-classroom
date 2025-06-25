from allauth.account.forms import SignupForm
from django import forms


class EmailSignupForm(SignupForm):
    """
    Custom signup form that only uses email, no username field.
    """
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'First Name',
            'class': 'form-control'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Last Name',
            'class': 'form-control'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove username field if it exists
        if 'username' in self.fields:
            del self.fields['username']
        
        # Set field order
        self.field_order = ['email', 'first_name', 'last_name', 'password1', 'password2']
    
    def save(self, request):
        # Save the user without username
        user = super().save(request)
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.save()
        return user