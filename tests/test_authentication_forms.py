"""
Tests for authentication forms.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch

from authentication.forms import WorkshopRegistrationForm, WorkshopCodeCreationForm
from authentication.models import WorkshopCode
from users.models import User


@pytest.mark.django_db
class TestWorkshopRegistrationForm:
    """Test suite for WorkshopRegistrationForm."""

    def test_valid_form(self, workshop_code_factory):
        """Test form with valid data."""
        workshop_code = workshop_code_factory(code="TEST123")
        
        form_data = {
            'workshop_code': 'TEST123',
            'first_name': 'John',
            'last_name': 'Doe',
            'preferred_username': 'johndoe'
        }
        
        form = WorkshopRegistrationForm(data=form_data)
        assert form.is_valid()

    def test_invalid_workshop_code(self):
        """Test form with invalid workshop code."""
        form_data = {
            'workshop_code': 'INVALID',
            'first_name': 'John',
            'last_name': 'Doe',
            'preferred_username': 'johndoe'
        }
        
        form = WorkshopRegistrationForm(data=form_data)
        assert not form.is_valid()
        assert 'workshop_code' in form.errors

    def test_expired_workshop_code(self, workshop_code_factory):
        """Test form with expired workshop code."""
        workshop_code = workshop_code_factory(
            code="EXPIRED",
            expires_at=timezone.now() - timezone.timedelta(hours=1)
        )
        
        form_data = {
            'workshop_code': 'EXPIRED',
            'first_name': 'John',
            'last_name': 'Doe'
        }
        
        form = WorkshopRegistrationForm(data=form_data)
        assert not form.is_valid()
        assert 'workshop_code' in form.errors
        assert 'expired' in form.errors['workshop_code'][0].lower()

    def test_inactive_workshop_code(self, workshop_code_factory):
        """Test form with inactive workshop code."""
        workshop_code = workshop_code_factory(
            code="INACTIVE",
            is_active=False
        )
        
        form_data = {
            'workshop_code': 'INACTIVE',
            'first_name': 'John',
            'last_name': 'Doe'
        }
        
        form = WorkshopRegistrationForm(data=form_data)
        assert not form.is_valid()
        assert 'workshop_code' in form.errors

    def test_max_registrations_reached(self, workshop_code_factory, user_factory):
        """Test form when max registrations reached."""
        workshop_code = workshop_code_factory(
            code="FULL123",
            max_registrations=1
        )
        
        # Create a user that used this workshop code
        existing_user = user_factory()
        existing_user.workshop_code_used = workshop_code
        existing_user.save()
        
        form_data = {
            'workshop_code': 'FULL123',
            'first_name': 'Jane',
            'last_name': 'Doe'
        }
        
        form = WorkshopRegistrationForm(data=form_data)
        assert not form.is_valid()
        assert 'workshop_code' in form.errors

    def test_preferred_username_uniqueness(self, workshop_code_factory, user_factory):
        """Test preferred username uniqueness checking."""
        workshop_code = workshop_code_factory(code="TEST123")
        
        # Create existing user with similar email
        existing_user = user_factory(email="john@workshop.local")
        
        form_data = {
            'workshop_code': 'TEST123',
            'first_name': 'John',
            'last_name': 'Doe',
            'preferred_username': 'john'
        }
        
        form = WorkshopRegistrationForm(data=form_data)
        assert form.is_valid()
        
        # Should generate unique username
        cleaned_data = form.cleaned_data
        assert cleaned_data['preferred_username'] != 'john'

    def test_save_creates_user(self, workshop_code_factory):
        """Test that save creates a user with correct attributes."""
        workshop_code = workshop_code_factory(code="SAVE123")
        
        form_data = {
            'workshop_code': 'SAVE123',
            'first_name': 'John',
            'last_name': 'Doe',
            'preferred_username': 'johndoe'
        }
        
        form = WorkshopRegistrationForm(data=form_data)
        assert form.is_valid()
        
        user = form.save()
        
        assert user.first_name == 'John'
        assert user.last_name == 'Doe'
        assert user.email == 'johndoe@workshop.local'
        assert user.registration_method == 'workshop_code'
        assert user.workshop_code_used == workshop_code
        assert user.pending_approval is True
        assert user.is_active is False

    def test_save_without_preferred_username(self, workshop_code_factory):
        """Test save without preferred username generates email from name."""
        workshop_code = workshop_code_factory(code="NOUSER")
        
        form_data = {
            'workshop_code': 'NOUSER',
            'first_name': 'Jane',
            'last_name': 'Smith'
        }
        
        form = WorkshopRegistrationForm(data=form_data)
        assert form.is_valid()
        
        user = form.save()
        
        assert user.email == 'jane.smith@workshop.local'

    def test_email_uniqueness_with_counters(self, workshop_code_factory, user_factory):
        """Test email uniqueness when conflicts exist."""
        workshop_code = workshop_code_factory(code="UNIQUE")
        
        # Create existing users
        user_factory(email="john.doe@workshop.local")
        user_factory(email="john.doe1@workshop.local")
        
        form_data = {
            'workshop_code': 'UNIQUE',
            'first_name': 'John',
            'last_name': 'Doe'
        }
        
        form = WorkshopRegistrationForm(data=form_data)
        assert form.is_valid()
        
        user = form.save()
        
        # Should get john.doe2@workshop.local
        assert user.email == 'john.doe2@workshop.local'


@pytest.mark.django_db
class TestWorkshopCodeCreationForm:
    """Test suite for WorkshopCodeCreationForm."""

    def test_valid_form(self, class_factory, user_factory):
        """Test form with valid data."""
        classroom = class_factory()
        creator = user_factory()
        
        form_data = {
            'name': 'Test Workshop',
            'description': 'A test workshop for learning',
            'max_registrations': 25,
            'class_link': classroom.id
        }
        
        form = WorkshopCodeCreationForm(data=form_data, created_by=creator)
        assert form.is_valid()

    def test_form_without_max_registrations(self, class_factory, user_factory):
        """Test form without max registrations (unlimited)."""
        classroom = class_factory()
        creator = user_factory()
        
        form_data = {
            'name': 'Unlimited Workshop',
            'description': 'Workshop with no registration limit',
            'class_link': classroom.id
        }
        
        form = WorkshopCodeCreationForm(data=form_data, created_by=creator)
        assert form.is_valid()

    def test_form_with_future_expiration(self, class_factory, user_factory):
        """Test form with future expiration date."""
        classroom = class_factory()
        creator = user_factory()
        
        future_date = timezone.now() + timezone.timedelta(days=7)
        
        form_data = {
            'name': 'Future Workshop',
            'description': 'Workshop expiring in a week',
            'expires_at': future_date.strftime('%Y-%m-%dT%H:%M'),
            'class_link': classroom.id
        }
        
        form = WorkshopCodeCreationForm(data=form_data, created_by=creator)
        assert form.is_valid()

    def test_default_expiration_24_hours(self, class_factory, user_factory):
        """Test that default expiration is set to 24 hours."""
        classroom = class_factory()
        creator = user_factory()
        
        form = WorkshopCodeCreationForm(created_by=creator)
        
        # Check that expires_at field has a default value
        expires_initial = form.fields['expires_at'].initial
        assert expires_initial is not None
        
        # Should be approximately 24 hours from now
        now = timezone.now()
        expected = now + timezone.timedelta(hours=24)
        time_diff = abs((expires_initial - expected).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_save_with_created_by(self, class_factory, user_factory):
        """Test that save sets created_by field."""
        classroom = class_factory()
        creator = user_factory()
        
        form_data = {
            'name': 'Creator Workshop',
            'description': 'Workshop with creator',
            'class_link': classroom.id
        }
        
        form = WorkshopCodeCreationForm(data=form_data, created_by=creator)
        assert form.is_valid()
        
        workshop_code = form.save()
        
        assert workshop_code.name == 'Creator Workshop'
        assert workshop_code.created_by == creator
        assert workshop_code.class_link == classroom
        assert len(workshop_code.code) == 8  # Auto-generated code

    def test_save_without_commit(self, class_factory, user_factory):
        """Test save with commit=False."""
        classroom = class_factory()
        creator = user_factory()
        
        form_data = {
            'name': 'No Commit Workshop',
            'description': 'Workshop not committed',
            'class_link': classroom.id
        }
        
        form = WorkshopCodeCreationForm(data=form_data, created_by=creator)
        assert form.is_valid()
        
        workshop_code = form.save(commit=False)
        
        assert workshop_code.created_by == creator
        assert workshop_code.pk is None  # Not saved to database
        
        # Manual save
        workshop_code.save()
        assert workshop_code.pk is not None

    def test_missing_required_fields(self):
        """Test form with missing required fields."""
        form_data = {
            'description': 'Missing name'
        }
        
        form = WorkshopCodeCreationForm(data=form_data)
        assert not form.is_valid()
        assert 'name' in form.errors

    def test_form_widgets(self, class_factory, user_factory):
        """Test that form widgets are configured correctly."""
        form = WorkshopCodeCreationForm()
        
        # Check textarea widget for description
        assert form.fields['description'].widget.__class__.__name__ == 'Textarea'
        assert form.fields['description'].widget.attrs['rows'] == 3
        
        # Check datetime widget
        assert form.fields['expires_at'].widget.__class__.__name__ == 'DateTimeInput'
        assert form.fields['expires_at'].widget.attrs['type'] == 'datetime-local'