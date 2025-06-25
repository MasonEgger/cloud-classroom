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
    ssh_key = Faker("text", max_nb_chars=200)


class TeacherFactory(DjangoModelFactory):
    """Factory for creating Teacher instances."""
    
    class Meta:
        model = Teacher
    
    user = SubFactory(UserFactory)


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