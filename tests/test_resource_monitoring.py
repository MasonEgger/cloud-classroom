"""Tests for resource monitoring and status updates."""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cloud_classroom.models import User, UserRole, Workshop, ResourceTemplate, Resource, ResourceStatus
from cloud_classroom.services.digitalocean_client import DropletInfo


@pytest.mark.unit
def test_sync_resource_status_active(client: TestClient, db: Session) -> None:
    """Test syncing resource status when droplet is active."""
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

    workshop_response = client.post(
        "/api/v1/workshops",
        json={"title": "Monitoring Workshop", "mode": "simple"},
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

    # Create resource with outdated status
    resource = Resource(
        name="Test Resource",
        user_id=instructor.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.PROVISIONING,  # Outdated status
        provider_resource_id="12345",
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    # Mock DigitalOcean API response
    with patch("cloud_classroom.services.resource_service.SyncDigitalOceanClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_droplet_info = DropletInfo(
            id="12345",
            name="Test Resource",
            ip_address="192.168.1.100",
            status="active",  # Updated status from DO
            size="s-1vcpu-1gb",
            image="ubuntu-22-04-x64",
            region="nyc3",
        )
        mock_client.get_droplet.return_value = mock_droplet_info

        # Sync resource status
        response = client.post(
            f"/api/v1/workshops/{workshop_id}/resources/{resource.id}/sync-status",
            headers={"Authorization": f"Bearer {instructor_token}"},
        )

        assert response.status_code == 200
        sync_result = response.json()
        
        assert sync_result["success"] is True
        assert sync_result["old_status"] == "provisioning"
        assert sync_result["new_status"] == "active"
        assert sync_result["ip_address"] == "192.168.1.100"

        # Verify database was updated
        db.refresh(resource)
        assert resource.status == ResourceStatus.ACTIVE
        assert resource.ip_address == "192.168.1.100"


@pytest.mark.unit
def test_sync_resource_status_not_found(client: TestClient, db: Session) -> None:
    """Test syncing resource status when droplet no longer exists."""
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
        json={"title": "Monitoring Workshop 2", "mode": "simple"},
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

    # Create resource
    resource = Resource(
        name="Test Resource",
        user_id=instructor.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.ACTIVE,
        provider_resource_id="99999",
        ip_address="192.168.1.100",
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    # Mock DigitalOcean API response (droplet not found)
    with patch("cloud_classroom.services.resource_service.SyncDigitalOceanClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_droplet.return_value = None

        # Sync resource status
        response = client.post(
            f"/api/v1/workshops/{workshop_id}/resources/{resource.id}/sync-status",
            headers={"Authorization": f"Bearer {instructor_token}"},
        )

        assert response.status_code == 200
        sync_result = response.json()
        
        assert sync_result["success"] is True
        assert sync_result["old_status"] == "active"
        assert sync_result["new_status"] == "error"
        assert "not found" in sync_result["message"].lower()

        # Verify database was updated
        db.refresh(resource)
        assert resource.status == ResourceStatus.ERROR
        assert "not found" in resource.error_message.lower()


@pytest.mark.unit
def test_sync_all_workshop_resources(client: TestClient, db: Session) -> None:
    """Test syncing all resources in a workshop."""
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
        json={"title": "Bulk Sync Workshop", "mode": "simple"},
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

    # Create multiple resources
    resource1 = Resource(
        name="Resource 1",
        user_id=instructor.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.PROVISIONING,
        provider_resource_id="11111",
    )
    resource2 = Resource(
        name="Resource 2",
        user_id=instructor.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.ACTIVE,
        provider_resource_id="22222",
        ip_address="192.168.1.100",
    )
    resource3 = Resource(
        name="Resource 3",
        user_id=instructor.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.DESTROYED,  # Should be skipped
        provider_resource_id="33333",
    )
    
    db.add_all([resource1, resource2, resource3])
    db.commit()

    # Mock DigitalOcean API responses
    with patch("cloud_classroom.services.resource_service.SyncDigitalOceanClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        def mock_get_droplet(droplet_id: str):
            if droplet_id == "11111":
                return DropletInfo("11111", "Resource 1", "192.168.1.101", "active", "s-1vcpu-1gb", "ubuntu-22-04-x64", "nyc3")
            elif droplet_id == "22222":
                return DropletInfo("22222", "Resource 2", "192.168.1.102", "off", "s-1vcpu-1gb", "ubuntu-22-04-x64", "nyc3")
            else:
                return None
        
        mock_client.get_droplet.side_effect = mock_get_droplet

        # Sync all resources
        response = client.post(
            f"/api/v1/workshops/{workshop_id}/sync-all-resources",
            headers={"Authorization": f"Bearer {instructor_token}"},
        )

        assert response.status_code == 200
        sync_result = response.json()
        
        assert sync_result["synced_resources"] == 2  # Only active resources are synced
        assert "successfully" in sync_result["message"]

        # Verify database updates
        db.refresh(resource1)
        db.refresh(resource2)
        db.refresh(resource3)
        
        assert resource1.status == ResourceStatus.ACTIVE
        assert resource1.ip_address == "192.168.1.101"
        assert resource2.status == ResourceStatus.STOPPED
        assert resource2.ip_address == "192.168.1.102"
        assert resource3.status == ResourceStatus.DESTROYED  # Unchanged


@pytest.mark.unit
def test_get_resource_health_status(client: TestClient, db: Session) -> None:
    """Test getting health status for workshop resources."""
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
        json={"title": "Health Check Workshop", "mode": "simple"},
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

    # Create resources with different statuses
    resource1 = Resource(
        name="Healthy Resource",
        user_id=instructor.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.ACTIVE,
        provider_resource_id="active-123",
        ip_address="192.168.1.100",
    )
    resource2 = Resource(
        name="Stopped Resource",
        user_id=instructor.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.STOPPED,
        provider_resource_id="stopped-123",
        ip_address="192.168.1.101",
    )
    resource3 = Resource(
        name="Error Resource",
        user_id=instructor.id,
        workshop_id=workshop_id,
        template_id=template_id,
        status=ResourceStatus.ERROR,
        provider_resource_id="error-123",
        error_message="Failed to provision",
    )
    
    db.add_all([resource1, resource2, resource3])
    db.commit()

    # Get health status
    response = client.get(
        f"/api/v1/workshops/{workshop_id}/health-status",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )

    assert response.status_code == 200
    health_status = response.json()
    
    assert health_status["total_resources"] == 3
    assert health_status["active_resources"] == 1
    assert health_status["stopped_resources"] == 1
    assert health_status["error_resources"] == 1
    assert health_status["healthy_percentage"] == 33.3  # 1/3 active
    assert len(health_status["resource_statuses"]) == 3
    
    # Check individual resource statuses
    statuses_by_name = {r["name"]: r for r in health_status["resource_statuses"]}
    
    assert statuses_by_name["Healthy Resource"]["status"] == "active"
    assert statuses_by_name["Healthy Resource"]["is_healthy"] is True
    assert statuses_by_name["Stopped Resource"]["status"] == "stopped"
    assert statuses_by_name["Stopped Resource"]["is_healthy"] is False
    assert statuses_by_name["Error Resource"]["status"] == "error"
    assert statuses_by_name["Error Resource"]["is_healthy"] is False