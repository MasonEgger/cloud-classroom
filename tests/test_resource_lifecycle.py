"""Tests for resource lifecycle management (start, stop, destroy)."""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cloud_classroom.models import User, UserRole, ResourceStatus, Resource, ResourceTemplate


@pytest.mark.unit
def test_start_resource_success(client: TestClient, db: Session) -> None:
    """Test successfully starting a stopped resource."""
    # Create basic setup (instructor, workshop, template, student)
    instructor_data = {
        "email": "instructor@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Instructor",
    }
    client.post("/api/v1/auth/register", json=instructor_data)

    instructor = db.query(User).filter(User.email == instructor_data["email"]).first()
    assert instructor is not None
    instructor.role = UserRole.INSTRUCTOR
    db.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": instructor_data["email"],
            "password": instructor_data["password"],
        },
    )
    instructor_token = login_response.json()["access_token"]

    workshop_response = client.post(
        "/api/v1/workshops",
        json={"title": "Test Workshop", "mode": "simple"},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    workshop_id = workshop_response.json()["id"]

    template_response = client.post(
        f"/api/v1/workshops/{workshop_id}/templates",
        json={
            "name": "Test Server",
            "droplet_size": "s-1vcpu-1gb",
            "droplet_image": "ubuntu-22-04-x64",
            "region": "nyc3",
        },
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    template_id = template_response.json()["id"]

    student_data = {
        "email": "student@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Student",
    }
    client.post("/api/v1/auth/register", json=student_data)

    student_login = client.post(
        "/api/v1/auth/login",
        data={
            "username": student_data["email"],
            "password": student_data["password"],
        },
    )
    student_token = student_login.json()["access_token"]

    # Enroll student
    access_code = workshop_response.json()["access_code"]
    client.post(
        f"/api/v1/workshops/{workshop_id}/join",
        json={"access_code": access_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    # Create a stopped resource manually in database
    user = db.query(User).filter(User.email == student_data["email"]).first()
    assert user is not None

    resource = Resource(
        name="Test Resource",
        user_id=user.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.STOPPED,
        provider_resource_id="12345",
        ip_address="192.168.1.100",
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    # Mock DigitalOcean API
    with patch("cloud_classroom.services.resource_service.SyncDigitalOceanClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.start_droplet.return_value = True

        # Start the resource
        response = client.post(
            f"/api/v1/workshops/{workshop_id}/resources/{resource.id}/actions",
            json={"action": "start"},
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert response.status_code == 200
        action_result = response.json()
        assert action_result["success"] is True
        assert "started successfully" in action_result["message"]
        assert action_result["resource_id"] == resource.id

        # Verify DigitalOcean API was called
        mock_client.start_droplet.assert_called_once_with("12345")

        # Verify resource status in database
        db.refresh(resource)
        assert resource.status == ResourceStatus.ACTIVE
        assert resource.started_at is not None


@pytest.mark.unit
def test_stop_resource_success(client: TestClient, db: Session) -> None:
    """Test successfully stopping an active resource."""
    # Create basic setup
    instructor_data = {
        "email": "instructor2@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Instructor 2",
    }
    client.post("/api/v1/auth/register", json=instructor_data)

    instructor = db.query(User).filter(User.email == instructor_data["email"]).first()
    assert instructor is not None
    instructor.role = UserRole.INSTRUCTOR
    db.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": instructor_data["email"],
            "password": instructor_data["password"],
        },
    )
    instructor_token = login_response.json()["access_token"]

    workshop_response = client.post(
        "/api/v1/workshops",
        json={"title": "Test Workshop 2", "mode": "simple"},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    workshop_id = workshop_response.json()["id"]

    template_response = client.post(
        f"/api/v1/workshops/{workshop_id}/templates",
        json={
            "name": "Test Server",
            "droplet_size": "s-1vcpu-1gb",
            "droplet_image": "ubuntu-22-04-x64",
            "region": "nyc3",
        },
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    template_id = template_response.json()["id"]

    student_data = {
        "email": "student2@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Student 2",
    }
    client.post("/api/v1/auth/register", json=student_data)

    student_login = client.post(
        "/api/v1/auth/login",
        data={
            "username": student_data["email"],
            "password": student_data["password"],
        },
    )
    student_token = student_login.json()["access_token"]

    # Enroll student
    access_code = workshop_response.json()["access_code"]
    client.post(
        f"/api/v1/workshops/{workshop_id}/join",
        json={"access_code": access_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    # Create an active resource
    user = db.query(User).filter(User.email == student_data["email"]).first()
    assert user is not None

    resource = Resource(
        name="Test Resource",
        user_id=user.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.ACTIVE,
        provider_resource_id="12345",
        ip_address="192.168.1.100",
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    # Mock DigitalOcean API
    with patch("cloud_classroom.services.resource_service.SyncDigitalOceanClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.stop_droplet.return_value = True

        # Stop the resource
        response = client.post(
            f"/api/v1/workshops/{workshop_id}/resources/{resource.id}/actions",
            json={"action": "stop"},
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert response.status_code == 200
        action_result = response.json()
        assert action_result["success"] is True
        assert "stopped successfully" in action_result["message"]

        # Verify DigitalOcean API was called
        mock_client.stop_droplet.assert_called_once_with("12345")

        # Verify resource status in database
        db.refresh(resource)
        assert resource.status == ResourceStatus.STOPPED
        assert resource.stopped_at is not None


@pytest.mark.unit
def test_destroy_resource_success(client: TestClient, db: Session) -> None:
    """Test successfully destroying a resource."""
    # Create basic setup
    instructor_data = {
        "email": "instructor3@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Instructor 3",
    }
    client.post("/api/v1/auth/register", json=instructor_data)

    instructor = db.query(User).filter(User.email == instructor_data["email"]).first()
    assert instructor is not None
    instructor.role = UserRole.INSTRUCTOR
    db.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": instructor_data["email"],
            "password": instructor_data["password"],
        },
    )
    instructor_token = login_response.json()["access_token"]

    workshop_response = client.post(
        "/api/v1/workshops",
        json={"title": "Test Workshop 3", "mode": "simple"},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    workshop_id = workshop_response.json()["id"]

    template_response = client.post(
        f"/api/v1/workshops/{workshop_id}/templates",
        json={
            "name": "Test Server",
            "droplet_size": "s-1vcpu-1gb",
            "droplet_image": "ubuntu-22-04-x64",
            "region": "nyc3",
        },
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    template_id = template_response.json()["id"]

    student_data = {
        "email": "student3@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Student 3",
    }
    client.post("/api/v1/auth/register", json=student_data)

    student_login = client.post(
        "/api/v1/auth/login",
        data={
            "username": student_data["email"],
            "password": student_data["password"],
        },
    )
    student_token = student_login.json()["access_token"]

    # Enroll student
    access_code = workshop_response.json()["access_code"]
    client.post(
        f"/api/v1/workshops/{workshop_id}/join",
        json={"access_code": access_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    # Create a resource
    user = db.query(User).filter(User.email == student_data["email"]).first()
    assert user is not None

    resource = Resource(
        name="Test Resource",
        user_id=user.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.ACTIVE,
        provider_resource_id="12345",
        ip_address="192.168.1.100",
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    # Mock DigitalOcean API
    with patch("cloud_classroom.services.resource_service.SyncDigitalOceanClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.destroy_droplet.return_value = True

        # Destroy the resource
        response = client.post(
            f"/api/v1/workshops/{workshop_id}/resources/{resource.id}/actions",
            json={"action": "destroy"},
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert response.status_code == 200
        action_result = response.json()
        assert action_result["success"] is True
        assert "destroyed successfully" in action_result["message"]

        # Verify DigitalOcean API was called
        mock_client.destroy_droplet.assert_called_once_with("12345")

        # Verify resource status in database
        db.refresh(resource)
        assert resource.status == ResourceStatus.DESTROYED
        assert resource.destroyed_at is not None


@pytest.mark.unit
def test_resource_action_wrong_state(client: TestClient, db: Session) -> None:
    """Test performing action on resource in wrong state."""
    # Create basic setup
    instructor_data = {
        "email": "instructor4@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Instructor 4",
    }
    client.post("/api/v1/auth/register", json=instructor_data)

    instructor = db.query(User).filter(User.email == instructor_data["email"]).first()
    assert instructor is not None
    instructor.role = UserRole.INSTRUCTOR
    db.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": instructor_data["email"],
            "password": instructor_data["password"],
        },
    )
    instructor_token = login_response.json()["access_token"]

    workshop_response = client.post(
        "/api/v1/workshops",
        json={"title": "Test Workshop 4", "mode": "simple"},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    workshop_id = workshop_response.json()["id"]

    template_response = client.post(
        f"/api/v1/workshops/{workshop_id}/templates",
        json={
            "name": "Test Server",
            "droplet_size": "s-1vcpu-1gb",
            "droplet_image": "ubuntu-22-04-x64",
            "region": "nyc3",
        },
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    template_id = template_response.json()["id"]

    student_data = {
        "email": "student4@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Student 4",
    }
    client.post("/api/v1/auth/register", json=student_data)

    student_login = client.post(
        "/api/v1/auth/login",
        data={
            "username": student_data["email"],
            "password": student_data["password"],
        },
    )
    student_token = student_login.json()["access_token"]

    # Enroll student
    access_code = workshop_response.json()["access_code"]
    client.post(
        f"/api/v1/workshops/{workshop_id}/join",
        json={"access_code": access_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    # Create an active resource
    user = db.query(User).filter(User.email == student_data["email"]).first()
    assert user is not None

    resource = Resource(
        name="Test Resource",
        user_id=user.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.ACTIVE,
        provider_resource_id="12345",
        ip_address="192.168.1.100",
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    # Try to start an already active resource
    response = client.post(
        f"/api/v1/workshops/{workshop_id}/resources/{resource.id}/actions",
        json={"action": "start"},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert response.status_code == 400
    assert "not in stopped state" in response.json()["detail"]


@pytest.mark.unit
def test_resource_action_not_found(client: TestClient, db: Session) -> None:
    """Test performing action on non-existent resource."""
    # Create basic setup
    instructor_data = {
        "email": "instructor5@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Instructor 5",
    }
    client.post("/api/v1/auth/register", json=instructor_data)

    instructor = db.query(User).filter(User.email == instructor_data["email"]).first()
    assert instructor is not None
    instructor.role = UserRole.INSTRUCTOR
    db.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": instructor_data["email"],
            "password": instructor_data["password"],
        },
    )
    instructor_token = login_response.json()["access_token"]

    workshop_response = client.post(
        "/api/v1/workshops",
        json={"title": "Test Workshop 5", "mode": "simple"},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    workshop_id = workshop_response.json()["id"]

    student_data = {
        "email": "student5@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Student 5",
    }
    client.post("/api/v1/auth/register", json=student_data)

    student_login = client.post(
        "/api/v1/auth/login",
        data={
            "username": student_data["email"],
            "password": student_data["password"],
        },
    )
    student_token = student_login.json()["access_token"]

    # Try to perform action on non-existent resource
    response = client.post(
        f"/api/v1/workshops/{workshop_id}/resources/99999/actions",
        json={"action": "start"},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()