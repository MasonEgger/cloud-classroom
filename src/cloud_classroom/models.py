"""Database models for Cloud Classroom."""

import enum
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cloud_classroom.database import Base


class UserRole(enum.Enum):
    """User roles in the system."""
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class ResourceStatus(enum.Enum):
    """Status of cloud resources."""
    PENDING = "pending"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    DESTROYED = "destroyed"


class WorkshopMode(enum.Enum):
    """Workshop operation modes."""
    SIMPLE = "simple"  # Workshop mode with access codes
    ACADEMIC = "academic"  # Academic course mode with enrollment


class User(Base):
    """User model."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(default=UserRole.STUDENT)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC)
    )

    # Relationships
    workshops: Mapped[list["Workshop"]] = relationship(back_populates="instructor")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="user")
    resources: Mapped[list["Resource"]] = relationship(back_populates="user")


class Workshop(Base):
    """Workshop/Class model."""
    __tablename__ = "workshops"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(default=None)
    access_code: Mapped[str | None] = mapped_column(String(50), unique=True, index=True, default=None)
    mode: Mapped[WorkshopMode] = mapped_column(default=WorkshopMode.SIMPLE)

    # Resource limits
    max_participants: Mapped[int] = mapped_column(default=50)
    resource_limit_per_user: Mapped[int] = mapped_column(default=3)  # Max resources per user
    budget_limit: Mapped[int] = mapped_column(default=1000)  # Budget in cents

    # Timing
    start_time: Mapped[datetime | None] = mapped_column(default=None)
    end_time: Mapped[datetime | None] = mapped_column(default=None)

    # Settings
    auto_approve_enrollment: Mapped[bool] = mapped_column(default=True)
    allow_resource_creation: Mapped[bool] = mapped_column(default=True)
    auto_cleanup: Mapped[bool] = mapped_column(default=True)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC)
    )

    # Foreign keys
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Relationships
    instructor: Mapped["User"] = relationship(back_populates="workshops")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="workshop")
    resources: Mapped[list["Resource"]] = relationship(back_populates="workshop")
    resource_templates: Mapped[list["ResourceTemplate"]] = relationship(back_populates="workshop")


class Enrollment(Base):
    """User enrollment in workshops."""
    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, approved, rejected
    enrolled_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    approved_at: Mapped[datetime | None] = mapped_column(default=None)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    workshop_id: Mapped[int] = mapped_column(ForeignKey("workshops.id"))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="enrollments")
    workshop: Mapped["Workshop"] = relationship(back_populates="enrollments")


class ResourceTemplate(Base):
    """Template for resources that can be created in a workshop."""
    __tablename__ = "resource_templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(default=None)

    # DigitalOcean specific settings
    droplet_size: Mapped[str] = mapped_column(String(50), default="s-1vcpu-1gb")  # DigitalOcean size slug
    droplet_image: Mapped[str] = mapped_column(String(100), default="ubuntu-22-04-x64")  # Image slug
    region: Mapped[str] = mapped_column(String(50), default="nyc3")  # Region slug

    # Provisioning
    user_data: Mapped[str | None] = mapped_column(default=None)  # Cloud-init user data
    ssh_keys: Mapped[str | None] = mapped_column(default=None)  # JSON array of SSH key IDs

    # Limits
    max_instances_per_user: Mapped[int] = mapped_column(default=1)
    estimated_cost_per_hour: Mapped[int] = mapped_column(default=600)  # Cost in cents per hour

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    # Foreign keys
    workshop_id: Mapped[int] = mapped_column(ForeignKey("workshops.id"))

    # Relationships
    workshop: Mapped["Workshop"] = relationship(back_populates="resource_templates")
    resources: Mapped[list["Resource"]] = relationship(back_populates="template")


class Resource(Base):
    """Individual cloud resource instances."""
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))

    # Cloud provider details
    provider_resource_id: Mapped[str | None] = mapped_column(String(255), default=None)  # DigitalOcean droplet ID
    provider: Mapped[str] = mapped_column(String(50), default="digitalocean")
    ip_address: Mapped[str | None] = mapped_column(String(45), default=None)  # IPv4 or IPv6 address

    # Status and lifecycle
    status: Mapped[ResourceStatus] = mapped_column(default=ResourceStatus.PENDING)
    error_message: Mapped[str | None] = mapped_column(default=None)

    # Timing
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    stopped_at: Mapped[datetime | None] = mapped_column(default=None)
    destroyed_at: Mapped[datetime | None] = mapped_column(default=None)

    # Cost tracking
    estimated_cost: Mapped[int] = mapped_column(default=0)  # Running total in cents
    last_cost_update: Mapped[datetime | None] = mapped_column(default=None)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    workshop_id: Mapped[int] = mapped_column(ForeignKey("workshops.id"))
    template_id: Mapped[int] = mapped_column(ForeignKey("resource_templates.id"))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="resources")
    workshop: Mapped["Workshop"] = relationship(back_populates="resources")
    template: Mapped["ResourceTemplate"] = relationship(back_populates="resources")
