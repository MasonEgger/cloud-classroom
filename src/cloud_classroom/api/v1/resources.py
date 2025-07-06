"""API endpoints for resource management."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from cloud_classroom.core.dependencies import get_current_user
from cloud_classroom.database import get_db
from cloud_classroom.models import User, UserRole
from cloud_classroom.schemas.resource import (
    ResourceAction,
    ResourceActionResponse,
    ResourceCreate,
    ResourceListResponse,
    ResourceResponse,
    ResourceTemplateCreate,
    ResourceTemplateListResponse,
    ResourceTemplateResponse,
)
from cloud_classroom.services.resource_service import ResourceService

router = APIRouter()


@router.post(
    "/{workshop_id}/templates",
    response_model=ResourceTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_resource_template(
    workshop_id: int,
    template_data: ResourceTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResourceTemplateResponse:
    """Create a new resource template for a workshop."""
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can create resource templates",
        )

    service = ResourceService(db)
    
    try:
        template = service.create_template(
            workshop_id=workshop_id,
            instructor_id=current_user.id,
            template_data=template_data.model_dump(),
        )
        return ResourceTemplateResponse.model_validate(template)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/{workshop_id}/templates",
    response_model=ResourceTemplateListResponse,
)
def list_resource_templates(
    workshop_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResourceTemplateListResponse:
    """List all resource templates for a workshop."""
    service = ResourceService(db)
    
    templates = service.get_workshop_templates(workshop_id)
    template_responses = [ResourceTemplateResponse.model_validate(template) for template in templates]
    
    return ResourceTemplateListResponse(
        templates=template_responses,
        total=len(template_responses),
    )


@router.post(
    "/{workshop_id}/resources",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def provision_resource(
    workshop_id: int,
    resource_data: ResourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResourceResponse:
    """Provision a new resource from a template."""
    service = ResourceService(db)
    
    try:
        resource = service.provision_resource(
            user_id=current_user.id,
            workshop_id=workshop_id,
            template_id=resource_data.template_id,
            name=resource_data.name,
        )
        return ResourceResponse.model_validate(resource)
    except ValueError as e:
        if "not enrolled" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            ) from e
        elif "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        elif "exceeds maximum instances" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        elif "budget" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e


@router.get(
    "/{workshop_id}/resources",
    response_model=List[ResourceResponse],
)
def list_user_resources(
    workshop_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ResourceResponse]:
    """List all resources for the current user in a workshop."""
    service = ResourceService(db)
    
    try:
        resources = service.get_user_resources(
            user_id=current_user.id,
            workshop_id=workshop_id,
        )
        return [ResourceResponse.model_validate(resource) for resource in resources]
    except ValueError as e:
        if "not enrolled" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e


@router.post(
    "/{workshop_id}/resources/{resource_id}/actions",
    response_model=ResourceActionResponse,
)
def perform_resource_action(
    workshop_id: int,
    resource_id: int,
    action_data: ResourceAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResourceActionResponse:
    """Perform an action on a resource (start, stop, destroy)."""
    service = ResourceService(db)
    
    try:
        if action_data.action == "start":
            success = service.start_resource(resource_id, current_user.id)
            message = "Resource started successfully" if success else "Failed to start resource"
        elif action_data.action == "stop":
            success = service.stop_resource(resource_id, current_user.id)
            message = "Resource stopped successfully" if success else "Failed to stop resource"
        elif action_data.action == "destroy":
            success = service.destroy_resource(resource_id, current_user.id)
            message = "Resource destroyed successfully" if success else "Failed to destroy resource"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported action: {action_data.action}",
            )
        
        return ResourceActionResponse(
            success=success,
            message=message,
            resource_id=resource_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{workshop_id}/resources/{resource_id}",
    response_model=ResourceResponse,
)
def get_resource(
    workshop_id: int,
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResourceResponse:
    """Get details of a specific resource."""
    service = ResourceService(db)
    
    resource = service.get_resource(resource_id, current_user.id)
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    
    # Verify resource belongs to the workshop
    if resource.workshop_id != workshop_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found in this workshop",
        )
    
    return ResourceResponse.model_validate(resource)


@router.post(
    "/{workshop_id}/resources/{resource_id}/calculate-cost",
    response_model=Dict[str, Any],
)
def calculate_resource_cost(
    workshop_id: int,
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Calculate the current cost for a resource."""
    service = ResourceService(db)
    
    try:
        cost_info = service.calculate_resource_cost(resource_id, current_user.id)
        return cost_info
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/{workshop_id}/cost-summary",
    response_model=Dict[str, Any],
)
def get_workshop_cost_summary(
    workshop_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get cost summary for a workshop."""
    # Only instructors can view cost summaries
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can view cost summaries",
        )

    service = ResourceService(db)
    
    try:
        summary = service.get_workshop_cost_summary(workshop_id)
        return summary
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post(
    "/{workshop_id}/update-costs",
    response_model=Dict[str, Any],
)
def update_workshop_resource_costs(
    workshop_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Update costs for all resources in a workshop."""
    # Only instructors can update costs
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can update resource costs",
        )

    service = ResourceService(db)
    
    try:
        result = service.update_all_resource_costs(workshop_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post(
    "/{workshop_id}/resources/{resource_id}/sync-status",
    response_model=Dict[str, Any],
)
def sync_resource_status(
    workshop_id: int,
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Sync resource status with DigitalOcean."""
    service = ResourceService(db)
    
    try:
        result = service.sync_resource_status(resource_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post(
    "/{workshop_id}/sync-all-resources",
    response_model=Dict[str, Any],
)
def sync_all_workshop_resources(
    workshop_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Sync status for all resources in a workshop."""
    # Only instructors can sync all resources
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can sync all workshop resources",
        )

    service = ResourceService(db)
    
    try:
        result = service.sync_all_workshop_resources(workshop_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/{workshop_id}/health-status",
    response_model=Dict[str, Any],
)
def get_workshop_health_status(
    workshop_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get health status for all resources in a workshop."""
    # Only instructors can view health status
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can view workshop health status",
        )

    service = ResourceService(db)
    
    try:
        health_status = service.get_workshop_health_status(workshop_id)
        return health_status
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e