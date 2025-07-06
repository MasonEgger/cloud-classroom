"""Pydantic schemas for resource-related operations."""

from datetime import datetime

from pydantic import BaseModel, Field

from cloud_classroom.models import ResourceStatus


class ResourceTemplateBase(BaseModel):
    """Base resource template schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    droplet_size: str = Field(default="s-1vcpu-1gb", max_length=50)
    droplet_image: str = Field(default="ubuntu-22-04-x64", max_length=100)
    region: str = Field(default="nyc3", max_length=50)
    user_data: str | None = Field(None, max_length=10000)
    ssh_keys: str | None = Field(None, max_length=1000)
    max_instances_per_user: int = Field(default=1, ge=1, le=10)
    estimated_cost_per_hour: int = Field(default=600, ge=1)  # Cost in cents per hour


class ResourceTemplateCreate(ResourceTemplateBase):
    """Schema for creating a resource template."""
    pass


class ResourceTemplateUpdate(BaseModel):
    """Schema for updating a resource template."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    droplet_size: str | None = Field(None, max_length=50)
    droplet_image: str | None = Field(None, max_length=100)
    region: str | None = Field(None, max_length=50)
    user_data: str | None = Field(None, max_length=10000)
    ssh_keys: str | None = Field(None, max_length=1000)
    max_instances_per_user: int | None = Field(None, ge=1, le=10)
    estimated_cost_per_hour: int | None = Field(None, ge=1)
    is_active: bool | None = None


class ResourceTemplateResponse(ResourceTemplateBase):
    """Resource template response schema."""
    id: int
    workshop_id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ResourceTemplateListResponse(BaseModel):
    """Schema for listing resource templates."""
    templates: list[ResourceTemplateResponse]
    total: int


class ResourceBase(BaseModel):
    """Base resource schema."""
    name: str = Field(..., min_length=1, max_length=255)


class ResourceCreate(ResourceBase):
    """Schema for creating a resource instance."""
    template_id: int = Field(..., gt=0)


class ResourceResponse(ResourceBase):
    """Resource response schema."""
    id: int
    provider_resource_id: str | None
    provider: str
    ip_address: str | None
    status: ResourceStatus
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    stopped_at: datetime | None
    destroyed_at: datetime | None
    estimated_cost: int
    last_cost_update: datetime | None
    user_id: int
    workshop_id: int
    template_id: int

    model_config = {"from_attributes": True}


class ResourceListResponse(BaseModel):
    """Schema for resource list responses."""
    resources: list[ResourceResponse]
    total: int
    page: int
    page_size: int


class ResourceAction(BaseModel):
    """Schema for resource actions (start, stop, destroy)."""
    action: str = Field(..., pattern="^(start|stop|destroy|restart)$")


class ResourceActionResponse(BaseModel):
    """Schema for resource action responses."""
    success: bool
    message: str
    resource_id: int
