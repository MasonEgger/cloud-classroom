"""
Tests for authentication views.
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.utils import timezone
from unittest.mock import patch

from authentication.models import WorkshopCode

User = get_user_model()


@pytest.mark.django_db
class TestWorkshopRegistrationView:
    """Test suite for workshop registration view."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = Client()

    def test_get_workshop_register_simple_mode(self, class_factory):
        """Test GET request to workshop register in simple auth mode."""
        with patch.object(settings, 'SIMPLE_AUTH_MODE', True):
            response = self.client.get('/auth/workshop/register/')
            
            assert response.status_code == 200
            assert 'Workshop Registration' in response.content.decode()
            assert 'workshop_code' in response.content.decode()

    def test_get_workshop_register_not_simple_mode(self):
        """Test GET redirects to standard signup when not in simple mode."""
        with patch.object(settings, 'SIMPLE_AUTH_MODE', False):
            response = self.client.get('/auth/workshop/register/')
            
            assert response.status_code == 302
            assert 'account_signup' in response.url

    def test_post_valid_workshop_registration(self, class_factory):
        """Test successful workshop registration."""
        classroom = class_factory()
        workshop_code = WorkshopCode.objects.create(
            code="VALID123",
            name="Test Workshop",
            created_by=None,
            class_link=classroom
        )
        
        with patch.object(settings, 'SIMPLE_AUTH_MODE', True):
            response = self.client.post('/auth/workshop/register/', {
                'workshop_code': 'VALID123',
                'first_name': 'John',
                'last_name': 'Doe',
                'preferred_username': 'johndoe'
            })
            
            assert response.status_code == 302
            assert 'workshop_register_success' in response.url
            
            # Check user was created
            user = User.objects.get(email='johndoe@workshop.local')
            assert user.first_name == 'John'
            assert user.last_name == 'Doe'
            assert user.pending_approval is True
            assert user.is_active is False

    def test_post_invalid_workshop_code(self):
        """Test registration with invalid workshop code."""
        with patch.object(settings, 'SIMPLE_AUTH_MODE', True):
            response = self.client.post('/auth/workshop/register/', {
                'workshop_code': 'INVALID',
                'first_name': 'John',
                'last_name': 'Doe'
            })
            
            assert response.status_code == 200
            assert 'Invalid workshop code' in response.content.decode()

    def test_post_workshop_registration_exception(self, class_factory):
        """Test handling of exceptions during registration."""
        classroom = class_factory()
        WorkshopCode.objects.create(
            code="ERROR123",
            name="Error Workshop",
            created_by=None,
            class_link=classroom
        )
        
        with patch.object(settings, 'SIMPLE_AUTH_MODE', True):
            with patch('authentication.forms.WorkshopRegistrationForm.save') as mock_save:
                mock_save.side_effect = Exception("Database error")
                
                response = self.client.post('/auth/workshop/register/', {
                    'workshop_code': 'ERROR123',
                    'first_name': 'John',
                    'last_name': 'Doe'
                })
                
                assert response.status_code == 200
                messages = list(get_messages(response.wsgi_request))
                assert any('Registration failed' in str(msg) for msg in messages)

    def test_workshop_register_success_view(self):
        """Test workshop registration success page."""
        response = self.client.get('/auth/workshop/register/success/')
        
        assert response.status_code == 200
        assert 'Registration Pending' in response.content.decode()
        assert 'pending approval' in response.content.decode()

    def test_workshop_register_info_with_valid_code(self, class_factory):
        """Test workshop info view with valid code."""
        classroom = class_factory()
        workshop_code = WorkshopCode.objects.create(
            code="INFO123",
            name="Info Workshop",
            description="Workshop for testing info view",
            created_by=None,
            class_link=classroom
        )
        
        response = self.client.get('/auth/workshop/info/INFO123/')
        
        assert response.status_code == 200
        assert 'Info Workshop' in response.content.decode()
        assert 'Workshop for testing info view' in response.content.decode()

    def test_workshop_register_info_with_invalid_code(self):
        """Test workshop info view with invalid code."""
        response = self.client.get('/auth/workshop/info/INVALID/')
        
        assert response.status_code == 200
        messages = list(get_messages(response.wsgi_request))
        assert any('Workshop code not found' in str(msg) for msg in messages)

    def test_workshop_register_info_without_code(self):
        """Test workshop info view without code parameter."""
        response = self.client.get('/auth/workshop/info/')
        
        assert response.status_code == 200
        assert 'Workshop Information' in response.content.decode()


@pytest.mark.django_db 
class TestWorkshopAdminViews:
    """Test suite for workshop admin views."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = Client()

    def test_approve_workshop_user_as_staff(self, user_factory):
        """Test staff user can approve workshop users."""
        staff_user = user_factory(is_staff=True)
        workshop_user = user_factory(
            pending_approval=True,
            registration_method='workshop_code'
        )
        
        self.client.force_login(staff_user)
        
        response = self.client.post(f'/auth/approve-user/{workshop_user.id}/')
        
        assert response.status_code == 302
        
        workshop_user.refresh_from_db()
        assert workshop_user.pending_approval is False
        assert workshop_user.approved_by == staff_user
        assert workshop_user.approved_at is not None

    def test_approve_workshop_user_non_staff(self, user_factory):
        """Test non-staff user cannot approve workshop users."""
        regular_user = user_factory()
        workshop_user = user_factory(pending_approval=True)
        
        self.client.force_login(regular_user)
        
        response = self.client.post(f'/auth/approve-user/{workshop_user.id}/')
        
        assert response.status_code == 403

    def test_approve_workshop_user_with_htmx(self, user_factory):
        """Test approving user with HTMX request."""
        staff_user = user_factory(is_staff=True)
        workshop_user = user_factory(pending_approval=True)
        
        self.client.force_login(staff_user)
        
        response = self.client.post(
            f'/auth/approve-user/{workshop_user.id}/',
            HTTP_HX_REQUEST='true'
        )
        
        assert response.status_code == 200
        assert 'workshop_user_approved.html' in response.template_name

    def test_approve_nonexistent_user(self, user_factory):
        """Test approving non-existent user."""
        staff_user = user_factory(is_staff=True)
        self.client.force_login(staff_user)
        
        response = self.client.post('/auth/approve-user/99999/')
        
        assert response.status_code == 302
        messages = list(get_messages(response.wsgi_request))
        assert any('not found' in str(msg) for msg in messages)

    def test_reject_workshop_user_as_staff(self, user_factory):
        """Test staff user can reject workshop users."""
        staff_user = user_factory(is_staff=True)
        workshop_user = user_factory(
            pending_approval=True,
            registration_method='workshop_code'
        )
        
        self.client.force_login(staff_user)
        
        response = self.client.post(f'/auth/reject-user/{workshop_user.id}/')
        
        assert response.status_code == 302
        
        workshop_user.refresh_from_db()
        assert workshop_user.is_active is False
        assert workshop_user.pending_approval is False

    def test_reject_workshop_user_non_staff(self, user_factory):
        """Test non-staff user cannot reject workshop users."""
        regular_user = user_factory()
        workshop_user = user_factory(pending_approval=True)
        
        self.client.force_login(regular_user)
        
        response = self.client.post(f'/auth/reject-user/{workshop_user.id}/')
        
        assert response.status_code == 403

    def test_reject_workshop_user_with_htmx(self, user_factory):
        """Test rejecting user with HTMX request."""
        staff_user = user_factory(is_staff=True)
        workshop_user = user_factory(pending_approval=True)
        
        self.client.force_login(staff_user)
        
        response = self.client.post(
            f'/auth/reject-user/{workshop_user.id}/',
            HTTP_HX_REQUEST='true'
        )
        
        assert response.status_code == 200
        assert 'workshop_user_rejected.html' in response.template_name

    def test_reject_nonexistent_user(self, user_factory):
        """Test rejecting non-existent user."""
        staff_user = user_factory(is_staff=True)
        self.client.force_login(staff_user)
        
        response = self.client.post('/auth/reject-user/99999/')
        
        assert response.status_code == 302
        messages = list(get_messages(response.wsgi_request))
        assert any('not found' in str(msg) for msg in messages)


@pytest.mark.django_db
class TestAuthenticationCheck:
    """Test authentication check view."""

    @pytest.fixture(autouse=True) 
    def setup(self):
        """Set up test environment."""
        self.client = Client()

    def test_check_authenticated_user(self, user_factory):
        """Test check view with authenticated user."""
        user = user_factory()
        self.client.force_login(user)
        
        response = self.client.get('/auth/check/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['message'] == 'authenticated'

    def test_check_unauthenticated_user(self):
        """Test check view with unauthenticated user."""
        response = self.client.get('/auth/check/')
        
        assert response.status_code == 302  # Redirect to login


@pytest.mark.django_db
class TestWorkshopModeIntegration:
    """Integration tests for workshop mode functionality."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = Client()

    def test_complete_workshop_flow(self, class_factory, user_factory):
        """Test complete workshop registration and approval flow."""
        # Create workshop setup
        classroom = class_factory(name="Integration Test Class")
        admin = user_factory(is_staff=True)
        
        workshop_code = WorkshopCode.objects.create(
            code="FLOW123",
            name="Integration Workshop",
            description="End-to-end test workshop",
            created_by=admin,
            class_link=classroom,
            max_registrations=5
        )
        
        with patch.object(settings, 'SIMPLE_AUTH_MODE', True):
            # Step 1: User registers for workshop
            response = self.client.post('/auth/workshop/register/', {
                'workshop_code': 'FLOW123',
                'first_name': 'Integration',
                'last_name': 'User',
                'preferred_username': 'intuser'
            })
            
            assert response.status_code == 302
            
            # Check user was created in pending state
            user = User.objects.get(email='intuser@workshop.local')
            assert user.pending_approval is True
            assert user.is_active is False
            assert user.workshop_code_used == workshop_code
            
            # Step 2: Admin approves user
            self.client.force_login(admin)
            response = self.client.post(f'/auth/approve-user/{user.id}/')
            
            assert response.status_code == 302
            
            # Check user is now approved
            user.refresh_from_db()
            assert user.pending_approval is False
            assert user.is_active is True
            assert user.approved_by == admin
            assert user.approved_at is not None

    def test_workshop_registration_limits(self, class_factory, user_factory):
        """Test workshop registration limits are enforced."""
        classroom = class_factory()
        workshop_code = WorkshopCode.objects.create(
            code="LIMIT1",
            name="Limited Workshop",
            created_by=None,
            class_link=classroom,
            max_registrations=1
        )
        
        with patch.object(settings, 'SIMPLE_AUTH_MODE', True):
            # First registration should succeed
            response1 = self.client.post('/auth/workshop/register/', {
                'workshop_code': 'LIMIT1',
                'first_name': 'First',
                'last_name': 'User'
            })
            assert response1.status_code == 302
            
            # Second registration should fail
            response2 = self.client.post('/auth/workshop/register/', {
                'workshop_code': 'LIMIT1',
                'first_name': 'Second', 
                'last_name': 'User'
            })
            assert response2.status_code == 200
            assert 'maximum number' in response2.content.decode()

    def test_expired_workshop_code_registration(self, class_factory):
        """Test registration with expired workshop code."""
        classroom = class_factory()
        workshop_code = WorkshopCode.objects.create(
            code="EXPIRED",
            name="Expired Workshop",
            created_by=None,
            class_link=classroom,
            expires_at=timezone.now() - timezone.timedelta(hours=1)
        )
        
        with patch.object(settings, 'SIMPLE_AUTH_MODE', True):
            response = self.client.post('/auth/workshop/register/', {
                'workshop_code': 'EXPIRED',
                'first_name': 'Late',
                'last_name': 'User'
            })
            
            assert response.status_code == 200
            assert 'expired' in response.content.decode()
            assert not User.objects.filter(first_name='Late').exists()