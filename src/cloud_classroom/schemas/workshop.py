"""Pydantic schemas for workshop-related operations."""

from datetime import datetime

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from cloud_classroom.models import WorkshopMode


class WorkshopBase(BaseModel):
    """Base workshop schema."""
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    mode: WorkshopMode = Field(default=WorkshopMode.SIMPLE)
    max_participants: int = Field(default=50, ge=1, le=1000)
    resource_limit_per_user: int = Field(default=3, ge=1, le=20)
    budget_limit: int = Field(default=1000, ge=100)  # Budget in cents, minimum $1.00
    auto_approve_enrollment: bool = Field(default=True)
    allow_resource_creation: bool = Field(default=True)
    auto_cleanup: bool = Field(default=True)


class WorkshopCreate(WorkshopBase):
    """Schema for creating a new workshop."""
    start_time: datetime | None = Field(None)
    end_time: datetime | None = Field(None)

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: datetime | None, info: ValidationInfo) -> datetime | None:
        """Validate that end_time is after start_time."""
        if v is not None and info.data.get("start_time") is not None and v <= info.data["start_time"]:
            raise ValueError("End time must be after start time")
        return v


class WorkshopUpdate(BaseModel):
    """Schema for updating a workshop."""
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    max_participants: int | None = Field(None, ge=1, le=1000)
    resource_limit_per_user: int | None = Field(None, ge=1, le=20)
    budget_limit: int | None = Field(None, ge=100)
    start_time: datetime | None = Field(None)
    end_time: datetime | None = Field(None)
    auto_approve_enrollment: bool | None = None
    allow_resource_creation: bool | None = None
    auto_cleanup: bool | None = None
    is_active: bool | None = None


class WorkshopInDB(WorkshopBase):
    """Workshop schema with database fields."""
    id: int
    access_code: str | None
    start_time: datetime | None
    end_time: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    instructor_id: int

    model_config = {"from_attributes": True}


class WorkshopResponse(WorkshopBase):
    """Workshop response schema."""
    id: int
    access_code: str | None
    start_time: datetime | None
    end_time: datetime | None
    is_active: bool
    created_at: datetime
    instructor_id: int

    model_config = {"from_attributes": True}


class WorkshopListResponse(BaseModel):
    """Schema for workshop list responses."""
    workshops: list[WorkshopResponse]
    total: int
    page: int
    page_size: int


class EnrollmentBase(BaseModel):
    """Base enrollment schema."""
    pass


class EnrollmentCreate(EnrollmentBase):
    """Schema for creating enrollment (joining workshop)."""
    access_code: str = Field(..., min_length=1, max_length=50)


class EnrollmentResponse(EnrollmentBase):
    """Enrollment response schema."""
    id: int
    status: str
    enrolled_at: datetime
    approved_at: datetime | None
    user_id: int
    workshop_id: int

    model_config = {"from_attributes": True}
