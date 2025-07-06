"""Pydantic schemas for API request/response models."""

from cloud_classroom.schemas.resource import (
    ResourceAction,
    ResourceCreate,
    ResourceListResponse,
    ResourceResponse,
    ResourceTemplateCreate,
    ResourceTemplateResponse,
    ResourceTemplateUpdate,
)
from cloud_classroom.schemas.user import Token, TokenData, UserCreate, UserResponse, UserUpdate
from cloud_classroom.schemas.workshop import (
    EnrollmentCreate,
    EnrollmentResponse,
    WorkshopCreate,
    WorkshopListResponse,
    WorkshopResponse,
    WorkshopUpdate,
)

__all__ = [
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "Token",
    "TokenData",
    "WorkshopCreate",
    "WorkshopUpdate",
    "WorkshopResponse",
    "WorkshopListResponse",
    "EnrollmentCreate",
    "EnrollmentResponse",
    "ResourceTemplateCreate",
    "ResourceTemplateUpdate",
    "ResourceTemplateResponse",
    "ResourceCreate",
    "ResourceResponse",
    "ResourceListResponse",
    "ResourceAction",
]
