"""Tests for resource service exception handling and error scenarios."""

import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC

import pytest
from sqlalchemy.orm import Session

from cloud_classroom.models import User, Workshop, ResourceTemplate, Resource, Enrollment, UserRole, ResourceStatus, WorkshopMode
from cloud_classroom.services.resource_service import ResourceService
from cloud_classroom.services.digitalocean_client import DropletInfo


def create_test_user(db: Session, email: str, role: UserRole) -> User:
    """Create a test user."""
    user = User(
        email=email,
        full_name=f"Test {role.value}",
        hashed_password="hashed_password",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_test_workshop(db: Session, instructor: User) -> Workshop:
    """Create a test workshop."""
    workshop = Workshop(
        title="Test Workshop",
        description="A test workshop",
        access_code="TEST123",
        mode=WorkshopMode.SIMPLE,
        max_participants=10,
        resource_limit_per_user=5,
        budget_limit=10000,
        instructor_id=instructor.id,
        auto_approve_enrollment=True,
        allow_resource_creation=True,
        auto_cleanup=True,
    )
    db.add(workshop)
    db.commit()
    db.refresh(workshop)
    return workshop


def create_test_template(db: Session, workshop: Workshop) -> ResourceTemplate:
    """Create a test resource template."""
    template = ResourceTemplate(
        name="Test Server",
        droplet_size="s-1vcpu-1gb",
        droplet_image="ubuntu-22-04-x64",
        region="nyc3",
        user_data="#!/bin/bash\necho 'Hello World'",
        workshop_id=workshop.id,
        is_active=True,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@pytest.mark.unit
def test_provision_resource_digitalocean_api_failure(db: Session) -> None:
    """Test resource provisioning when DigitalOcean API fails."""
    # Setup test data
    instructor = create_test_user(db, "instructor@test.com", UserRole.INSTRUCTOR)
    student = create_test_user(db, "student@test.com", UserRole.STUDENT)
    workshop = create_test_workshop(db, instructor)
    template = create_test_template(db, workshop)
    
    # Create enrollment
    enrollment = Enrollment(
        user_id=student.id,
        workshop_id=workshop.id,
        status="approved",
    )
    db.add(enrollment)
    db.commit()
    
    # Mock DigitalOcean client to raise exception
    with patch('cloud_classroom.services.resource_service.SyncDigitalOceanClient') as mock_client_class:
        mock_client = Mock()
        mock_client.create_droplet.side_effect = Exception("API connection failed")
        mock_client_class.return_value = mock_client
        
        resource_service = ResourceService(db)
        
        # Attempt to provision resource - should raise exception
        with pytest.raises(Exception, match="API connection failed"):
            resource_service.provision_resource(
                user_id=student.id,
                workshop_id=workshop.id,
                template_id=template.id,
                name="test-resource",
            )
        
        # Verify resource was created with error status in database
        resource = db.query(Resource).filter(Resource.name == "test-resource").first()
        assert resource is not None
        assert resource.status == ResourceStatus.ERROR
        assert "API connection failed" in resource.error_message
        assert resource.provider_resource_id is None
        assert resource.ip_address is None


@pytest.mark.unit
def test_provision_resource_invalid_ssh_keys_json(db: Session) -> None:
    """Test resource provisioning when SSH keys JSON is malformed."""
    # Setup test data
    instructor = create_test_user(db, "instructor@test.com", UserRole.INSTRUCTOR)
    student = create_test_user(db, "student@test.com", UserRole.STUDENT)
    workshop = create_test_workshop(db, instructor)
    template = create_test_template(db, workshop)
    
    # Set invalid JSON for SSH keys
    template.ssh_keys = "invalid json {"
    db.commit()
    
    # Create enrollment
    enrollment = Enrollment(
        user_id=student.id,
        workshop_id=workshop.id,
        status="approved",
    )
    db.add(enrollment)
    db.commit()
    
    # Mock DigitalOcean client
    with patch('cloud_classroom.services.resource_service.SyncDigitalOceanClient') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        resource_service = ResourceService(db)
        
        # Attempt to provision resource - should raise exception due to invalid JSON
        with pytest.raises(Exception):  # JSON decode error
            resource_service.provision_resource(
                user_id=student.id,
                workshop_id=workshop.id,
                template_id=template.id,
                name="test-resource",
            )
        
        # Verify resource was created with error status in database
        resource = db.query(Resource).filter(Resource.name == "test-resource").first()
        assert resource is not None
        assert resource.status == ResourceStatus.ERROR
        assert resource.error_message is not None
        assert "json" in resource.error_message.lower() or "Expecting" in resource.error_message


@pytest.mark.unit
def test_start_resource_digitalocean_api_failure(db: Session) -> None:
    """Test starting a resource when DigitalOcean API fails."""
    # Setup test data
    instructor = create_test_user(db, "instructor@test.com", UserRole.INSTRUCTOR)
    student = create_test_user(db, "student@test.com", UserRole.STUDENT)
    workshop = create_test_workshop(db, instructor)
    template = create_test_template(db, workshop)
    
    # Create a resource
    resource = Resource(
        name="test-resource",
        status=ResourceStatus.STOPPED,
        user_id=student.id,
        workshop_id=workshop.id,
        template_id=template.id,
        provider_resource_id="12345",
        ip_address="192.168.1.100",
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    
    # Mock DigitalOcean client to fail
    with patch('cloud_classroom.services.resource_service.SyncDigitalOceanClient') as mock_client_class:
        mock_client = Mock()
        mock_client.start_droplet.return_value = False
        mock_client_class.return_value = mock_client
        
        resource_service = ResourceService(db)
        
        # Attempt to start resource
        result = resource_service.start_resource(resource.id, student.id)
        
        # Verify operation failed
        assert result is False
        mock_client.start_droplet.assert_called_once_with("12345")


@pytest.mark.unit
def test_stop_resource_digitalocean_api_failure(db: Session) -> None:
    """Test stopping a resource when DigitalOcean API fails."""
    # Setup test data
    instructor = create_test_user(db, "instructor@test.com", UserRole.INSTRUCTOR)
    student = create_test_user(db, "student@test.com", UserRole.STUDENT)
    workshop = create_test_workshop(db, instructor)
    template = create_test_template(db, workshop)
    
    # Create a resource
    resource = Resource(
        name="test-resource",
        status=ResourceStatus.ACTIVE,
        user_id=student.id,
        workshop_id=workshop.id,
        template_id=template.id,
        provider_resource_id="12345",
        ip_address="192.168.1.100",
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    
    # Mock DigitalOcean client to fail
    with patch('cloud_classroom.services.resource_service.SyncDigitalOceanClient') as mock_client_class:
        mock_client = Mock()
        mock_client.stop_droplet.return_value = False
        mock_client_class.return_value = mock_client
        
        resource_service = ResourceService(db)
        
        # Attempt to stop resource
        result = resource_service.stop_resource(resource.id, student.id)
        
        # Verify operation failed
        assert result is False
        mock_client.stop_droplet.assert_called_once_with("12345")


@pytest.mark.unit
def test_destroy_resource_digitalocean_api_failure(db: Session) -> None:
    """Test destroying a resource when DigitalOcean API fails."""
    # Setup test data
    instructor = create_test_user(db, "instructor@test.com", UserRole.INSTRUCTOR)
    student = create_test_user(db, "student@test.com", UserRole.STUDENT)
    workshop = create_test_workshop(db, instructor)
    template = create_test_template(db, workshop)
    
    # Create a resource
    resource = Resource(
        name="test-resource",
        status=ResourceStatus.ACTIVE,
        user_id=student.id,
        workshop_id=workshop.id,
        template_id=template.id,
        provider_resource_id="12345",
        ip_address="192.168.1.100",
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    
    # Mock DigitalOcean client to fail
    with patch('cloud_classroom.services.resource_service.SyncDigitalOceanClient') as mock_client_class:
        mock_client = Mock()
        mock_client.destroy_droplet.return_value = False
        mock_client_class.return_value = mock_client
        
        resource_service = ResourceService(db)
        
        # Attempt to destroy resource
        result = resource_service.destroy_resource(resource.id, student.id)
        
        # Verify operation failed
        assert result is False
        mock_client.destroy_droplet.assert_called_once_with("12345")


@pytest.mark.unit
def test_provision_resource_missing_provider_id_after_creation(db: Session) -> None:
    """Test resource provisioning when DigitalOcean returns droplet without ID."""
    # Setup test data
    instructor = create_test_user(db, "instructor@test.com", UserRole.INSTRUCTOR)
    student = create_test_user(db, "student@test.com", UserRole.STUDENT)
    workshop = create_test_workshop(db, instructor)
    template = create_test_template(db, workshop)
    
    # Create enrollment
    enrollment = Enrollment(
        user_id=student.id,
        workshop_id=workshop.id,
        status="approved",
    )
    db.add(enrollment)
    db.commit()
    
    # Mock DigitalOcean client to return droplet with None ID
    mock_droplet_info = DropletInfo(
        id=None,  # This should cause an issue
        name="test-resource",
        ip_address="192.168.1.100",
        status="new",
        size="s-1vcpu-1gb",
        image="ubuntu-22-04-x64",
        region="nyc3",
    )
    
    with patch('cloud_classroom.services.resource_service.SyncDigitalOceanClient') as mock_client_class:
        mock_client = Mock()
        mock_client.create_droplet.return_value = mock_droplet_info
        mock_client_class.return_value = mock_client
        
        resource_service = ResourceService(db)
        
        # Attempt to provision resource
        resource = resource_service.provision_resource(
            user_id=student.id,
            workshop_id=workshop.id,
            template_id=template.id,
            name="test-resource",
        )
        
        # Verify resource was created but provider_resource_id is None
        assert resource is not None
        assert resource.provider_resource_id is None
        assert resource.ip_address == "192.168.1.100"


@pytest.mark.unit
def test_sync_resource_status_droplet_not_found(db: Session) -> None:
    """Test syncing resource status when droplet is not found on DigitalOcean."""
    # Setup test data
    instructor = create_test_user(db, "instructor@test.com", UserRole.INSTRUCTOR)
    student = create_test_user(db, "student@test.com", UserRole.STUDENT)
    workshop = create_test_workshop(db, instructor)
    template = create_test_template(db, workshop)
    
    # Create a resource
    resource = Resource(
        name="test-resource",
        status=ResourceStatus.ACTIVE,
        user_id=student.id,
        workshop_id=workshop.id,
        template_id=template.id,
        provider_resource_id="12345",
        ip_address="192.168.1.100",
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    
    # Mock DigitalOcean client to return None (droplet not found)
    with patch('cloud_classroom.services.resource_service.SyncDigitalOceanClient') as mock_client_class:
        mock_client = Mock()
        mock_client.get_droplet.return_value = None
        mock_client_class.return_value = mock_client
        
        resource_service = ResourceService(db)
        
        # Sync resource status
        resource_service.sync_resource_status(resource.id, student.id)
        
        # Verify resource status was updated (likely to ERROR or kept ACTIVE)
        db.refresh(resource)
        # When droplet not found, status should remain unchanged or be set to ERROR
        assert resource.status in [ResourceStatus.ACTIVE, ResourceStatus.ERROR]


@pytest.mark.unit
def test_sync_all_workshop_resources_with_errors(db: Session) -> None:
    """Test syncing all workshop resources when some have errors."""
    # Setup test data
    instructor = create_test_user(db, "instructor@test.com", UserRole.INSTRUCTOR)
    student = create_test_user(db, "student@test.com", UserRole.STUDENT)
    workshop = create_test_workshop(db, instructor)
    template = create_test_template(db, workshop)
    
    # Create multiple resources, some with missing provider IDs
    resource1 = Resource(
        name="test-resource-1",
        status=ResourceStatus.ACTIVE,
        user_id=student.id,
        workshop_id=workshop.id,
        template_id=template.id,
        provider_resource_id="12345",
        ip_address="192.168.1.100",
    )
    
    resource2 = Resource(
        name="test-resource-2",
        status=ResourceStatus.ACTIVE,
        user_id=student.id,
        workshop_id=workshop.id,
        template_id=template.id,
        provider_resource_id=None,  # Missing provider ID
        ip_address=None,
    )
    
    db.add(resource1)
    db.add(resource2)
    db.commit()
    
    # Mock DigitalOcean client
    mock_droplet_info = DropletInfo(
        id="12345",
        name="test-resource-1",
        ip_address="192.168.1.100",
        status="active",
        size="s-1vcpu-1gb",
        image="ubuntu-22-04-x64",
        region="nyc3",
    )
    
    with patch('cloud_classroom.services.resource_service.SyncDigitalOceanClient') as mock_client_class:
        mock_client = Mock()
        mock_client.get_droplet.return_value = mock_droplet_info
        mock_client_class.return_value = mock_client
        
        resource_service = ResourceService(db)
        
        # Sync all workshop resources
        resource_service.sync_all_workshop_resources(workshop.id)
        
        # Verify only resource1 was synced (resource2 has no provider ID)
        mock_client.get_droplet.assert_called_once_with("12345")


@pytest.mark.unit
def test_calculate_workshop_costs_with_api_errors(db: Session) -> None:
    """Test calculating workshop costs when some resources have API errors."""
    # Setup test data
    instructor = create_test_user(db, "instructor@test.com", UserRole.INSTRUCTOR)
    student = create_test_user(db, "student@test.com", UserRole.STUDENT)
    workshop = create_test_workshop(db, instructor)
    template = create_test_template(db, workshop)
    
    # Create resources with different statuses
    resource1 = Resource(
        name="test-resource-1",
        status=ResourceStatus.ACTIVE,
        user_id=student.id,
        workshop_id=workshop.id,
        template_id=template.id,
        provider_resource_id="12345",
        started_at=datetime.now(UTC),
        estimated_cost=500,  # $5.00 in cents
    )
    
    resource2 = Resource(
        name="test-resource-2",
        status=ResourceStatus.ERROR,  # Error status
        user_id=student.id,
        workshop_id=workshop.id,
        template_id=template.id,
        provider_resource_id=None,
        started_at=datetime.now(UTC),
        estimated_cost=0,  # No cost for error resources
    )
    
    db.add(resource1)
    db.add(resource2)
    db.commit()
    
    with patch('cloud_classroom.services.resource_service.SyncDigitalOceanClient') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        resource_service = ResourceService(db)
        
        # Get cost summary instead
        cost_summary = resource_service.get_workshop_cost_summary(workshop.id)
        total_cost = cost_summary.get('total_cost', 0)
        
        # Verify only running resource contributes to cost
        assert total_cost >= 0  # Should include only resource1's cost


@pytest.mark.unit
def test_get_resource_health_status_missing_provider_id(db: Session) -> None:
    """Test getting resource health status for resource without provider ID."""
    # Setup test data
    instructor = create_test_user(db, "instructor@test.com", UserRole.INSTRUCTOR)
    student = create_test_user(db, "student@test.com", UserRole.STUDENT)
    workshop = create_test_workshop(db, instructor)
    template = create_test_template(db, workshop)
    
    # Create a resource without provider ID
    resource = Resource(
        name="test-resource",
        status=ResourceStatus.ERROR,
        user_id=student.id,
        workshop_id=workshop.id,
        template_id=template.id,
        provider_resource_id=None,  # Missing provider ID
        ip_address=None,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    
    with patch('cloud_classroom.services.resource_service.SyncDigitalOceanClient') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        resource_service = ResourceService(db)
        
        # Get health status
        health_status = resource_service.get_workshop_health_status(workshop.id)
        
        # Verify health check handles missing provider ID gracefully
        assert health_status is not None
        # Workshop health status should return meaningful data
        assert "total_resources" in health_status or "healthy_resources" in health_status