"""Service for managing cloud resources."""

import json
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from cloud_classroom.config import settings
from cloud_classroom.models import (
    Enrollment,
    Resource,
    ResourceStatus,
    ResourceTemplate,
    User,
    Workshop,
)
from cloud_classroom.services.digitalocean_client import SyncDigitalOceanClient


class ResourceService:
    """Service for managing cloud resources."""

    def __init__(self, db: Session) -> None:
        """Initialize the resource service."""
        self.db = db
        self.digitalocean_client = SyncDigitalOceanClient(token=settings.digitalocean_token)

    def provision_resource(
        self,
        user_id: int,
        workshop_id: int,
        template_id: int,
        name: str,
    ) -> Resource:
        """Provision a new resource from a template."""
        # Verify user is enrolled in workshop
        enrollment = (
            self.db.query(Enrollment)
            .filter(
                Enrollment.user_id == user_id,
                Enrollment.workshop_id == workshop_id,
                Enrollment.status == "approved",
            )
            .first()
        )
        
        if enrollment is None:
            raise ValueError("User is not enrolled in this workshop")

        # Get template
        template = (
            self.db.query(ResourceTemplate)
            .filter(
                ResourceTemplate.id == template_id,
                ResourceTemplate.workshop_id == workshop_id,
                ResourceTemplate.is_active == True,
            )
            .first()
        )
        
        if template is None:
            raise ValueError("Template not found")

        # Check user's existing resources for this template
        existing_count = (
            self.db.query(Resource)
            .filter(
                Resource.user_id == user_id,
                Resource.template_id == template_id,
                Resource.status.in_([
                    ResourceStatus.PENDING,
                    ResourceStatus.PROVISIONING,
                    ResourceStatus.ACTIVE,
                    ResourceStatus.STOPPED,
                ])
            )
            .count()
        )

        if existing_count >= template.max_instances_per_user:
            raise ValueError(
                f"User exceeds maximum instances ({template.max_instances_per_user}) for this template"
            )

        # Check budget limit
        if not self.check_budget_limit(workshop_id, template.estimated_cost_per_hour):
            raise ValueError("Provisioning this resource would exceed the workshop budget limit")

        # Create resource record
        resource = Resource(
            name=name,
            user_id=user_id,
            workshop_id=workshop_id,
            template_id=template_id,
            status=ResourceStatus.PROVISIONING,
            provider="digitalocean",
        )
        
        self.db.add(resource)
        self.db.commit()
        self.db.refresh(resource)

        try:
            # Parse SSH keys if provided
            ssh_keys = []
            if template.ssh_keys:
                ssh_keys = json.loads(template.ssh_keys)

            # Create droplet via DigitalOcean API
            droplet_info = self.digitalocean_client.create_droplet(
                name=name,
                template=template,
                ssh_keys=ssh_keys,
            )

            # Update resource with droplet information
            resource.provider_resource_id = droplet_info.id
            resource.ip_address = droplet_info.ip_address
            resource.started_at = datetime.now(UTC)
            
            self.db.commit()

        except Exception as e:
            # Update resource status to error
            resource.status = ResourceStatus.ERROR
            resource.error_message = str(e)
            self.db.commit()
            raise

        return resource

    def get_user_resources(
        self,
        user_id: int,
        workshop_id: int,
    ) -> List[Resource]:
        """Get all resources for a user in a workshop."""
        # Verify user is enrolled in workshop
        enrollment = (
            self.db.query(Enrollment)
            .filter(
                Enrollment.user_id == user_id,
                Enrollment.workshop_id == workshop_id,
                Enrollment.status == "approved",
            )
            .first()
        )
        
        if enrollment is None:
            raise ValueError("User is not enrolled in this workshop")

        return (
            self.db.query(Resource)
            .filter(
                Resource.user_id == user_id,
                Resource.workshop_id == workshop_id,
            )
            .order_by(Resource.created_at.desc())
            .all()
        )

    def get_resource(
        self,
        resource_id: int,
        user_id: int,
    ) -> Optional[Resource]:
        """Get a specific resource owned by the user."""
        return (
            self.db.query(Resource)
            .filter(
                Resource.id == resource_id,
                Resource.user_id == user_id,
            )
            .first()
        )

    def start_resource(self, resource_id: int, user_id: int) -> bool:
        """Start a stopped resource."""
        resource = self.get_resource(resource_id, user_id)
        if resource is None:
            raise ValueError("Resource not found")

        if resource.provider_resource_id is None:
            raise ValueError("Resource has no provider ID")

        if resource.status != ResourceStatus.STOPPED:
            raise ValueError("Resource is not in stopped state")

        try:
            success = self.digitalocean_client.start_droplet(resource.provider_resource_id)
            if success:
                resource.status = ResourceStatus.ACTIVE
                resource.started_at = datetime.now(UTC)
                resource.stopped_at = None
                self.db.commit()
            return success
        except Exception as e:
            resource.status = ResourceStatus.ERROR
            resource.error_message = str(e)
            self.db.commit()
            raise

    def stop_resource(self, resource_id: int, user_id: int) -> bool:
        """Stop a running resource."""
        resource = self.get_resource(resource_id, user_id)
        if resource is None:
            raise ValueError("Resource not found")

        if resource.provider_resource_id is None:
            raise ValueError("Resource has no provider ID")

        if resource.status != ResourceStatus.ACTIVE:
            raise ValueError("Resource is not in active state")

        try:
            success = self.digitalocean_client.stop_droplet(resource.provider_resource_id)
            if success:
                resource.status = ResourceStatus.STOPPED
                resource.stopped_at = datetime.now(UTC)
                self.db.commit()
            return success
        except Exception as e:
            resource.status = ResourceStatus.ERROR
            resource.error_message = str(e)
            self.db.commit()
            raise

    def destroy_resource(self, resource_id: int, user_id: int) -> bool:
        """Destroy a resource permanently."""
        resource = self.get_resource(resource_id, user_id)
        if resource is None:
            raise ValueError("Resource not found")

        if resource.provider_resource_id is None:
            raise ValueError("Resource has no provider ID")

        if resource.status == ResourceStatus.DESTROYED:
            raise ValueError("Resource is already destroyed")

        try:
            success = self.digitalocean_client.destroy_droplet(resource.provider_resource_id)
            if success:
                resource.status = ResourceStatus.DESTROYED
                resource.destroyed_at = datetime.now(UTC)
                self.db.commit()
            return success
        except Exception as e:
            resource.status = ResourceStatus.ERROR
            resource.error_message = str(e)
            self.db.commit()
            raise

    def create_template(
        self,
        workshop_id: int,
        instructor_id: int,
        template_data: Dict[str, Any],
    ) -> ResourceTemplate:
        """Create a new resource template for a workshop."""
        # Verify instructor owns the workshop
        workshop = (
            self.db.query(Workshop)
            .filter(
                Workshop.id == workshop_id,
                Workshop.instructor_id == instructor_id,
            )
            .first()
        )
        
        if workshop is None:
            raise ValueError("Workshop not found or not owned by instructor")

        template = ResourceTemplate(
            workshop_id=workshop_id,
            **template_data,
        )
        
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        return template

    def get_workshop_templates(self, workshop_id: int) -> List[ResourceTemplate]:
        """Get all templates for a workshop."""
        return (
            self.db.query(ResourceTemplate)
            .filter(
                ResourceTemplate.workshop_id == workshop_id,
                ResourceTemplate.is_active == True,
            )
            .order_by(ResourceTemplate.created_at.asc())
            .all()
        )

    def calculate_resource_cost(self, resource_id: int, user_id: int) -> Dict[str, Any]:
        """Calculate the current cost for a resource."""
        resource = self.get_resource(resource_id, user_id)
        if resource is None:
            raise ValueError("Resource not found")

        template = (
            self.db.query(ResourceTemplate)
            .filter(ResourceTemplate.id == resource.template_id)
            .first()
        )
        if template is None:
            raise ValueError("Resource template not found")

        if resource.started_at is None:
            return {
                "total_cost_cents": resource.estimated_cost,
                "hours_running": 0.0,
                "cost_per_hour_cents": template.estimated_cost_per_hour,
            }

        # Calculate running time
        end_time = resource.stopped_at or resource.destroyed_at or datetime.now(UTC)
        
        # Ensure both timestamps have the same timezone info
        if resource.started_at.tzinfo is None:
            # Convert naive datetime to UTC
            started_at = resource.started_at.replace(tzinfo=UTC)
        else:
            started_at = resource.started_at
            
        if end_time.tzinfo is None:
            # Convert naive datetime to UTC
            end_time = end_time.replace(tzinfo=UTC)
        
        running_time = end_time - started_at
        hours_running = running_time.total_seconds() / 3600.0

        # Calculate cost
        total_cost = int(hours_running * template.estimated_cost_per_hour)

        # Update resource cost
        resource.estimated_cost = total_cost
        resource.last_cost_update = datetime.now(UTC)
        self.db.commit()

        return {
            "total_cost_cents": total_cost,
            "hours_running": hours_running,
            "cost_per_hour_cents": template.estimated_cost_per_hour,
        }

    def check_budget_limit(self, workshop_id: int, additional_cost_per_hour: int) -> bool:
        """Check if adding a resource would exceed workshop budget."""
        workshop = (
            self.db.query(Workshop)
            .filter(Workshop.id == workshop_id)
            .first()
        )
        if workshop is None:
            raise ValueError("Workshop not found")

        if workshop.budget_limit <= 0:
            return True  # No budget limit

        # Calculate current total cost for all resources in workshop
        current_total = (
            self.db.query(func.sum(Resource.estimated_cost))
            .filter(
                Resource.workshop_id == workshop_id,
                Resource.status.in_([
                    ResourceStatus.PENDING,
                    ResourceStatus.PROVISIONING,
                    ResourceStatus.ACTIVE,
                    ResourceStatus.STOPPED,
                ])
            )
            .scalar() or 0
        )

        # Estimate additional cost for 1 hour (conservative estimate)
        estimated_additional_cost = additional_cost_per_hour

        return (current_total + estimated_additional_cost) <= workshop.budget_limit

    def get_workshop_cost_summary(self, workshop_id: int) -> Dict[str, Any]:
        """Get cost summary for a workshop."""
        workshop = (
            self.db.query(Workshop)
            .filter(Workshop.id == workshop_id)
            .first()
        )
        if workshop is None:
            raise ValueError("Workshop not found")

        # Get total cost of all resources
        total_cost = (
            self.db.query(func.sum(Resource.estimated_cost))
            .filter(Resource.workshop_id == workshop_id)
            .scalar() or 0
        )

        # Count resources by status
        active_count = (
            self.db.query(Resource)
            .filter(
                Resource.workshop_id == workshop_id,
                Resource.status == ResourceStatus.ACTIVE,
            )
            .count()
        )

        total_count = (
            self.db.query(Resource)
            .filter(Resource.workshop_id == workshop_id)
            .count()
        )

        # Calculate budget metrics
        budget_limit = workshop.budget_limit
        remaining_budget = max(0, budget_limit - total_cost)
        budget_used_percentage = (total_cost / budget_limit * 100) if budget_limit > 0 else 0

        return {
            "total_cost_cents": total_cost,
            "budget_limit_cents": budget_limit,
            "remaining_budget_cents": remaining_budget,
            "budget_used_percentage": round(budget_used_percentage, 1),
            "active_resources_count": active_count,
            "total_resources_count": total_count,
        }

    def update_all_resource_costs(self, workshop_id: int) -> Dict[str, Any]:
        """Update costs for all active resources in a workshop."""
        # Get all active resources in the workshop
        resources = (
            self.db.query(Resource)
            .filter(
                Resource.workshop_id == workshop_id,
                Resource.status.in_([ResourceStatus.ACTIVE, ResourceStatus.STOPPED]),
                Resource.started_at.is_not(None),
            )
            .all()
        )

        updated_count = 0
        for resource in resources:
            try:
                template = (
                    self.db.query(ResourceTemplate)
                    .filter(ResourceTemplate.id == resource.template_id)
                    .first()
                )
                if template is None:
                    continue

                # Calculate running time
                if resource.started_at is None:
                    continue
                    
                end_time = resource.stopped_at or resource.destroyed_at or datetime.now(UTC)
                
                # Ensure both timestamps have the same timezone info
                if resource.started_at.tzinfo is None:
                    started_at = resource.started_at.replace(tzinfo=UTC)
                else:
                    started_at = resource.started_at
                    
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=UTC)
                
                running_time = end_time - started_at
                hours_running = running_time.total_seconds() / 3600.0

                # Update cost
                resource.estimated_cost = int(hours_running * template.estimated_cost_per_hour)
                resource.last_cost_update = datetime.now(UTC)
                updated_count += 1

            except Exception:
                # Skip resources that can't be updated
                continue

        self.db.commit()

        return {
            "updated_resources": updated_count,
            "message": f"Updated costs for {updated_count} resources successfully",
        }

    def sync_resource_status(self, resource_id: int, user_id: int) -> Dict[str, Any]:
        """Sync resource status with DigitalOcean."""
        resource = self.get_resource(resource_id, user_id)
        if resource is None:
            raise ValueError("Resource not found")

        if resource.provider_resource_id is None:
            raise ValueError("Resource has no provider ID")

        old_status = resource.status.value
        
        try:
            # Get current status from DigitalOcean
            droplet_info = self.digitalocean_client.get_droplet(resource.provider_resource_id)
            
            if droplet_info is None:
                # Droplet no longer exists
                resource.status = ResourceStatus.ERROR
                resource.error_message = "Droplet not found in DigitalOcean"
                new_status = resource.status.value
                self.db.commit()
                
                return {
                    "success": True,
                    "old_status": old_status,
                    "new_status": new_status,
                    "message": "Resource marked as error - droplet not found",
                }
            
            # Update resource with current DigitalOcean status
            if droplet_info.status == "active":
                resource.status = ResourceStatus.ACTIVE
            elif droplet_info.status == "off":
                resource.status = ResourceStatus.STOPPED
            elif droplet_info.status == "new":
                resource.status = ResourceStatus.PROVISIONING
            else:
                resource.status = ResourceStatus.ERROR
                resource.error_message = f"Unknown DigitalOcean status: {droplet_info.status}"
            
            # Update IP address if available
            if droplet_info.ip_address:
                resource.ip_address = droplet_info.ip_address
            
            new_status = resource.status.value
            self.db.commit()
            
            return {
                "success": True,
                "old_status": old_status,
                "new_status": new_status,
                "ip_address": resource.ip_address,
                "message": f"Resource status updated from {old_status} to {new_status}",
            }
            
        except Exception as e:
            resource.status = ResourceStatus.ERROR
            resource.error_message = f"Failed to sync status: {str(e)}"
            self.db.commit()
            
            return {
                "success": False,
                "old_status": old_status,
                "new_status": resource.status.value,
                "message": f"Failed to sync status: {str(e)}",
            }

    def sync_all_workshop_resources(self, workshop_id: int) -> Dict[str, Any]:
        """Sync status for all resources in a workshop."""
        # Get all resources that can be synced (not destroyed)
        resources = (
            self.db.query(Resource)
            .filter(
                Resource.workshop_id == workshop_id,
                Resource.provider_resource_id.is_not(None),
                Resource.status != ResourceStatus.DESTROYED,
            )
            .all()
        )

        synced_count = 0
        for resource in resources:
            try:
                # Get current status from DigitalOcean
                if resource.provider_resource_id is None:
                    continue
                    
                droplet_info = self.digitalocean_client.get_droplet(resource.provider_resource_id)
                
                if droplet_info is None:
                    # Droplet no longer exists
                    resource.status = ResourceStatus.ERROR
                    resource.error_message = "Droplet not found in DigitalOcean"
                else:
                    # Update resource with current DigitalOcean status
                    if droplet_info.status == "active":
                        resource.status = ResourceStatus.ACTIVE
                    elif droplet_info.status == "off":
                        resource.status = ResourceStatus.STOPPED
                    elif droplet_info.status == "new":
                        resource.status = ResourceStatus.PROVISIONING
                    else:
                        resource.status = ResourceStatus.ERROR
                        resource.error_message = f"Unknown DigitalOcean status: {droplet_info.status}"
                    
                    # Update IP address if available
                    if droplet_info.ip_address:
                        resource.ip_address = droplet_info.ip_address
                
                synced_count += 1
                
            except Exception as e:
                resource.status = ResourceStatus.ERROR
                resource.error_message = f"Failed to sync status: {str(e)}"
                continue

        self.db.commit()

        return {
            "synced_resources": synced_count,
            "message": f"Synced {synced_count} resources successfully",
        }

    def get_workshop_health_status(self, workshop_id: int) -> Dict[str, Any]:
        """Get health status summary for all resources in a workshop."""
        # Get all resources in the workshop
        resources = (
            self.db.query(Resource)
            .filter(Resource.workshop_id == workshop_id)
            .all()
        )

        total_resources = len(resources)
        active_count = sum(1 for r in resources if r.status == ResourceStatus.ACTIVE)
        stopped_count = sum(1 for r in resources if r.status == ResourceStatus.STOPPED)
        error_count = sum(1 for r in resources if r.status == ResourceStatus.ERROR)
        
        healthy_percentage = (active_count / total_resources * 100) if total_resources > 0 else 0

        # Build individual resource status info
        resource_statuses = []
        for resource in resources:
            is_healthy = resource.status == ResourceStatus.ACTIVE
            
            resource_statuses.append({
                "id": resource.id,
                "name": resource.name,
                "status": resource.status.value,
                "is_healthy": is_healthy,
                "ip_address": resource.ip_address,
                "error_message": resource.error_message,
                "created_at": resource.created_at,
            })

        return {
            "total_resources": total_resources,
            "active_resources": active_count,
            "stopped_resources": stopped_count,
            "error_resources": error_count,
            "healthy_percentage": round(healthy_percentage, 1),
            "resource_statuses": resource_statuses,
        }