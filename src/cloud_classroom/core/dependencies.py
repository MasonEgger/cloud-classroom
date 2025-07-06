"""FastAPI dependency functions for authentication and authorization."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from cloud_classroom.core.security import decode_token
from cloud_classroom.database import get_db
from cloud_classroom.models import User, UserRole

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(credentials.credentials)
        email = payload.get("sub")
        if not isinstance(email, str):
            raise credentials_exception
    except ValueError:
        raise credentials_exception from None

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return user


async def get_current_instructor(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get the current user and verify they are an instructor or admin."""
    if current_user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Instructor role required.",
        )
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get the current user and verify they are an admin."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required.",
        )
    return current_user
