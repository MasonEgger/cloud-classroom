"""Comprehensive integration tests for DigitalOcean functionality."""

from unittest.mock import Mock, patch
from datetime import datetime, UTC, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cloud_classroom.models import User, UserRole, Workshop, ResourceTemplate, Resource, ResourceStatus
from cloud_classroom.services.digitalocean_client import DropletInfo


@pytest.mark.integration
def test_complete_digitalocean_workflow(client: TestClient, db: Session) -> None:
    """Test complete DigitalOcean workflow from template creation to resource destruction."""
    
    # Step 1: Create instructor and workshop
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

    # Create workshop with budget
    workshop_data = {
        "title": "Complete DigitalOcean Workshop",
        "description": "Testing the full DigitalOcean integration",
        "mode": "simple",
        "budget_limit": 10000,  # $100.00
        "max_participants": 10,
    }

    workshop_response = client.post(
        "/api/v1/workshops",
        json=workshop_data,
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert workshop_response.status_code == 201
    workshop = workshop_response.json()
    workshop_id = workshop["id"]
    access_code = workshop["access_code"]

    # Step 2: Create resource template with cloud-init
    template_data = {
        "name": "Ubuntu Development Server",
        "description": "Ubuntu 22.04 with development tools",
        "droplet_size": "s-2vcpu-2gb",
        "droplet_image": "ubuntu-22-04-x64",
        "region": "nyc3",
        "user_data": """#!/bin/bash
# Install development tools
apt-get update
apt-get install -y git nodejs npm python3-pip
echo 'Development environment ready!' > /tmp/setup-complete.txt
""",
        "max_instances_per_user": 2,
        "estimated_cost_per_hour": 1200,  # $12.00/hour
    }

    template_response = client.post(
        f"/api/v1/workshops/{workshop_id}/templates",
        json=template_data,
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert template_response.status_code == 201
    template = template_response.json()
    template_id = template["id"]

    # Verify template was created correctly
    assert template["name"] == "Ubuntu Development Server"
    assert template["droplet_size"] == "s-2vcpu-2gb"
    assert template["user_data"] is not None
    assert "development tools" in template["user_data"]

    # Step 3: Create student and enroll in workshop
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
    enroll_response = client.post(
        f"/api/v1/workshops/{workshop_id}/join",
        json={"access_code": access_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert enroll_response.status_code == 201

    # Step 4: Mock DigitalOcean API and provision resource
    with patch("cloud_classroom.services.resource_service.SyncDigitalOceanClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock droplet creation
        mock_droplet_info = DropletInfo(
            id="12345",
            name="student-dev-server",
            ip_address="192.168.1.100",
            status="new",
            size="s-2vcpu-2gb",
            image="ubuntu-22-04-x64",
            region="nyc3",
        )
        mock_client.create_droplet.return_value = mock_droplet_info

        # Provision resource
        provision_data = {
            "name": "student-dev-server",
            "template_id": template_id,
        }

        provision_response = client.post(
            f"/api/v1/workshops/{workshop_id}/resources",
            json=provision_data,
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert provision_response.status_code == 201
        resource = provision_response.json()
        resource_id = resource["id"]

        # Verify resource was created correctly
        assert resource["name"] == "student-dev-server"
        assert resource["status"] == "provisioning"
        assert resource["provider_resource_id"] == "12345"
        assert resource["ip_address"] == "192.168.1.100"

        # Verify DigitalOcean API was called with correct parameters
        mock_client.create_droplet.assert_called_once()
        call_args = mock_client.create_droplet.call_args
        assert call_args[1]["name"] == "student-dev-server"
        # Template object is passed correctly (detailed validation done in unit tests)

    # Step 5: Test status synchronization
    with patch("cloud_classroom.services.resource_service.SyncDigitalOceanClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock droplet is now active
        mock_active_droplet = DropletInfo(
            id="12345",
            name="student-dev-server",
            ip_address="192.168.1.100",
            status="active",
            size="s-2vcpu-2gb",
            image="ubuntu-22-04-x64",
            region="nyc3",
        )
        mock_client.get_droplet.return_value = mock_active_droplet

        # Sync status
        sync_response = client.post(
            f"/api/v1/workshops/{workshop_id}/resources/{resource_id}/sync-status",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert sync_response.status_code == 200
        sync_result = sync_response.json()
        
        assert sync_result["success"] is True
        assert sync_result["old_status"] == "provisioning"
        assert sync_result["new_status"] == "active"

    # Step 6: Test cost calculation
    # Manually update the resource to simulate 2 hours of running
    resource_obj = db.query(Resource).filter(Resource.id == resource_id).first()
    assert resource_obj is not None
    resource_obj.started_at = datetime.now(UTC) - timedelta(hours=2)
    db.commit()

    cost_response = client.post(
        f"/api/v1/workshops/{workshop_id}/resources/{resource_id}/calculate-cost",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert cost_response.status_code == 200
    cost_data = cost_response.json()
    
    # Should be approximately 2 hours * $12.00/hour = $24.00 = 2400 cents
    assert cost_data["total_cost_cents"] >= 2300
    assert cost_data["total_cost_cents"] <= 2500
    assert cost_data["cost_per_hour_cents"] == 1200

    # Step 7: Test workshop cost summary (instructor only)
    summary_response = client.get(
        f"/api/v1/workshops/{workshop_id}/cost-summary",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert summary_response.status_code == 200
    summary = summary_response.json()
    
    assert summary["total_resources_count"] == 1
    assert summary["active_resources_count"] == 1
    assert summary["budget_limit_cents"] == 10000
    assert summary["total_cost_cents"] >= 2300

    # Step 8: Test resource lifecycle management
    with patch("cloud_classroom.services.resource_service.SyncDigitalOceanClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.stop_droplet.return_value = True

        # Stop resource
        stop_response = client.post(
            f"/api/v1/workshops/{workshop_id}/resources/{resource_id}/actions",
            json={"action": "stop"},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert stop_response.status_code == 200
        stop_result = stop_response.json()
        assert stop_result["success"] is True

        mock_client.stop_droplet.assert_called_once_with("12345")

    # Step 9: Test resource monitoring/health status
    health_response = client.get(
        f"/api/v1/workshops/{workshop_id}/health-status",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert health_response.status_code == 200
    health_status = health_response.json()
    
    assert health_status["total_resources"] == 1
    assert health_status["stopped_resources"] == 1  # We stopped it
    assert health_status["active_resources"] == 0

    # Step 10: Test bulk sync all resources
    with patch("cloud_classroom.services.resource_service.SyncDigitalOceanClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock droplet is now active again
        mock_client.get_droplet.return_value = mock_active_droplet

        bulk_sync_response = client.post(
            f"/api/v1/workshops/{workshop_id}/sync-all-resources",
            headers={"Authorization": f"Bearer {instructor_token}"},
        )
        assert bulk_sync_response.status_code == 200
        bulk_sync_result = bulk_sync_response.json()
        
        assert bulk_sync_result["synced_resources"] == 1

    # Step 11: Final cleanup - destroy resource
    with patch("cloud_classroom.services.resource_service.SyncDigitalOceanClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.destroy_droplet.return_value = True

        # Destroy resource
        destroy_response = client.post(
            f"/api/v1/workshops/{workshop_id}/resources/{resource_id}/actions",
            json={"action": "destroy"},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert destroy_response.status_code == 200
        destroy_result = destroy_response.json()
        assert destroy_result["success"] is True

        mock_client.destroy_droplet.assert_called_once_with("12345")

    # Verify final state
    final_resource_response = client.get(
        f"/api/v1/workshops/{workshop_id}/resources/{resource_id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert final_resource_response.status_code == 200
    final_resource = final_resource_response.json()
    assert final_resource["status"] == "destroyed"

    # Verify we can list all user resources
    list_response = client.get(
        f"/api/v1/workshops/{workshop_id}/resources",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert list_response.status_code == 200
    resources_list = list_response.json()
    assert len(resources_list) == 1
    assert resources_list[0]["id"] == resource_id


@pytest.mark.integration
def test_budget_enforcement_prevents_overprovisioning(client: TestClient, db: Session) -> None:
    """Test that budget limits prevent resource overprovisioning."""
    
    # Create instructor and low-budget workshop
    instructor_data = {
        "email": "budget-instructor@example.com",
        "password": "SecurePassword123!",
        "full_name": "Budget Instructor",
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

    # Create workshop with very low budget
    workshop_data = {
        "title": "Budget Limited Workshop",
        "mode": "simple",
        "budget_limit": 500,  # Only $5.00
    }

    workshop_response = client.post(
        "/api/v1/workshops",
        json=workshop_data,
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    workshop_id = workshop_response.json()["id"]
    access_code = workshop_response.json()["access_code"]

    # Create expensive template
    template_data = {
        "name": "Expensive Server",
        "droplet_size": "s-8vcpu-16gb",
        "estimated_cost_per_hour": 10000,  # $100.00/hour - way over budget
    }

    template_response = client.post(
        f"/api/v1/workshops/{workshop_id}/templates",
        json=template_data,
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    template_id = template_response.json()["id"]

    # Create student
    student_data = {
        "email": "budget-student@example.com",
        "password": "SecurePassword123!",
        "full_name": "Budget Student",
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
    client.post(
        f"/api/v1/workshops/{workshop_id}/join",
        json={"access_code": access_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    # Try to provision expensive resource - should fail
    with patch("cloud_classroom.services.resource_service.SyncDigitalOceanClient"):
        provision_data = {
            "name": "Expensive Server",
            "template_id": template_id,
        }

        provision_response = client.post(
            f"/api/v1/workshops/{workshop_id}/resources",
            json=provision_data,
            headers={"Authorization": f"Bearer {student_token}"},
        )

        # Should fail due to budget constraint
        assert provision_response.status_code == 400
        assert "budget" in provision_response.json()["detail"].lower()


@pytest.mark.integration  
def test_error_handling_and_recovery(client: TestClient, db: Session) -> None:
    """Test error handling when DigitalOcean API fails."""
    
    # Create basic setup
    instructor_data = {
        "email": "error-instructor@example.com",
        "password": "SecurePassword123!",
        "full_name": "Error Instructor",
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
        json={"title": "Error Handling Workshop", "mode": "simple"},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    workshop_id = workshop_response.json()["id"]

    template_response = client.post(
        f"/api/v1/workshops/{workshop_id}/templates",
        json={"name": "Error Test Server"},
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    template_id = template_response.json()["id"]

    # Create resource manually with error state
    resource = Resource(
        name="Error Test Resource",
        user_id=instructor.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.ERROR,
        provider_resource_id="error-123",
        error_message="Simulated DigitalOcean API error",
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    # Test that health status correctly identifies error resources
    health_response = client.get(
        f"/api/v1/workshops/{workshop_id}/health-status",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert health_response.status_code == 200
    health_status = health_response.json()
    
    assert health_status["total_resources"] == 1
    assert health_status["error_resources"] == 1
    assert health_status["healthy_percentage"] == 0.0
    
    error_resource = health_status["resource_statuses"][0]
    assert error_resource["status"] == "error"
    assert error_resource["is_healthy"] is False
    assert error_resource["error_message"] == "Simulated DigitalOcean API error"