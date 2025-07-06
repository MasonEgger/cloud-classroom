"""Tests for workshop enrollment functionality."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cloud_classroom.models import User, UserRole


@pytest.mark.unit
def test_join_workshop_success(client: TestClient, db: Session) -> None:
    """Test successful workshop enrollment."""
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
        "description": "A workshop for testing enrollment",
        "mode": "simple",
        "auto_approve_enrollment": True,
    }

    workshop_response = client.post(
        "/api/v1/workshops",
        json=workshop_data,
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    workshop = workshop_response.json()
    workshop_id = workshop["id"]
    access_code = workshop["access_code"]

    # Create student
    student_data = {
        "email": "student@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Student",
    }
    client.post("/api/v1/auth/register", json=student_data)

    # Login student
    student_login = client.post(
        "/api/v1/auth/login",
        data={
            "username": student_data["email"],
            "password": student_data["password"],
        },
    )
    student_token = student_login.json()["access_token"]

    # Join workshop
    join_data = {"access_code": access_code}
    response = client.post(
        f"/api/v1/workshops/{workshop_id}/join",
        json=join_data,
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert response.status_code == 201
    enrollment = response.json()
    assert enrollment["status"] == "approved"  # Auto-approved
    assert enrollment["workshop_id"] == workshop_id
    assert "enrolled_at" in enrollment
    assert "approved_at" in enrollment


@pytest.mark.unit
def test_join_workshop_invalid_access_code(client: TestClient, db: Session) -> None:
    """Test joining workshop with invalid access code."""
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
    instructor_token = login_response.json()["access_token"]

    workshop_data = {
        "title": "Test Workshop 2",
        "mode": "simple",
    }

    workshop_response = client.post(
        "/api/v1/workshops",
        json=workshop_data,
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

    # Try to join with wrong access code
    join_data = {"access_code": "WRONGCODE"}
    response = client.post(
        f"/api/v1/workshops/{workshop_id}/join",
        json=join_data,
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert response.status_code == 400
    assert "invalid access code" in response.json()["detail"].lower()


@pytest.mark.unit
def test_join_workshop_already_enrolled(client: TestClient, db: Session) -> None:
    """Test joining workshop when already enrolled."""
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
    instructor_token = login_response.json()["access_token"]

    workshop_data = {
        "title": "Test Workshop 3",
        "mode": "simple",
    }

    workshop_response = client.post(
        "/api/v1/workshops",
        json=workshop_data,
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    workshop = workshop_response.json()
    workshop_id = workshop["id"]
    access_code = workshop["access_code"]

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

    # Join workshop first time
    join_data = {"access_code": access_code}
    first_response = client.post(
        f"/api/v1/workshops/{workshop_id}/join",
        json=join_data,
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert first_response.status_code == 201

    # Try to join again
    second_response = client.post(
        f"/api/v1/workshops/{workshop_id}/join",
        json=join_data,
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert second_response.status_code == 400
    assert "already enrolled" in second_response.json()["detail"].lower()


@pytest.mark.unit
def test_join_workshop_full_capacity(client: TestClient, db: Session) -> None:
    """Test joining workshop when it's at full capacity."""
    # Create instructor
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

    # Create workshop with max 1 participant
    workshop_data = {
        "title": "Small Workshop",
        "mode": "simple",
        "max_participants": 1,
    }

    workshop_response = client.post(
        "/api/v1/workshops",
        json=workshop_data,
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    workshop = workshop_response.json()
    workshop_id = workshop["id"]
    access_code = workshop["access_code"]

    # Create and enroll first student
    student1_data = {
        "email": "student4a@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Student 4A",
    }
    client.post("/api/v1/auth/register", json=student1_data)

    student1_login = client.post(
        "/api/v1/auth/login",
        data={
            "username": student1_data["email"],
            "password": student1_data["password"],
        },
    )
    student1_token = student1_login.json()["access_token"]

    # First student joins successfully
    join_data = {"access_code": access_code}
    first_response = client.post(
        f"/api/v1/workshops/{workshop_id}/join",
        json=join_data,
        headers={"Authorization": f"Bearer {student1_token}"},
    )
    assert first_response.status_code == 201

    # Create second student
    student2_data = {
        "email": "student4b@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Student 4B",
    }
    client.post("/api/v1/auth/register", json=student2_data)

    student2_login = client.post(
        "/api/v1/auth/login",
        data={
            "username": student2_data["email"],
            "password": student2_data["password"],
        },
    )
    student2_token = student2_login.json()["access_token"]

    # Second student should be rejected (workshop is full)
    second_response = client.post(
        f"/api/v1/workshops/{workshop_id}/join",
        json=join_data,
        headers={"Authorization": f"Bearer {student2_token}"},
    )

    assert second_response.status_code == 400
    assert "workshop is full" in second_response.json()["detail"].lower()


@pytest.mark.unit
def test_join_workshop_manual_approval(client: TestClient, db: Session) -> None:
    """Test joining workshop with manual approval required."""
    # Create instructor
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

    # Create workshop with manual approval
    workshop_data = {
        "title": "Manual Approval Workshop",
        "mode": "simple",
        "auto_approve_enrollment": False,
    }

    workshop_response = client.post(
        "/api/v1/workshops",
        json=workshop_data,
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    workshop = workshop_response.json()
    workshop_id = workshop["id"]
    access_code = workshop["access_code"]

    # Create student
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

    # Join workshop
    join_data = {"access_code": access_code}
    response = client.post(
        f"/api/v1/workshops/{workshop_id}/join",
        json=join_data,
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert response.status_code == 201
    enrollment = response.json()
    assert enrollment["status"] == "pending"  # Manual approval required
    assert enrollment["workshop_id"] == workshop_id
    assert "enrolled_at" in enrollment
    assert enrollment["approved_at"] is None  # Not yet approved
