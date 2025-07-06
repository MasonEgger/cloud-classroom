"""Tests for cost tracking and budget enforcement."""

from datetime import datetime, UTC, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cloud_classroom.models import User, UserRole, Workshop, ResourceTemplate, Resource, ResourceStatus


@pytest.mark.unit
def test_calculate_resource_cost(client: TestClient, db: Session) -> None:
    """Test calculating cost for a running resource."""
    # Create basic setup
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

    # Create workshop with budget limit
    workshop_data = {
        "title": "Cost Tracking Workshop",
        "mode": "simple",
        "budget_limit": 5000,  # $50.00 in cents
    }

    workshop_response = client.post(
        "/api/v1/workshops",
        json=workshop_data,
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    workshop_id = workshop_response.json()["id"]

    # Create template with known cost
    template_data = {
        "name": "Expensive Server",
        "droplet_size": "s-2vcpu-2gb",
        "droplet_image": "ubuntu-22-04-x64",
        "region": "nyc3",
        "estimated_cost_per_hour": 1200,  # $12.00/hour in cents
    }

    template_response = client.post(
        f"/api/v1/workshops/{workshop_id}/templates",
        json=template_data,
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    template_id = template_response.json()["id"]

    # Create resource that's been running for 2 hours
    user = db.query(User).filter(User.email == instructor_data["email"]).first()
    assert user is not None

    two_hours_ago = datetime.now(UTC) - timedelta(hours=2)
    resource = Resource(
        name="Cost Test Resource",
        user_id=user.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.ACTIVE,
        provider_resource_id="12345",
        started_at=two_hours_ago,
        estimated_cost=0,  # Will be calculated
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    # Get updated cost calculation
    response = client.post(
        f"/api/v1/workshops/{workshop_id}/resources/{resource.id}/calculate-cost",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )

    assert response.status_code == 200
    cost_data = response.json()
    
    # Should be approximately 2 hours * $12.00/hour = $24.00 = 2400 cents
    assert cost_data["total_cost_cents"] >= 2300  # Allow some timing tolerance
    assert cost_data["total_cost_cents"] <= 2500
    assert cost_data["hours_running"] >= 1.9
    assert cost_data["hours_running"] <= 2.1
    assert cost_data["cost_per_hour_cents"] == 1200


@pytest.mark.unit
def test_workshop_budget_enforcement(client: TestClient, db: Session) -> None:
    """Test that budget limits are enforced when provisioning resources."""
    # Create instructor and workshop with low budget
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

    # Create workshop with low budget
    workshop_data = {
        "title": "Budget Limited Workshop",
        "mode": "simple", 
        "budget_limit": 1000,  # $10.00 in cents
    }

    workshop_response = client.post(
        "/api/v1/workshops",
        json=workshop_data,
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    workshop_id = workshop_response.json()["id"]

    # Create expensive template
    template_data = {
        "name": "Expensive Server",
        "droplet_size": "s-8vcpu-16gb",
        "droplet_image": "ubuntu-22-04-x64",
        "region": "nyc3",
        "estimated_cost_per_hour": 5000,  # $50.00/hour in cents
    }

    template_response = client.post(
        f"/api/v1/workshops/{workshop_id}/templates",
        json=template_data,
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    template_id = template_response.json()["id"]

    # Create existing resource that uses most of budget
    existing_resource = Resource(
        name="Existing Resource", 
        user_id=instructor.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.ACTIVE,
        provider_resource_id="existing-123",
        estimated_cost=800,  # $8.00 used already
    )
    db.add(existing_resource)
    db.commit()

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

    # Enroll student
    access_code = workshop_response.json()["access_code"]
    client.post(
        f"/api/v1/workshops/{workshop_id}/join",
        json={"access_code": access_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    # Try to provision resource that would exceed budget
    with patch("cloud_classroom.services.resource_service.SyncDigitalOceanClient"):
        provision_data = {
            "name": "Budget Busting Server",
            "template_id": template_id,
        }

        response = client.post(
            f"/api/v1/workshops/{workshop_id}/resources",
            json=provision_data,
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert response.status_code == 400
        assert "budget" in response.json()["detail"].lower()


@pytest.mark.unit
def test_workshop_cost_summary(client: TestClient, db: Session) -> None:
    """Test getting cost summary for a workshop."""
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

    workshop_response = client.post(
        "/api/v1/workshops", 
        json={
            "title": "Cost Summary Workshop",
            "mode": "simple",
            "budget_limit": 10000,  # $100.00
        },
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    workshop_id = workshop_response.json()["id"]

    # Create template
    template_response = client.post(
        f"/api/v1/workshops/{workshop_id}/templates",
        json={
            "name": "Test Server",
            "estimated_cost_per_hour": 600,  # $6.00/hour
        },
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    template_id = template_response.json()["id"]

    # Create some resources with different costs
    resource1 = Resource(
        name="Resource 1",
        user_id=instructor.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.ACTIVE,
        estimated_cost=1200,  # $12.00
    )
    resource2 = Resource(
        name="Resource 2",
        user_id=instructor.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.STOPPED,
        estimated_cost=800,   # $8.00
    )
    resource3 = Resource(
        name="Resource 3",
        user_id=instructor.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.DESTROYED,
        estimated_cost=600,   # $6.00
    )
    
    db.add_all([resource1, resource2, resource3])
    db.commit()

    # Get cost summary
    response = client.get(
        f"/api/v1/workshops/{workshop_id}/cost-summary",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )

    assert response.status_code == 200
    summary = response.json()
    
    assert summary["total_cost_cents"] == 2600  # $26.00 total
    assert summary["budget_limit_cents"] == 10000  # $100.00 budget
    assert summary["remaining_budget_cents"] == 7400  # $74.00 remaining
    assert summary["budget_used_percentage"] == 26.0  # 26% used
    assert summary["active_resources_count"] == 1
    assert summary["total_resources_count"] == 3


@pytest.mark.unit
def test_update_all_resource_costs(client: TestClient, db: Session) -> None:
    """Test batch updating costs for all workshop resources."""
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
        json={"title": "Batch Update Workshop", "mode": "simple"},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    workshop_id = workshop_response.json()["id"]

    # Create template
    template_response = client.post(
        f"/api/v1/workshops/{workshop_id}/templates",
        json={
            "name": "Test Server",
            "estimated_cost_per_hour": 600,  # $6.00/hour
        },
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    template_id = template_response.json()["id"]

    # Create resources with outdated costs
    one_hour_ago = datetime.now(UTC) - timedelta(hours=1)
    resource1 = Resource(
        name="Resource 1",
        user_id=instructor.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.ACTIVE,
        started_at=one_hour_ago,
        estimated_cost=0,  # Outdated cost
        last_cost_update=one_hour_ago,
    )
    resource2 = Resource(
        name="Resource 2",
        user_id=instructor.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.ACTIVE,
        started_at=one_hour_ago,
        estimated_cost=300,  # Partially updated cost
        last_cost_update=one_hour_ago,
    )
    
    db.add_all([resource1, resource2])
    db.commit()

    # Trigger batch cost update
    response = client.post(
        f"/api/v1/workshops/{workshop_id}/update-costs",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )

    assert response.status_code == 200
    update_result = response.json()
    
    assert update_result["updated_resources"] == 2
    assert "successfully" in update_result["message"]

    # Verify costs were updated
    db.refresh(resource1)
    db.refresh(resource2)
    
    # Should be approximately 1 hour * $6.00/hour = $6.00 = 600 cents
    assert resource1.estimated_cost >= 550
    assert resource1.estimated_cost <= 650
    assert resource2.estimated_cost >= 550
    assert resource2.estimated_cost <= 650