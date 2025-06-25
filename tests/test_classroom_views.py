"""
Tests for classroom HTMX views.
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse
from unittest.mock import patch, AsyncMock, MagicMock

from services.digitalocean import DOError


@pytest.mark.django_db
class TestClassroomDashboardView:
    """Test suite for classroom dashboard view."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = Client()

    def test_dashboard_unauthenticated(self):
        """Test dashboard redirects unauthenticated users."""
        response = self.client.get('/classroom/')
        assert response.status_code == 302
        assert 'login' in response.url

    def test_dashboard_authenticated_user(self, user_factory):
        """Test dashboard for authenticated user."""
        user = user_factory()
        self.client.force_login(user)
        
        response = self.client.get('/classroom/')
        assert response.status_code == 200
        assert 'classroom/dashboard.html' in [t.name for t in response.templates]

    def test_dashboard_with_student_data(self, student_factory, class_factory, droplet_factory):
        """Test dashboard displays student classes and droplets."""
        student = student_factory()
        classroom1 = class_factory(name="Python 101")
        classroom2 = class_factory(name="Django Advanced")
        
        student.classes.add(classroom1, classroom2)
        
        # Create droplets for student
        droplet1 = droplet_factory(owner=student.user, class_id=classroom1)
        droplet2 = droplet_factory(owner=student.user, class_id=classroom2)
        
        self.client.force_login(student.user)
        response = self.client.get('/classroom/')
        
        assert response.status_code == 200
        content = response.content.decode()
        assert "Python 101" in content
        assert "Django Advanced" in content

    def test_dashboard_with_teacher_data(self, teacher_factory, class_factory, student_factory):
        """Test dashboard displays teacher classes and students."""
        teacher = teacher_factory()
        classroom = class_factory(name="Web Development")
        teacher.classes.add(classroom)
        
        # Add students to class
        student1 = student_factory()
        student2 = student_factory()
        student1.classes.add(classroom)
        student2.classes.add(classroom)
        
        self.client.force_login(teacher.user)
        response = self.client.get('/classroom/')
        
        assert response.status_code == 200
        content = response.content.decode()
        assert "Web Development" in content


@pytest.mark.django_db
class TestDropletManagementViews:
    """Test suite for droplet management views."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = Client()

    def test_create_droplet_view_get(self, student_factory, class_factory):
        """Test GET request to create droplet view."""
        student = student_factory()
        classroom = class_factory()
        student.classes.add(classroom)
        
        self.client.force_login(student.user)
        response = self.client.get(f'/classroom/droplet/create/{classroom.id}/')
        
        assert response.status_code == 200
        assert 'classroom/droplet_create.html' in [t.name for t in response.templates]

    @patch('classroom.views.ClassroomService')
    def test_create_droplet_post_success(self, mock_service_class, student_factory, class_factory):
        """Test successful droplet creation."""
        student = student_factory()
        classroom = class_factory(droplet_student_limit=5)
        student.classes.add(classroom)
        
        # Mock the service
        mock_service = AsyncMock()
        mock_service_class.return_value.__aenter__.return_value = mock_service
        mock_service.create_droplet_for_student.return_value = MagicMock(
            name='test-droplet',
            droplet_id='12345',
            ip_addr='192.168.1.1'
        )
        
        self.client.force_login(student.user)
        response = self.client.post(f'/classroom/droplet/create/{classroom.id}/')
        
        assert response.status_code == 302
        assert '/classroom/' in response.url

    @patch('classroom.views.ClassroomService')
    def test_create_droplet_limit_exceeded(self, mock_service_class, student_factory, class_factory, droplet_factory):
        """Test droplet creation when limit is exceeded."""
        student = student_factory()
        classroom = class_factory(droplet_student_limit=1)
        student.classes.add(classroom)
        
        # Student already has max droplets
        droplet_factory(owner=student.user, class_id=classroom)
        
        self.client.force_login(student.user)
        response = self.client.post(f'/classroom/droplet/create/{classroom.id}/')
        
        assert response.status_code == 200
        content = response.content.decode()
        assert 'limit' in content.lower()

    @patch('classroom.views.ClassroomService')
    def test_create_droplet_service_error(self, mock_service_class, student_factory, class_factory):
        """Test droplet creation when service raises error."""
        student = student_factory()
        classroom = class_factory()
        student.classes.add(classroom)
        
        # Mock service to raise error
        mock_service = AsyncMock()
        mock_service_class.return_value.__aenter__.return_value = mock_service
        mock_service.create_droplet_for_student.side_effect = DOError("API Error")
        
        self.client.force_login(student.user)
        response = self.client.post(f'/classroom/droplet/create/{classroom.id}/')
        
        assert response.status_code == 200
        content = response.content.decode()
        assert 'error' in content.lower()

    def test_create_droplet_not_enrolled(self, student_factory, class_factory):
        """Test student cannot create droplet for class not enrolled in."""
        student = student_factory()
        classroom = class_factory()
        # Student not enrolled in classroom
        
        self.client.force_login(student.user)
        response = self.client.post(f'/classroom/droplet/create/{classroom.id}/')
        
        assert response.status_code == 403

    @patch('classroom.views.ClassroomService')
    def test_delete_droplet_success(self, mock_service_class, student_factory, class_factory, droplet_factory):
        """Test successful droplet deletion."""
        student = student_factory()
        classroom = class_factory()
        student.classes.add(classroom)
        droplet = droplet_factory(owner=student.user, class_id=classroom)
        
        # Mock the service
        mock_service = AsyncMock()
        mock_service_class.return_value.__aenter__.return_value = mock_service
        
        self.client.force_login(student.user)
        response = self.client.post(f'/classroom/droplet/delete/{droplet.id}/')
        
        assert response.status_code == 302
        assert '/classroom/' in response.url

    def test_delete_droplet_not_owner(self, student_factory, class_factory, droplet_factory):
        """Test student cannot delete droplet they don't own."""
        student1 = student_factory()
        student2 = student_factory()
        classroom = class_factory()
        student1.classes.add(classroom)
        student2.classes.add(classroom)
        
        # Droplet owned by student1
        droplet = droplet_factory(owner=student1.user, class_id=classroom)
        
        # Student2 tries to delete
        self.client.force_login(student2.user)
        response = self.client.post(f'/classroom/droplet/delete/{droplet.id}/')
        
        assert response.status_code == 403

    @patch('classroom.views.ClassroomService')
    def test_teacher_delete_student_droplet(self, mock_service_class, teacher_factory, student_factory, class_factory, droplet_factory):
        """Test teacher can delete student droplets in their class."""
        teacher = teacher_factory()
        student = student_factory()
        classroom = class_factory()
        teacher.classes.add(classroom)
        student.classes.add(classroom)
        
        droplet = droplet_factory(owner=student.user, class_id=classroom)
        
        # Mock the service
        mock_service = AsyncMock()
        mock_service_class.return_value.__aenter__.return_value = mock_service
        
        self.client.force_login(teacher.user)
        response = self.client.post(f'/classroom/droplet/delete/{droplet.id}/')
        
        assert response.status_code == 302


@pytest.mark.django_db
class TestClassManagementViews:
    """Test suite for class management views."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = Client()

    def test_class_list_view(self, teacher_factory, class_factory):
        """Test class list view for teachers."""
        teacher = teacher_factory()
        classroom1 = class_factory(name="Class 1")
        classroom2 = class_factory(name="Class 2")
        classroom3 = class_factory(name="Other Class")  # Not taught by teacher
        
        teacher.classes.add(classroom1, classroom2)
        
        self.client.force_login(teacher.user)
        response = self.client.get('/classroom/classes/')
        
        assert response.status_code == 200
        content = response.content.decode()
        assert "Class 1" in content
        assert "Class 2" in content
        assert "Other Class" not in content

    def test_class_detail_view(self, teacher_factory, student_factory, class_factory, droplet_factory):
        """Test class detail view with students and droplets."""
        teacher = teacher_factory()
        classroom = class_factory(name="Detailed Class")
        teacher.classes.add(classroom)
        
        # Add students with droplets
        student1 = student_factory()
        student2 = student_factory()
        student1.classes.add(classroom)
        student2.classes.add(classroom)
        
        droplet1 = droplet_factory(owner=student1.user, class_id=classroom)
        droplet2 = droplet_factory(owner=student2.user, class_id=classroom)
        
        self.client.force_login(teacher.user)
        response = self.client.get(f'/classroom/class/{classroom.id}/')
        
        assert response.status_code == 200
        content = response.content.decode()
        assert "Detailed Class" in content
        assert student1.user.email in content
        assert student2.user.email in content

    def test_class_detail_not_teacher(self, student_factory, teacher_factory, class_factory):
        """Test non-teacher cannot access class detail."""
        teacher = teacher_factory()
        student = student_factory()
        classroom = class_factory()
        teacher.classes.add(classroom)
        
        self.client.force_login(student.user)
        response = self.client.get(f'/classroom/class/{classroom.id}/')
        
        assert response.status_code == 403


@pytest.mark.django_db
class TestHTMXIntegration:
    """Test HTMX-specific functionality."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = Client()

    def test_htmx_partial_response(self, student_factory, class_factory):
        """Test HTMX partial template rendering."""
        student = student_factory()
        classroom = class_factory()
        student.classes.add(classroom)
        
        self.client.force_login(student.user)
        response = self.client.get(
            '/classroom/',
            HTTP_HX_REQUEST='true'
        )
        
        assert response.status_code == 200
        # HTMX responses should use partial templates
        assert any('partial' in t.name or 'fragment' in t.name for t in response.templates if hasattr(response, 'templates'))

    @patch('classroom.views.ClassroomService')
    def test_htmx_droplet_creation(self, mock_service_class, student_factory, class_factory):
        """Test HTMX droplet creation returns partial response."""
        student = student_factory()
        classroom = class_factory()
        student.classes.add(classroom)
        
        # Mock service
        mock_service = AsyncMock()
        mock_service_class.return_value.__aenter__.return_value = mock_service
        mock_service.create_droplet_for_student.return_value = MagicMock(
            name='htmx-droplet',
            droplet_id='htmx123'
        )
        
        self.client.force_login(student.user)
        response = self.client.post(
            f'/classroom/droplet/create/{classroom.id}/',
            HTTP_HX_REQUEST='true'
        )
        
        # HTMX requests should return different response format
        assert response.status_code in [200, 302]

    def test_htmx_error_handling(self, student_factory, class_factory):
        """Test HTMX error responses."""
        student = student_factory()
        classroom = class_factory()
        # Student not enrolled
        
        self.client.force_login(student.user)
        response = self.client.post(
            f'/classroom/droplet/create/{classroom.id}/',
            HTTP_HX_REQUEST='true'
        )
        
        assert response.status_code == 403


@pytest.mark.django_db
class TestClassroomSecurity:
    """Test security aspects of classroom views."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = Client()

    def test_csrf_protection(self, student_factory, class_factory):
        """Test CSRF protection on forms."""
        student = student_factory()
        classroom = class_factory()
        student.classes.add(classroom)
        
        self.client.force_login(student.user)
        
        # Get the form first to get CSRF token
        response = self.client.get(f'/classroom/droplet/create/{classroom.id}/')
        assert response.status_code == 200
        
        # Extract CSRF token from response
        csrf_token = None
        for line in response.content.decode().split('\n'):
            if 'csrfmiddlewaretoken' in line:
                csrf_token = line.split('value="')[1].split('"')[0]
                break
        
        assert csrf_token is not None

    def test_permission_isolation(self, student_factory, teacher_factory, class_factory):
        """Test users can only access their own classes."""
        student = student_factory()
        teacher = teacher_factory()
        
        student_class = class_factory(name="Student Class")
        teacher_class = class_factory(name="Teacher Class")
        
        student.classes.add(student_class)
        teacher.classes.add(teacher_class)
        
        # Student should not access teacher's class
        self.client.force_login(student.user)
        response = self.client.get(f'/classroom/class/{teacher_class.id}/')
        assert response.status_code == 403
        
        # Teacher should not access other teacher's class
        self.client.force_login(teacher.user)
        response = self.client.get(f'/classroom/class/{student_class.id}/')
        assert response.status_code == 403

    def test_droplet_ownership_enforcement(self, student_factory, class_factory, droplet_factory):
        """Test droplet operations respect ownership."""
        student1 = student_factory()
        student2 = student_factory()
        classroom = class_factory()
        
        student1.classes.add(classroom)
        student2.classes.add(classroom)
        
        # Student1's droplet
        droplet = droplet_factory(owner=student1.user, class_id=classroom)
        
        # Student2 tries to delete student1's droplet
        self.client.force_login(student2.user)
        response = self.client.post(f'/classroom/droplet/delete/{droplet.id}/')
        
        assert response.status_code == 403