"""Security utilities for password hashing and JWT tokens."""

import secrets
import string
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from cloud_classroom.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt  # type: ignore[no-any-return]


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload  # type: ignore[no-any-return]
    except JWTError as e:
        raise ValueError("Invalid token") from e


def generate_access_code(length: int = 8) -> str:
    """Generate a random access code for workshops."""
    # Use uppercase letters and digits, excluding ambiguous characters
    alphabet = string.ascii_uppercase + string.digits
    # Remove potentially confusing characters: 0, O, 1, I, L
    alphabet = alphabet.replace("0", "").replace("O", "").replace("1", "").replace("I", "").replace("L", "")

    return "".join(secrets.choice(alphabet) for _ in range(length))
