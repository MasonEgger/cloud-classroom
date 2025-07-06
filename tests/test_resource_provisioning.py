"""Tests for resource provisioning functionality."""

from unittest.mock import Mock, patch
from datetime import datetime, UTC

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cloud_classroom.models import User, UserRole, Workshop, ResourceTemplate, Resource, ResourceStatus
from cloud_classroom.services.digitalocean_client import DropletInfo


@pytest.mark.unit
def test_provision_resource_success(client: TestClient, db: Session) -> None:
    """Test successful resource provisioning from template."""
    # Create instructor
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

    # Login instructor and create workshop
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": instructor_data["email"],
            "password": instructor_data["password"],
        },
    )
    instructor_token = login_response.json()["access_token"]

    # Create workshop
    workshop_data = {
        "title": "Test Workshop",
        "description": "A workshop for testing resource provisioning",
        "mode": "simple",
    }

    workshop_response = client.post(
        "/api/v1/workshops",
        json=workshop_data,
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    workshop_id = workshop_response.json()["id"]

    # Create resource template
    template_data = {
        "name": "Basic Ubuntu Server",
        "description": "Ubuntu 22.04 with basic tools",
        "droplet_size": "s-1vcpu-1gb",
        "droplet_image": "ubuntu-22-04-x64",
        "region": "nyc3",
        "user_data": "#!/bin/bash\necho 'Hello World' > /tmp/hello.txt",
        "max_instances_per_user": 2,
        "estimated_cost_per_hour": 600,
    }

    template_response = client.post(
        f"/api/v1/workshops/{workshop_id}/templates",
        json=template_data,
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    template_id = template_response.json()["id"]

    # Create student and enroll in workshop
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

    # Enroll student in workshop
    access_code = workshop_response.json()["access_code"]
    client.post(
        f"/api/v1/workshops/{workshop_id}/join",
        json={"access_code": access_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    # Mock DigitalOcean API
    with patch("cloud_classroom.services.resource_service.SyncDigitalOceanClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_droplet_info = DropletInfo(
            id="12345",
            name="test-resource-1",
            ip_address="192.168.1.100",
            status="new",
            size="s-1vcpu-1gb",
            image="ubuntu-22-04-x64",
            region="nyc3",
        )
        mock_client.create_droplet.return_value = mock_droplet_info

        # Provision resource
        provision_data = {
            "name": "My Test Server",
            "template_id": template_id,
        }

        response = client.post(
            f"/api/v1/workshops/{workshop_id}/resources",
            json=provision_data,
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert response.status_code == 201
        resource = response.json()
        
        assert resource["name"] == "My Test Server"
        assert resource["template_id"] == template_id
        assert resource["status"] == "provisioning"
        assert resource["provider"] == "digitalocean"
        assert resource["provider_resource_id"] == "12345"
        assert resource["ip_address"] == "192.168.1.100"
        assert "created_at" in resource

        # Verify DigitalOcean API was called correctly
        mock_client.create_droplet.assert_called_once()
        call_args = mock_client.create_droplet.call_args
        assert call_args[1]["name"] == "My Test Server"
        assert call_args[1]["ssh_keys"] == []


@pytest.mark.unit
def test_provision_resource_template_not_found(client: TestClient, db: Session) -> None:
    """Test resource provisioning with non-existent template."""
    # Create instructor and workshop (similar setup as above)
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

    # Create student
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

    # Enroll student in workshop
    access_code = workshop_response.json()["access_code"]
    client.post(
        f"/api/v1/workshops/{workshop_id}/join",
        json={"access_code": access_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    # Try to provision with non-existent template
    provision_data = {
        "name": "My Test Server",
        "template_id": 99999,
    }

    response = client.post(
        f"/api/v1/workshops/{workshop_id}/resources",
        json=provision_data,
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert response.status_code == 404
    assert "template not found" in response.json()["detail"].lower()


@pytest.mark.unit
def test_provision_resource_exceeds_user_limit(client: TestClient, db: Session) -> None:
    """Test resource provisioning when user exceeds their limit."""
    # Create instructor and workshop with template
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

    # Create template with limit of 1 instance per user
    template_data = {
        "name": "Limited Server",
        "droplet_size": "s-1vcpu-1gb",
        "droplet_image": "ubuntu-22-04-x64",
        "region": "nyc3",
        "max_instances_per_user": 1,
    }

    template_response = client.post(
        f"/api/v1/workshops/{workshop_id}/templates",
        json=template_data,
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    template_id = template_response.json()["id"]

    # Create student
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

    # Create first resource (manually add to DB to simulate existing resource)
    user = db.query(User).filter(User.email == student_data["email"]).first()
    assert user is not None
    
    template = db.query(ResourceTemplate).filter(ResourceTemplate.id == template_id).first()
    assert template is not None
    
    existing_resource = Resource(
        name="Existing Resource",
        user_id=user.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.ACTIVE,
        provider_resource_id="existing-12345",
    )
    db.add(existing_resource)
    db.commit()

    # Try to create second resource (should fail)
    with patch("cloud_classroom.services.resource_service.SyncDigitalOceanClient"):
        provision_data = {
            "name": "Second Server",
            "template_id": template_id,
        }

        response = client.post(
            f"/api/v1/workshops/{workshop_id}/resources",
            json=provision_data,
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert response.status_code == 400
        assert "exceeds maximum instances" in response.json()["detail"].lower()


@pytest.mark.unit
def test_provision_resource_not_enrolled(client: TestClient, db: Session) -> None:
    """Test resource provisioning when user is not enrolled in workshop."""
    # Create instructor and workshop
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

    # Create template
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

    # Create student but don't enroll
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

    # Try to provision resource without being enrolled
    provision_data = {
        "name": "Unauthorized Server",
        "template_id": template_id,
    }

    response = client.post(
        f"/api/v1/workshops/{workshop_id}/resources",
        json=provision_data,
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert response.status_code == 403
    assert "not enrolled" in response.json()["detail"].lower()


@pytest.mark.unit
def test_list_user_resources(client: TestClient, db: Session) -> None:
    """Test listing user's resources in a workshop."""
    # Create basic setup (instructor, workshop, template, student)
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

    # Enroll student
    access_code = workshop_response.json()["access_code"]
    client.post(
        f"/api/v1/workshops/{workshop_id}/join",
        json={"access_code": access_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    # Create some resources manually in database
    user = db.query(User).filter(User.email == student_data["email"]).first()
    assert user is not None

    resource1 = Resource(
        name="Resource 1",
        user_id=user.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.ACTIVE,
        provider_resource_id="12345",
        ip_address="192.168.1.100",
    )
    resource2 = Resource(
        name="Resource 2",
        user_id=user.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.STOPPED,
        provider_resource_id="67890",
        ip_address="192.168.1.101",
    )
    db.add_all([resource1, resource2])
    db.commit()

    # List resources
    response = client.get(
        f"/api/v1/workshops/{workshop_id}/resources",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert response.status_code == 200
    resources = response.json()
    assert len(resources) == 2
    
    # Check first resource (most recent first due to created_at desc ordering)
    assert resources[0]["name"] == "Resource 2"
    assert resources[0]["status"] == "stopped"
    assert resources[0]["ip_address"] == "192.168.1.101"
    
    # Check second resource  
    assert resources[1]["name"] == "Resource 1"
    assert resources[1]["status"] == "active"
    assert resources[1]["ip_address"] == "192.168.1.100"