"""Tests for workshop resource template error handling and permission boundary testing."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cloud_classroom.models import User, Workshop, Enrollment, ResourceTemplate, UserRole


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


def create_workshop_and_template(
    client: TestClient, db: Session, instructor_user: User, instructor_token: str
) -> tuple[int, int]:
    """Helper to create a workshop and resource template."""
    # Create workshop
    workshop_data = {
        "title": "Test Workshop",
        "description": "A test workshop",
        "mode": "simple",
        "max_participants": 10,
        "resource_limit_per_user": 5,
        "budget_limit": 10000,
        "auto_approve_enrollment": True,
        "allow_resource_creation": True,
        "auto_cleanup": True,
    }
    
    headers = {"Authorization": f"Bearer {instructor_token}"}
    response = client.post("/api/v1/workshops/", json=workshop_data, headers=headers)
    assert response.status_code == 201
    workshop_id = response.json()["id"]
    
    # Create resource template
    template_data = {
        "name": "Test Server",
        "droplet_size": "s-1vcpu-1gb",
        "droplet_image": "ubuntu-22-04-x64",
        "region": "nyc3",
        "user_data": "#!/bin/bash\necho 'Hello World'",
    }
    
    response = client.post(f"/api/v1/workshops/{workshop_id}/resource-templates", json=template_data, headers=headers)
    assert response.status_code == 201
    template_id = response.json()["id"]
    
    return workshop_id, template_id


@pytest.mark.unit
def test_list_resource_templates_workshop_not_found(client: TestClient, db: Session) -> None:
    """Test listing resource templates for non-existent workshop."""
    instructor_user, token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/workshops/99999/resource-templates", headers=headers)
    
    assert response.status_code == 404
    assert "Workshop not found" in response.json()["detail"]


@pytest.mark.unit
def test_list_resource_templates_student_not_enrolled(client: TestClient, db: Session) -> None:
    """Test student trying to list resource templates for workshop they're not enrolled in."""
    instructor_user, instructor_token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    student_user, student_token = create_user_and_login(client, db, "student@test.com", UserRole.STUDENT)
    
    workshop_id, _ = create_workshop_and_template(client, db, instructor_user, instructor_token)
    
    # Try to access as student (not enrolled)
    student_headers = {"Authorization": f"Bearer {student_token}"}
    response = client.get(f"/api/v1/workshops/{workshop_id}/resource-templates", headers=student_headers)
    
    assert response.status_code == 403
    assert "Not authorized to view this workshop" in response.json()["detail"]


@pytest.mark.unit
def test_list_resource_templates_student_enrolled_can_access(client: TestClient, db: Session) -> None:
    """Test enrolled student can list resource templates."""
    instructor_user, instructor_token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    student_user, student_token = create_user_and_login(client, db, "student@test.com", UserRole.STUDENT)
    
    workshop_id, template_id = create_workshop_and_template(client, db, instructor_user, instructor_token)
    
    # Create enrollment for student
    enrollment = Enrollment(
        user_id=student_user.id,
        workshop_id=workshop_id,
        status="approved",
    )
    db.add(enrollment)
    db.commit()
    
    # Access as enrolled student
    student_headers = {"Authorization": f"Bearer {student_token}"}
    response = client.get(f"/api/v1/workshops/{workshop_id}/resource-templates", headers=student_headers)
    
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) == 1
    assert templates[0]["id"] == template_id


@pytest.mark.unit
def test_get_resource_template_workshop_not_found(client: TestClient, db: Session) -> None:
    """Test getting resource template for non-existent workshop."""
    instructor_user, token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/workshops/99999/resource-templates/1", headers=headers)
    
    assert response.status_code == 404
    assert "Workshop not found" in response.json()["detail"]


@pytest.mark.unit
def test_get_resource_template_template_not_found(client: TestClient, db: Session) -> None:
    """Test getting non-existent resource template."""
    instructor_user, instructor_token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    
    workshop_id, _ = create_workshop_and_template(client, db, instructor_user, instructor_token)
    
    headers = {"Authorization": f"Bearer {instructor_token}"}
    response = client.get(f"/api/v1/workshops/{workshop_id}/resource-templates/99999", headers=headers)
    
    assert response.status_code == 404
    assert "Resource template not found" in response.json()["detail"]


@pytest.mark.unit
def test_get_resource_template_student_not_enrolled(client: TestClient, db: Session) -> None:
    """Test student trying to get resource template for workshop they're not enrolled in."""
    instructor_user, instructor_token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    student_user, student_token = create_user_and_login(client, db, "student@test.com", UserRole.STUDENT)
    
    workshop_id, template_id = create_workshop_and_template(client, db, instructor_user, instructor_token)
    
    # Try to access as student (not enrolled)
    student_headers = {"Authorization": f"Bearer {student_token}"}
    response = client.get(f"/api/v1/workshops/{workshop_id}/resource-templates/{template_id}", headers=student_headers)
    
    assert response.status_code == 403
    assert "Not authorized to view this workshop" in response.json()["detail"]


@pytest.mark.unit
def test_create_resource_template_workshop_not_found(client: TestClient, db: Session) -> None:
    """Test creating resource template for non-existent workshop."""
    instructor_user, token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    
    template_data = {
        "name": "Test Server",
        "droplet_size": "s-1vcpu-1gb",
        "droplet_image": "ubuntu-22-04-x64",
        "region": "nyc3",
        "user_data": "#!/bin/bash\necho 'Hello World'",
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/workshops/99999/resource-templates", json=template_data, headers=headers)
    
    assert response.status_code == 404
    assert "Workshop not found" in response.json()["detail"]


@pytest.mark.unit
def test_create_resource_template_wrong_instructor(client: TestClient, db: Session) -> None:
    """Test instructor trying to create resource template for another instructor's workshop."""
    instructor1_user, instructor1_token = create_user_and_login(client, db, "instructor1@test.com", UserRole.INSTRUCTOR)
    instructor2_user, instructor2_token = create_user_and_login(client, db, "instructor2@test.com", UserRole.INSTRUCTOR)
    
    workshop_id, _ = create_workshop_and_template(client, db, instructor1_user, instructor1_token)
    
    template_data = {
        "name": "Unauthorized Template",
        "droplet_size": "s-1vcpu-1gb",
        "droplet_image": "ubuntu-22-04-x64",
        "region": "nyc3",
        "user_data": "#!/bin/bash\necho 'Unauthorized'",
    }
    
    # Try to create template as instructor2
    instructor2_headers = {"Authorization": f"Bearer {instructor2_token}"}
    response = client.post(f"/api/v1/workshops/{workshop_id}/resource-templates", json=template_data, headers=instructor2_headers)
    
    assert response.status_code == 403
    assert "Not authorized to modify this workshop" in response.json()["detail"]


@pytest.mark.unit
def test_update_resource_template_workshop_not_found(client: TestClient, db: Session) -> None:
    """Test updating resource template for non-existent workshop."""
    instructor_user, token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    
    update_data = {
        "name": "Updated Template",
        "droplet_size": "s-2vcpu-2gb",
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.put("/api/v1/workshops/99999/resource-templates/1", json=update_data, headers=headers)
    
    assert response.status_code == 404
    assert "Workshop not found" in response.json()["detail"]


@pytest.mark.unit
def test_update_resource_template_template_not_found(client: TestClient, db: Session) -> None:
    """Test updating non-existent resource template."""
    instructor_user, instructor_token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    
    workshop_id, _ = create_workshop_and_template(client, db, instructor_user, instructor_token)
    
    update_data = {
        "name": "Updated Template",
        "droplet_size": "s-2vcpu-2gb",
    }
    
    headers = {"Authorization": f"Bearer {instructor_token}"}
    response = client.put(f"/api/v1/workshops/{workshop_id}/resource-templates/99999", json=update_data, headers=headers)
    
    assert response.status_code == 404
    assert "Resource template not found" in response.json()["detail"]


@pytest.mark.unit
def test_update_resource_template_wrong_instructor(client: TestClient, db: Session) -> None:
    """Test instructor trying to update resource template for another instructor's workshop."""
    instructor1_user, instructor1_token = create_user_and_login(client, db, "instructor1@test.com", UserRole.INSTRUCTOR)
    instructor2_user, instructor2_token = create_user_and_login(client, db, "instructor2@test.com", UserRole.INSTRUCTOR)
    
    workshop_id, template_id = create_workshop_and_template(client, db, instructor1_user, instructor1_token)
    
    update_data = {
        "name": "Unauthorized Update",
        "droplet_size": "s-2vcpu-2gb",
    }
    
    # Try to update template as instructor2
    instructor2_headers = {"Authorization": f"Bearer {instructor2_token}"}
    response = client.put(f"/api/v1/workshops/{workshop_id}/resource-templates/{template_id}", json=update_data, headers=instructor2_headers)
    
    assert response.status_code == 403
    assert "Not authorized to modify this workshop" in response.json()["detail"]


@pytest.mark.unit
def test_delete_resource_template_workshop_not_found(client: TestClient, db: Session) -> None:
    """Test deleting resource template for non-existent workshop."""
    instructor_user, token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.delete("/api/v1/workshops/99999/resource-templates/1", headers=headers)
    
    assert response.status_code == 404
    assert "Workshop not found" in response.json()["detail"]


@pytest.mark.unit
def test_delete_resource_template_template_not_found(client: TestClient, db: Session) -> None:
    """Test deleting non-existent resource template."""
    instructor_user, instructor_token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    
    workshop_id, _ = create_workshop_and_template(client, db, instructor_user, instructor_token)
    
    headers = {"Authorization": f"Bearer {instructor_token}"}
    response = client.delete(f"/api/v1/workshops/{workshop_id}/resource-templates/99999", headers=headers)
    
    assert response.status_code == 404
    assert "Resource template not found" in response.json()["detail"]


@pytest.mark.unit
def test_delete_resource_template_wrong_instructor(client: TestClient, db: Session) -> None:
    """Test instructor trying to delete resource template for another instructor's workshop."""
    instructor1_user, instructor1_token = create_user_and_login(client, db, "instructor1@test.com", UserRole.INSTRUCTOR)
    instructor2_user, instructor2_token = create_user_and_login(client, db, "instructor2@test.com", UserRole.INSTRUCTOR)
    
    workshop_id, template_id = create_workshop_and_template(client, db, instructor1_user, instructor1_token)
    
    # Try to delete template as instructor2
    instructor2_headers = {"Authorization": f"Bearer {instructor2_token}"}
    response = client.delete(f"/api/v1/workshops/{workshop_id}/resource-templates/{template_id}", headers=instructor2_headers)
    
    assert response.status_code == 403
    assert "Not authorized to modify this workshop" in response.json()["detail"]


@pytest.mark.unit
def test_admin_can_access_any_workshop_templates(client: TestClient, db: Session) -> None:
    """Test admin can access resource templates for any workshop."""
    instructor_user, instructor_token = create_user_and_login(client, db, "instructor@test.com", UserRole.INSTRUCTOR)
    admin_user, admin_token = create_user_and_login(client, db, "admin@test.com", UserRole.ADMIN)
    
    workshop_id, template_id = create_workshop_and_template(client, db, instructor_user, instructor_token)
    
    # Access as admin
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get(f"/api/v1/workshops/{workshop_id}/resource-templates", headers=admin_headers)
    
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) == 1
    assert templates[0]["id"] == template_id