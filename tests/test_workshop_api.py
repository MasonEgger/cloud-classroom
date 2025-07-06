"""Tests for workshop API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cloud_classroom.models import User, UserRole


@pytest.mark.unit
def test_create_workshop_success(client: TestClient, db: Session) -> None:
    """Test successful workshop creation by instructor."""
    # First, create and login as instructor
    instructor_data = {
        "email": "instructor@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Instructor",
    }

    # Register instructor
    register_response = client.post("/api/v1/auth/register", json=instructor_data)
    assert register_response.status_code == 201

    # Update user role to instructor
    user = db.query(User).filter(User.email == instructor_data["email"]).first()
    assert user is not None
    user.role = UserRole.INSTRUCTOR
    db.commit()

    # Login as instructor
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": instructor_data["email"],
            "password": instructor_data["password"],
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Create workshop
    workshop_data = {
        "title": "Introduction to Cloud Computing",
        "description": "Learn the basics of cloud infrastructure",
        "mode": "simple",
        "max_participants": 20,
        "resource_limit_per_user": 2,
        "budget_limit": 5000,  # $50.00 in cents
        "auto_approve_enrollment": True,
        "allow_resource_creation": True,
        "auto_cleanup": True,
    }

    response = client.post(
        "/api/v1/workshops",
        json=workshop_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == workshop_data["title"]
    assert data["description"] == workshop_data["description"]
    assert data["mode"] == workshop_data["mode"]
    assert data["max_participants"] == workshop_data["max_participants"]
    assert data["instructor_id"] == user.id
    assert "access_code" in data  # Should generate access code
    assert len(data["access_code"]) == 8  # Standard access code length
    assert "id" in data
    assert "created_at" in data


@pytest.mark.unit
def test_create_workshop_unauthorized(client: TestClient) -> None:
    """Test workshop creation without authentication."""
    workshop_data = {
        "title": "Unauthorized Workshop",
        "description": "This should fail",
        "mode": "simple",
    }

    response = client.post("/api/v1/workshops", json=workshop_data)

    # HTTPBearer returns 403 when no credentials provided
    assert response.status_code == 403


@pytest.mark.unit
def test_create_workshop_student_forbidden(client: TestClient) -> None:
    """Test workshop creation by student (should be forbidden)."""
    # Register as student
    student_data = {
        "email": "student@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Student",
    }

    client.post("/api/v1/auth/register", json=student_data)

    # Login as student
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": student_data["email"],
            "password": student_data["password"],
        },
    )
    token = login_response.json()["access_token"]

    # Try to create workshop
    workshop_data = {
        "title": "Student Workshop",
        "description": "This should fail",
        "mode": "simple",
    }

    response = client.post(
        "/api/v1/workshops",
        json=workshop_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


@pytest.mark.unit
def test_get_workshop_success(client: TestClient, db: Session) -> None:
    """Test retrieving a workshop by ID."""
    # Create instructor and workshop first
    instructor_data = {
        "email": "instructor2@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Instructor 2",
    }

    client.post("/api/v1/auth/register", json=instructor_data)

    # Update to instructor role
    user = db.query(User).filter(User.email == instructor_data["email"]).first()
    assert user is not None
    user.role = UserRole.INSTRUCTOR
    db.commit()

    # Login and create workshop
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
        "title": "Test Workshop for Retrieval",
        "description": "A workshop to test GET endpoint",
        "mode": "simple",
    }

    create_response = client.post(
        "/api/v1/workshops",
        json=workshop_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    workshop_id = create_response.json()["id"]

    # Get workshop
    response = client.get(
        f"/api/v1/workshops/{workshop_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == workshop_id
    assert data["title"] == workshop_data["title"]


@pytest.mark.unit
def test_get_workshop_not_found(client: TestClient, db: Session) -> None:
    """Test retrieving a non-existent workshop."""
    # Create instructor
    instructor_data = {
        "email": "instructor3@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Instructor 3",
    }

    client.post("/api/v1/auth/register", json=instructor_data)

    user = db.query(User).filter(User.email == instructor_data["email"]).first()
    assert user is not None
    user.role = UserRole.INSTRUCTOR
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": instructor_data["email"],
            "password": instructor_data["password"],
        },
    )
    token = login_response.json()["access_token"]

    # Try to get non-existent workshop
    response = client.get(
        "/api/v1/workshops/99999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
