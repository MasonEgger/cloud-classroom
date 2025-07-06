"""Tests for resource template management."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cloud_classroom.models import User, UserRole


@pytest.mark.unit
def test_create_resource_template_success(client: TestClient, db: Session) -> None:
    """Test successful resource template creation."""
    # Create instructor and workshop
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
    token = login_response.json()["access_token"]

    # Create workshop
    workshop_data = {
        "title": "Test Workshop",
        "mode": "simple",
    }

    workshop_response = client.post(
        "/api/v1/workshops",
        json=workshop_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    workshop_id = workshop_response.json()["id"]

    # Create resource template
    template_data = {
        "name": "Basic Ubuntu Server",
        "description": "A basic Ubuntu server for testing",
        "droplet_size": "s-1vcpu-1gb",
        "droplet_image": "ubuntu-22-04-x64",
        "region": "nyc3",
        "max_instances_per_user": 2,
        "estimated_cost_per_hour": 600,  # $6.00 per hour in cents
        "user_data": "#!/bin/bash\napt update && apt install -y htop",
    }

    response = client.post(
        f"/api/v1/workshops/{workshop_id}/resource-templates",
        json=template_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == template_data["name"]
    assert data["description"] == template_data["description"]
    assert data["droplet_size"] == template_data["droplet_size"]
    assert data["workshop_id"] == workshop_id
    assert "id" in data
    assert "created_at" in data


@pytest.mark.unit
def test_list_resource_templates(client: TestClient, db: Session) -> None:
    """Test listing resource templates for a workshop."""
    # Create instructor and workshop
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
    token = login_response.json()["access_token"]

    # Create workshop
    workshop_data = {
        "title": "Test Workshop 2",
        "mode": "simple",
    }

    workshop_response = client.post(
        "/api/v1/workshops",
        json=workshop_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    workshop_id = workshop_response.json()["id"]

    # Create multiple resource templates
    template1_data = {
        "name": "Small Server",
        "droplet_size": "s-1vcpu-1gb",
    }

    template2_data = {
        "name": "Medium Server",
        "droplet_size": "s-2vcpu-2gb",
    }

    client.post(
        f"/api/v1/workshops/{workshop_id}/resource-templates",
        json=template1_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    client.post(
        f"/api/v1/workshops/{workshop_id}/resource-templates",
        json=template2_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    # List templates
    response = client.get(
        f"/api/v1/workshops/{workshop_id}/resource-templates",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    templates = response.json()
    assert len(templates) == 2
    template_names = [t["name"] for t in templates]
    assert "Small Server" in template_names
    assert "Medium Server" in template_names


@pytest.mark.unit
def test_create_resource_template_unauthorized(client: TestClient, db: Session) -> None:
    """Test resource template creation by student (should be forbidden)."""
    # Create instructor and workshop
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
    token = login_response.json()["access_token"]

    workshop_data = {
        "title": "Test Workshop 3",
        "mode": "simple",
    }

    workshop_response = client.post(
        "/api/v1/workshops",
        json=workshop_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    workshop_id = workshop_response.json()["id"]

    # Create student
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

    # Try to create resource template as student
    template_data = {
        "name": "Unauthorized Template",
        "droplet_size": "s-1vcpu-1gb",
    }

    response = client.post(
        f"/api/v1/workshops/{workshop_id}/resource-templates",
        json=template_data,
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert response.status_code == 403


@pytest.mark.unit
def test_create_resource_template_wrong_instructor(client: TestClient, db: Session) -> None:
    """Test resource template creation by different instructor (should be forbidden)."""
    # Create first instructor and workshop
    instructor1_data = {
        "email": "instructor4a@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Instructor 4A",
    }
    client.post("/api/v1/auth/register", json=instructor1_data)

    instructor1 = db.query(User).filter(User.email == instructor1_data["email"]).first()
    assert instructor1 is not None
    instructor1.role = UserRole.INSTRUCTOR
    db.commit()

    login1_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": instructor1_data["email"],
            "password": instructor1_data["password"],
        },
    )
    token1 = login1_response.json()["access_token"]

    workshop_data = {
        "title": "Test Workshop 4",
        "mode": "simple",
    }

    workshop_response = client.post(
        "/api/v1/workshops",
        json=workshop_data,
        headers={"Authorization": f"Bearer {token1}"},
    )
    workshop_id = workshop_response.json()["id"]

    # Create second instructor
    instructor2_data = {
        "email": "instructor4b@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Instructor 4B",
    }
    client.post("/api/v1/auth/register", json=instructor2_data)

    instructor2 = db.query(User).filter(User.email == instructor2_data["email"]).first()
    assert instructor2 is not None
    instructor2.role = UserRole.INSTRUCTOR
    db.commit()

    login2_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": instructor2_data["email"],
            "password": instructor2_data["password"],
        },
    )
    token2 = login2_response.json()["access_token"]

    # Try to create resource template in first instructor's workshop
    template_data = {
        "name": "Unauthorized Template",
        "droplet_size": "s-1vcpu-1gb",
    }

    response = client.post(
        f"/api/v1/workshops/{workshop_id}/resource-templates",
        json=template_data,
        headers={"Authorization": f"Bearer {token2}"},
    )

    assert response.status_code == 403
