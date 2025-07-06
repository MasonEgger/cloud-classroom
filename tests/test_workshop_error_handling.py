"""Tests for workshop API error handling and edge cases."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cloud_classroom.models import User, Workshop, Enrollment, UserRole, WorkshopMode


def create_user_and_login(client: TestClient, db: Session, email: str, role: UserRole) -> tuple[User, str]:
    """Helper to create a user and get authentication token."""
    # Register user
    user_data = {
        "email": email,
        "password": "SecurePassword123!",
        "full_name": f"Test {role.value}",
    }
    
    register_response = client.post("/api/v1/auth/register", json=user_data)
    assert register_response.status_code == 201
    
    # Update role if needed
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    if user.role != role:
        user.role = role
        db.commit()
    
    # Login to get token
    login_data = {"username": email, "password": "SecurePassword123!"}
    login_response = client.post("/api/v1/auth/login", data=login_data)
    assert login_response.status_code == 200
    
    token = login_response.json()["access_token"]
    return user, token


@pytest.mark.unit
def test_access_code_generation_failure(client: TestClient, db: Session) -> None:
    """Test workshop creation when access code generation fails."""
    instructor_user, token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    
    workshop_data = {
        "title": "Test Workshop",
        "description": "A test workshop",
        "mode": "simple",
        "max_participants": 10,
        "resource_limit_per_user": 5,
        "budget_limit": 10000,  # Budget in cents ($100.00)
        "auto_approve_enrollment": True,
        "allow_resource_creation": True,
        "auto_cleanup": True,
    }
    
    # Create a workshop with access code "AAAAAA" to create a collision
    existing_workshop = Workshop(
        title="Existing Workshop",
        description="Existing workshop",
        access_code="AAAAAA",
        mode=WorkshopMode.SIMPLE,
        max_participants=10,
        resource_limit_per_user=5,
        budget_limit=10000,
        instructor_id=instructor_user.id,
        auto_approve_enrollment=True,
        allow_resource_creation=True,
        auto_cleanup=True,
    )
    db.add(existing_workshop)
    db.commit()
    
    # Mock random.choices to always return "AAAAAA" to force collision
    # Since max_attempts is a local variable, we need to patch the function to use fewer attempts
    headers = {"Authorization": f"Bearer {token}"}
    
    with patch("cloud_classroom.api.v1.workshops.generate_access_code", return_value="AAAAAA"):
        # Now try to create another workshop - should fail since generate_access_code always returns "AAAAAA"
        # which already exists in the database, and all 10 attempts will return the same code
        response = client.post("/api/v1/workshops/", json=workshop_data, headers=headers)
        
        assert response.status_code == 500
        assert "Failed to generate unique access code" in response.json()["detail"]


@pytest.mark.unit
def test_get_workshop_student_not_enrolled(client: TestClient, db: Session) -> None:
    """Test student trying to access workshop they're not enrolled in."""
    instructor_user, instructor_token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    student_user, student_token = create_user_and_login(client, db, "student@test.com", UserRole.STUDENT)
    
    # Create a workshop
    workshop_data = {
        "title": "Test Workshop",
        "description": "A test workshop",
        "mode": "simple",
        "max_participants": 10,
        "resource_limit_per_user": 5,
        "budget_limit": 10000,  # Budget in cents ($100.00)
        "auto_approve_enrollment": True,
        "allow_resource_creation": True,
        "auto_cleanup": True,
    }
    
    headers = {"Authorization": f"Bearer {instructor_token}"}
    response = client.post("/api/v1/workshops/", json=workshop_data, headers=headers)
    assert response.status_code == 201
    workshop_id = response.json()["id"]
    
    # Try to access as student (not enrolled)
    student_headers = {"Authorization": f"Bearer {student_token}"}
    response = client.get(f"/api/v1/workshops/{workshop_id}", headers=student_headers)
    
    assert response.status_code == 403
    assert "Not authorized to view this workshop" in response.json()["detail"]


@pytest.mark.unit
def test_get_workshop_other_instructor(client: TestClient, db: Session) -> None:
    """Test instructor trying to access another instructor's workshop."""
    instructor1_user, instructor1_token = create_user_and_login(client, db, "instructor1@test.com", UserRole.INSTRUCTOR)
    instructor2_user, instructor2_token = create_user_and_login(client, db, "instructor2@test.com", UserRole.INSTRUCTOR)
    
    # Create a workshop as instructor1
    workshop_data = {
        "title": "Test Workshop",
        "description": "A test workshop",
        "mode": "simple",
        "max_participants": 10,
        "resource_limit_per_user": 5,
        "budget_limit": 10000,  # Budget in cents ($100.00)
        "auto_approve_enrollment": True,
        "allow_resource_creation": True,
        "auto_cleanup": True,
    }
    
    headers = {"Authorization": f"Bearer {instructor1_token}"}
    response = client.post("/api/v1/workshops/", json=workshop_data, headers=headers)
    assert response.status_code == 201
    workshop_id = response.json()["id"]
    
    # Try to access as instructor2 (different instructor)
    instructor2_headers = {"Authorization": f"Bearer {instructor2_token}"}
    response = client.get(f"/api/v1/workshops/{workshop_id}", headers=instructor2_headers)
    
    assert response.status_code == 403
    assert "Not authorized to view this workshop" in response.json()["detail"]


@pytest.mark.unit
def test_admin_can_access_any_workshop(client: TestClient, db: Session) -> None:
    """Test admin can access any workshop."""
    instructor_user, instructor_token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    admin_user, admin_token = create_user_and_login(client, db, "admin@test.com", UserRole.ADMIN)
    
    # Create a workshop as instructor
    workshop_data = {
        "title": "Test Workshop",
        "description": "A test workshop",
        "mode": "simple",
        "max_participants": 10,
        "resource_limit_per_user": 5,
        "budget_limit": 10000,  # Budget in cents ($100.00)
        "auto_approve_enrollment": True,
        "allow_resource_creation": True,
        "auto_cleanup": True,
    }
    
    headers = {"Authorization": f"Bearer {instructor_token}"}
    response = client.post("/api/v1/workshops/", json=workshop_data, headers=headers)
    assert response.status_code == 201
    workshop_id = response.json()["id"]
    
    # Access as admin
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get(f"/api/v1/workshops/{workshop_id}", headers=admin_headers)
    
    assert response.status_code == 200
    assert response.json()["id"] == workshop_id


@pytest.mark.unit
def test_student_can_access_enrolled_workshop(client: TestClient, db: Session) -> None:
    """Test student can access workshop they're enrolled in."""
    instructor_user, instructor_token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    student_user, student_token = create_user_and_login(client, db, "student@test.com", UserRole.STUDENT)
    
    # Create a workshop
    workshop_data = {
        "title": "Test Workshop",
        "description": "A test workshop",
        "mode": "simple",
        "max_participants": 10,
        "resource_limit_per_user": 5,
        "budget_limit": 10000,  # Budget in cents ($100.00)
        "auto_approve_enrollment": True,
        "allow_resource_creation": True,
        "auto_cleanup": True,
    }
    
    headers = {"Authorization": f"Bearer {instructor_token}"}
    response = client.post("/api/v1/workshops/", json=workshop_data, headers=headers)
    assert response.status_code == 201
    workshop_id = response.json()["id"]
    
    # Create an approved enrollment for the student
    enrollment = Enrollment(
        user_id=student_user.id,
        workshop_id=workshop_id,
        status="approved",
    )
    db.add(enrollment)
    db.commit()
    
    # Access as student (enrolled)
    student_headers = {"Authorization": f"Bearer {student_token}"}
    response = client.get(f"/api/v1/workshops/{workshop_id}", headers=student_headers)
    
    assert response.status_code == 200
    assert response.json()["id"] == workshop_id


@pytest.mark.unit
def test_update_workshop_not_found(client: TestClient, db: Session) -> None:
    """Test updating a non-existent workshop."""
    instructor_user, token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    
    update_data = {
        "title": "Updated Workshop",
        "description": "Updated description",
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.put("/api/v1/workshops/99999", json=update_data, headers=headers)
    
    assert response.status_code == 404
    assert "Workshop not found" in response.json()["detail"]


@pytest.mark.unit
def test_update_workshop_wrong_instructor(client: TestClient, db: Session) -> None:
    """Test instructor trying to update another instructor's workshop."""
    instructor1_user, instructor1_token = create_user_and_login(client, db, "instructor1@test.com", UserRole.INSTRUCTOR)
    instructor2_user, instructor2_token = create_user_and_login(client, db, "instructor2@test.com", UserRole.INSTRUCTOR)
    
    # Create a workshop as instructor1
    workshop_data = {
        "title": "Test Workshop",
        "description": "A test workshop",
        "mode": "simple",
        "max_participants": 10,
        "resource_limit_per_user": 5,
        "budget_limit": 10000,  # Budget in cents ($100.00)
        "auto_approve_enrollment": True,
        "allow_resource_creation": True,
        "auto_cleanup": True,
    }
    
    headers = {"Authorization": f"Bearer {instructor1_token}"}
    response = client.post("/api/v1/workshops/", json=workshop_data, headers=headers)
    assert response.status_code == 201
    workshop_id = response.json()["id"]
    
    # Try to update as instructor2
    update_data = {
        "title": "Updated Workshop",
        "description": "Updated description",
    }
    
    instructor2_headers = {"Authorization": f"Bearer {instructor2_token}"}
    response = client.put(f"/api/v1/workshops/{workshop_id}", json=update_data, headers=instructor2_headers)
    
    assert response.status_code == 403
    assert "Not authorized to update this workshop" in response.json()["detail"]


@pytest.mark.unit
def test_delete_workshop_not_found(client: TestClient, db: Session) -> None:
    """Test deleting a non-existent workshop."""
    instructor_user, token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.delete("/api/v1/workshops/99999", headers=headers)
    
    assert response.status_code == 404
    assert "Workshop not found" in response.json()["detail"]


@pytest.mark.unit
def test_delete_workshop_wrong_instructor(client: TestClient, db: Session) -> None:
    """Test instructor trying to delete another instructor's workshop."""
    instructor1_user, instructor1_token = create_user_and_login(client, db, "instructor1@test.com", UserRole.INSTRUCTOR)
    instructor2_user, instructor2_token = create_user_and_login(client, db, "instructor2@test.com", UserRole.INSTRUCTOR)
    
    # Create a workshop as instructor1
    workshop_data = {
        "title": "Test Workshop",
        "description": "A test workshop",
        "mode": "simple",
        "max_participants": 10,
        "resource_limit_per_user": 5,
        "budget_limit": 10000,  # Budget in cents ($100.00)
        "auto_approve_enrollment": True,
        "allow_resource_creation": True,
        "auto_cleanup": True,
    }
    
    headers = {"Authorization": f"Bearer {instructor1_token}"}
    response = client.post("/api/v1/workshops/", json=workshop_data, headers=headers)
    assert response.status_code == 201
    workshop_id = response.json()["id"]
    
    # Try to delete as instructor2
    instructor2_headers = {"Authorization": f"Bearer {instructor2_token}"}
    response = client.delete(f"/api/v1/workshops/{workshop_id}", headers=instructor2_headers)
    
    assert response.status_code == 403
    assert "Not authorized to delete this workshop" in response.json()["detail"]


@pytest.mark.unit
def test_workshop_list_filtering_student_no_enrollments(client: TestClient, db: Session) -> None:
    """Test student with no enrollments sees empty workshop list."""
    student_user, token = create_user_and_login(client, db, "student@test.com", UserRole.STUDENT)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/workshops/", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["workshops"]) == 0


@pytest.mark.unit
def test_workshop_list_filtering_student_with_pending_enrollment(client: TestClient, db: Session) -> None:
    """Test student with pending enrollment doesn't see workshop in list."""
    instructor_user, instructor_token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    student_user, student_token = create_user_and_login(client, db, "student@test.com", UserRole.STUDENT)
    
    # Create a workshop
    workshop_data = {
        "title": "Test Workshop",
        "description": "A test workshop",
        "mode": "simple",
        "max_participants": 10,
        "resource_limit_per_user": 5,
        "budget_limit": 10000,  # Budget in cents ($100.00)
        "auto_approve_enrollment": True,
        "allow_resource_creation": True,
        "auto_cleanup": True,
    }
    
    headers = {"Authorization": f"Bearer {instructor_token}"}
    response = client.post("/api/v1/workshops/", json=workshop_data, headers=headers)
    assert response.status_code == 201
    workshop_id = response.json()["id"]
    
    # Create a pending enrollment for the student
    enrollment = Enrollment(
        user_id=student_user.id,
        workshop_id=workshop_id,
        status="pending",
    )
    db.add(enrollment)
    db.commit()
    
    # Check workshop list as student
    student_headers = {"Authorization": f"Bearer {student_token}"}
    response = client.get("/api/v1/workshops/", headers=student_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["workshops"]) == 0


@pytest.mark.unit
def test_workshop_list_filtering_instructor_empty_list(client: TestClient, db: Session) -> None:
    """Test instructor with no workshops sees empty list."""
    instructor_user, token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/workshops/", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["workshops"]) == 0