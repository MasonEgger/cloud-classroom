"""
Pytest configuration and fixtures for Cloud Classroom tests.
"""

from __future__ import annotations

import asyncio
import os
import django
from unittest.mock import AsyncMock, MagicMock
from typing import Any, AsyncGenerator

# Set up Django before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_settings')
django.setup()

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from factory import Faker, SubFactory
from factory.django import DjangoModelFactory

from classes.models import Class
from droplet.models import Droplet
from students.models import Student
from teachers.models import Teacher
from users.models import Profile, User

# Configure asyncio for pytest
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# User and Profile Factories
class UserFactory(DjangoModelFactory):
    """Factory for creating User instances."""
    
    class Meta:
        model = User
    
    email = Faker("email")
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    is_active = True


class ProfileFactory(DjangoModelFactory):
    """Factory for creating Profile instances."""
    
    class Meta:
        model = Profile
    
    user = SubFactory(UserFactory)
    ssh_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCgWTbgWhRBUbelv5+9UKJsJh3FZQ0FT+F3ff1PtuSGfb0a+/QCycDv74AOECaEFbCSoFepS16ECYY1/8yGKB2iu+eN8JqKwAVZAc3JKjCsRQ4Fyy4ziuVeWfsgv7cO8Mb8V9R9F6uSsSmmiqNTlM1sf36AJYQIi57W0LDY775yLQTawCQGt8pFQbXXEL138K2vd0Lq4G/i75sHW5b3IGHRQ0dosHV2bV107usqAHjYl4C63pTsNovePztzjyC7lwy0zDxAX43KOckcE/yZCfRjxKWvk6z6nf5mgK59pHucgykB3IJ2p1NpcfKf1dgEAgpzZT2mH+Ji8j09967UTbxt test@example.com"
    
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override to handle auto-created profiles."""
        user = kwargs.get('user')
        if user and hasattr(user, 'profile'):
            # Update existing profile instead of creating new one
            profile = user.profile
            profile.ssh_key = kwargs.get('ssh_key', cls.ssh_key)
            profile.save()
            return profile
        return super()._create(model_class, *args, **kwargs)


class TeacherFactory(DjangoModelFactory):
    """Factory for creating Teacher instances."""
    
    class Meta:
        model = Teacher
    
    user = SubFactory(UserFactory)
    droplet_limit = 10


class StudentFactory(DjangoModelFactory):
    """Factory for creating Student instances."""
    
    class Meta:
        model = Student
    
    user = SubFactory(UserFactory)


class ClassFactory(DjangoModelFactory):
    """Factory for creating Class instances."""
    
    class Meta:
        model = Class
    
    name = Faker("text", max_nb_chars=100)
    droplet_count = 1
    prefix = Faker("word")
    droplet_image = "ubuntu-22-04-x64"
    droplet_size = "s-1vcpu-1gb"
    droplet_region = "nyc1"
    droplet_student_limit = 5
    droplet_priv_net = False
    droplet_ipv6 = False


class DropletFactory(DjangoModelFactory):
    """Factory for creating Droplet instances."""
    
    class Meta:
        model = Droplet
    
    name = Faker("hostname")
    class_id = SubFactory(ClassFactory)
    droplet_id = Faker("numerify", text="########")
    initial_password = Faker("password")
    region = "nyc1"
    image = "ubuntu-22-04-x64"
    ip_addr = Faker("ipv4")
    owner = SubFactory(UserFactory)


class WorkshopCodeFactory(DjangoModelFactory):
    """Factory for creating WorkshopCode instances."""
    
    class Meta:
        model = 'authentication.WorkshopCode'
    
    code = Faker("lexify", text="????????", letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    name = Faker("text", max_nb_chars=50)
    description = Faker("text", max_nb_chars=200)
    created_by = SubFactory(UserFactory)
    class_link = SubFactory(ClassFactory)


# Additional fixtures for API testing
@pytest.fixture
def api_client():
    """Provide authenticated API client."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def mock_digitalocean_manager():
    """Provide mock DigitalOcean manager."""
    return MagicMock()


@pytest.fixture
def mock_classroom_service():
    """Provide mock ClassroomService."""
    return AsyncMock()


# Pytest fixtures
@pytest.fixture
def user_factory():
    """Provide UserFactory."""
    return UserFactory


@pytest.fixture
def profile_factory():
    """Provide ProfileFactory."""
    return ProfileFactory


@pytest.fixture
def teacher_factory():
    """Provide TeacherFactory."""
    return TeacherFactory


@pytest.fixture
def student_factory():
    """Provide StudentFactory."""
    return StudentFactory


@pytest.fixture
def class_factory():
    """Provide ClassFactory."""
    return ClassFactory


@pytest.fixture
def droplet_factory():
    """Provide DropletFactory."""
    return DropletFactory


@pytest.fixture
def workshop_code_factory():
    """Provide WorkshopCodeFactory."""
    return WorkshopCodeFactory


@pytest.fixture
def user(user_factory):
    """Create a test user."""
    return user_factory()


@pytest.fixture
def teacher(teacher_factory):
    """Create a test teacher."""
    return teacher_factory()


@pytest.fixture
def student(student_factory):
    """Create a test student."""
    return student_factory()


@pytest.fixture
def classroom(class_factory):
    """Create a test class."""
    return class_factory()


@pytest.fixture
def droplet(droplet_factory):
    """Create a test droplet."""
    return droplet_factory()


@pytest.fixture
def authenticated_client(user):
    """Provide Django test client with authenticated user."""
    client = Client()
    client.force_login(user)
    return client


# Mock fixtures for external services
@pytest.fixture
def mock_do_client():
    """Mock DigitalOcean client."""
    mock = AsyncMock()
    
    # Mock common responses
    mock.list_regions.return_value = [
        MagicMock(slug="nyc1", name="New York 1", available=True),
        MagicMock(slug="sfo3", name="San Francisco 3", available=True),
    ]
    
    mock.list_sizes.return_value = [
        MagicMock(
            slug="s-1vcpu-1gb", 
            memory=1024, 
            vcpus=1, 
            disk=25,
            price_monthly=6.0,
            available=True,
            regions=["nyc1", "sfo3"],
        ),
        MagicMock(
            slug="s-2vcpu-2gb",
            memory=2048,
            vcpus=2,
            disk=50,
            price_monthly=12.0,
            available=True,
            regions=["nyc1", "sfo3"],
        ),
    ]
    
    mock.list_images.return_value = [
        MagicMock(
            slug="ubuntu-22-04-x64",
            name="Ubuntu 22.04 x64",
            distribution="Ubuntu",
            public=True,
        ),
        MagicMock(
            slug="ubuntu-20-04-x64",
            name="Ubuntu 20.04 x64",
            distribution="Ubuntu",
            public=True,
        ),
    ]
    
    # Mock droplet creation
    mock_droplet = MagicMock()
    mock_droplet.id = 123456789
    mock_droplet.name = "test-droplet"
    mock_droplet.status = "active"
    mock_droplet.ip_address = "192.168.1.100"
    mock_droplet.size_slug = "s-1vcpu-1gb"
    mock_droplet.region = {"slug": "nyc1"}
    mock_droplet.image = {"slug": "ubuntu-22-04-x64"}
    
    mock.create_droplet.return_value = mock_droplet
    mock.get_droplet.return_value = mock_droplet
    mock.wait_for_droplet_active.return_value = mock_droplet
    mock.delete_droplet.return_value = None
    
    return mock


@pytest.fixture
def mock_classroom_service(mock_do_client):
    """Mock ClassroomService."""
    mock_service = AsyncMock()
    mock_service.client = mock_do_client
    
    # Mock service methods
    mock_service._generate_password.return_value = "TestPass123"
    mock_service._generate_droplet_name.return_value = "test-student-AT-example-DOT-com-Test"
    mock_service._generate_user_data.return_value = "#cloud-config\nusers:\n  - name: student"
    
    return mock_service


@pytest.fixture
async def async_mock_do_client() -> AsyncGenerator[AsyncMock, None]:
    """Async fixture for mocked DigitalOcean client."""
    mock = AsyncMock()
    
    # Setup mock responses
    mock.__aenter__.return_value = mock
    mock.__aexit__.return_value = None
    
    yield mock