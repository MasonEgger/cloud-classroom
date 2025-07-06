"""Workshop management endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from cloud_classroom.core.dependencies import get_current_instructor, get_current_user
from cloud_classroom.core.security import generate_access_code
from cloud_classroom.database import get_db
from cloud_classroom.models import Enrollment, ResourceTemplate, User, Workshop
from cloud_classroom.schemas import (
    EnrollmentCreate,
    EnrollmentResponse,
    ResourceTemplateCreate,
    ResourceTemplateResponse,
    ResourceTemplateUpdate,
    WorkshopCreate,
    WorkshopListResponse,
    WorkshopResponse,
    WorkshopUpdate,
)

router = APIRouter(prefix="/workshops", tags=["workshops"])


@router.post("", response_model=WorkshopResponse, status_code=status.HTTP_201_CREATED)
async def create_workshop(
    workshop_data: WorkshopCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
) -> Workshop:
    """Create a new workshop."""
    # Generate unique access code
    access_code: str | None = None
    if workshop_data.mode.value == "simple":  # Only generate access codes for simple mode
        max_attempts = 10
        for _ in range(max_attempts):
            candidate_code = generate_access_code()
            existing_workshop = db.query(Workshop).filter(Workshop.access_code == candidate_code).first()
            if existing_workshop is None:
                access_code = candidate_code
                break

        if access_code is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate unique access code. Please try again.",
            )

    # Create new workshop
    new_workshop = Workshop(
        title=workshop_data.title,
        description=workshop_data.description,
        access_code=access_code,
        mode=workshop_data.mode,
        max_participants=workshop_data.max_participants,
        resource_limit_per_user=workshop_data.resource_limit_per_user,
        budget_limit=workshop_data.budget_limit,
        start_time=workshop_data.start_time,
        end_time=workshop_data.end_time,
        auto_approve_enrollment=workshop_data.auto_approve_enrollment,
        allow_resource_creation=workshop_data.allow_resource_creation,
        auto_cleanup=workshop_data.auto_cleanup,
        instructor_id=current_user.id,
    )

    db.add(new_workshop)
    db.commit()
    db.refresh(new_workshop)

    return new_workshop


@router.get("", response_model=WorkshopListResponse)
async def list_workshops(
    skip: int = Query(0, ge=0, description="Number of workshops to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of workshops to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkshopListResponse:
    """List workshops. Instructors see their own workshops, students see enrolled workshops."""
    if current_user.role.value == "instructor" or current_user.role.value == "admin":
        # Instructors see their own workshops
        query = db.query(Workshop).filter(Workshop.instructor_id == current_user.id)
    else:
        # Students see workshops they are enrolled in
        query = (
            db.query(Workshop)
            .join(Enrollment, Workshop.id == Enrollment.workshop_id)
            .filter(Enrollment.user_id == current_user.id)
            .filter(Enrollment.status == "approved")
        )

    total = query.count()
    workshops = query.offset(skip).limit(limit).all()

    workshop_responses = [WorkshopResponse.model_validate(workshop) for workshop in workshops]

    return WorkshopListResponse(
        workshops=workshop_responses,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
    )


@router.get("/{workshop_id}", response_model=WorkshopResponse)
async def get_workshop(
    workshop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Workshop:
    """Get a specific workshop by ID."""
    workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()

    if workshop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop not found",
        )

    # Check permissions: instructor who owns it, enrolled student, or admin
    if current_user.role.value == "admin":
        # Admins can see any workshop
        pass
    elif current_user.role.value == "instructor" and workshop.instructor_id == current_user.id:
        # Instructors can see their own workshops
        pass
    else:
        # Students can only see workshops they are enrolled in
        enrollment = (
            db.query(Enrollment)
            .filter(Enrollment.user_id == current_user.id)
            .filter(Enrollment.workshop_id == workshop_id)
            .filter(Enrollment.status == "approved")
            .first()
        )
        if enrollment is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this workshop",
            )

    return workshop


@router.put("/{workshop_id}", response_model=WorkshopResponse)
async def update_workshop(
    workshop_id: int,
    workshop_data: WorkshopUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
) -> Workshop:
    """Update a workshop."""
    workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()

    if workshop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop not found",
        )

    # Check ownership (only the instructor who created it can update it, or admin)
    if current_user.role.value != "admin" and workshop.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this workshop",
        )

    # Update fields
    update_data = workshop_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workshop, field, value)

    db.commit()
    db.refresh(workshop)

    return workshop


@router.delete("/{workshop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workshop(
    workshop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
) -> None:
    """Delete a workshop."""
    workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()

    if workshop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop not found",
        )

    # Check ownership (only the instructor who created it can delete it, or admin)
    if current_user.role.value != "admin" and workshop.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this workshop",
        )

    db.delete(workshop)
    db.commit()


@router.post("/{workshop_id}/join", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def join_workshop(
    workshop_id: int,
    enrollment_data: EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Enrollment:
    """Join a workshop using an access code."""
    # Check if workshop exists
    workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()
    if workshop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop not found",
        )

    # Verify access code
    if workshop.access_code != enrollment_data.access_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid access code",
        )

    # Check if user is already enrolled
    existing_enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == current_user.id)
        .filter(Enrollment.workshop_id == workshop_id)
        .first()
    )
    if existing_enrollment is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already enrolled in this workshop",
        )

    # Check if workshop is full
    current_enrollment_count = (
        db.query(Enrollment)
        .filter(Enrollment.workshop_id == workshop_id)
        .filter(Enrollment.status.in_(["approved", "pending"]))
        .count()
    )
    if current_enrollment_count >= workshop.max_participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workshop is full",
        )

    # Create enrollment
    enrollment_status = "approved" if workshop.auto_approve_enrollment else "pending"
    new_enrollment = Enrollment(
        user_id=current_user.id,
        workshop_id=workshop_id,
        status=enrollment_status,
        approved_at=datetime.now(UTC) if enrollment_status == "approved" else None,
    )

    db.add(new_enrollment)
    db.commit()
    db.refresh(new_enrollment)

    return new_enrollment


# Resource Template endpoints
@router.post("/{workshop_id}/resource-templates", response_model=ResourceTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_resource_template(
    workshop_id: int,
    template_data: ResourceTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
) -> ResourceTemplate:
    """Create a new resource template for a workshop."""
    # Check if workshop exists and user owns it
    workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()
    if not workshop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop not found",
        )

    # Check ownership (only the instructor who created it can add templates, or admin)
    if current_user.role.value != "admin" and workshop.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this workshop",
        )

    # Create new resource template
    new_template = ResourceTemplate(
        name=template_data.name,
        description=template_data.description,
        droplet_size=template_data.droplet_size,
        droplet_image=template_data.droplet_image,
        region=template_data.region,
        user_data=template_data.user_data,
        ssh_keys=template_data.ssh_keys,
        max_instances_per_user=template_data.max_instances_per_user,
        estimated_cost_per_hour=template_data.estimated_cost_per_hour,
        workshop_id=workshop_id,
    )

    db.add(new_template)
    db.commit()
    db.refresh(new_template)

    return new_template


@router.get("/{workshop_id}/resource-templates", response_model=list[ResourceTemplateResponse])
async def list_resource_templates(
    workshop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ResourceTemplate]:
    """List resource templates for a workshop."""
    # Check if workshop exists
    workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()
    if workshop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop not found",
        )

    # Check permissions: instructor who owns it, enrolled student, or admin
    if current_user.role.value == "admin":
        # Admins can see any workshop's templates
        pass
    elif current_user.role.value == "instructor" and workshop.instructor_id == current_user.id:
        # Instructors can see their own workshop templates
        pass
    else:
        # Students can only see templates for workshops they are enrolled in
        enrollment = (
            db.query(Enrollment)
            .filter(Enrollment.user_id == current_user.id)
            .filter(Enrollment.workshop_id == workshop_id)
            .filter(Enrollment.status == "approved")
            .first()
        )
        if enrollment is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this workshop",
            )

    templates = (
        db.query(ResourceTemplate)
        .filter(ResourceTemplate.workshop_id == workshop_id)
        .filter(ResourceTemplate.is_active == True)  # noqa: E712
        .all()
    )

    return templates


@router.get("/{workshop_id}/resource-templates/{template_id}", response_model=ResourceTemplateResponse)
async def get_resource_template(
    workshop_id: int,
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResourceTemplate:
    """Get a specific resource template."""
    # Check if workshop exists
    workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()
    if workshop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop not found",
        )

    # Check permissions
    if current_user.role.value == "admin" or current_user.role.value == "instructor" and workshop.instructor_id == current_user.id:
        pass
    else:
        enrollment = (
            db.query(Enrollment)
            .filter(Enrollment.user_id == current_user.id)
            .filter(Enrollment.workshop_id == workshop_id)
            .filter(Enrollment.status == "approved")
            .first()
        )
        if enrollment is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this workshop",
            )

    template = (
        db.query(ResourceTemplate)
        .filter(ResourceTemplate.id == template_id)
        .filter(ResourceTemplate.workshop_id == workshop_id)
        .first()
    )

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource template not found",
        )

    return template


@router.put("/{workshop_id}/resource-templates/{template_id}", response_model=ResourceTemplateResponse)
async def update_resource_template(
    workshop_id: int,
    template_id: int,
    template_data: ResourceTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
) -> ResourceTemplate:
    """Update a resource template."""
    # Check if workshop exists and user owns it
    workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()
    if not workshop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop not found",
        )

    if current_user.role.value != "admin" and workshop.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this workshop",
        )

    template = (
        db.query(ResourceTemplate)
        .filter(ResourceTemplate.id == template_id)
        .filter(ResourceTemplate.workshop_id == workshop_id)
        .first()
    )

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource template not found",
        )

    # Update fields
    update_data = template_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    db.commit()
    db.refresh(template)

    return template


@router.delete("/{workshop_id}/resource-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource_template(
    workshop_id: int,
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
) -> None:
    """Delete a resource template."""
    # Check if workshop exists and user owns it
    workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()
    if not workshop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop not found",
        )

    if current_user.role.value != "admin" and workshop.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this workshop",
        )

    template = (
        db.query(ResourceTemplate)
        .filter(ResourceTemplate.id == template_id)
        .filter(ResourceTemplate.workshop_id == workshop_id)
        .first()
    )

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource template not found",
        )

    db.delete(template)
    db.commit()
