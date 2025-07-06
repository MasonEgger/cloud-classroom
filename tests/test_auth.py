"""Tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_register_user_success(client: TestClient) -> None:
    """Test successful user registration."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "full_name": "Test User",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert data["role"] == "student"
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.unit
def test_register_user_duplicate_email(client: TestClient) -> None:
    """Test registration with duplicate email."""
    # First registration
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "SecurePassword123!",
            "full_name": "First User",
        },
    )

    # Attempt duplicate registration
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "AnotherPassword123!",
            "full_name": "Second User",
        },
    )

    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.unit
def test_register_user_invalid_email(client: TestClient) -> None:
    """Test registration with invalid email."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "SecurePassword123!",
            "full_name": "Test User",
        },
    )

    assert response.status_code == 422


@pytest.mark.unit
def test_register_user_weak_password(client: TestClient) -> None:
    """Test registration with weak password."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "weak",
            "full_name": "Test User",
        },
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("password" in str(error).lower() for error in errors)


@pytest.mark.unit
def test_login_success(client: TestClient) -> None:
    """Test successful login."""
    # First register a user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "SecurePassword123!",
            "full_name": "Login Test User",
        },
    )

    # Now login
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "login@example.com",  # OAuth2 spec uses 'username'
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.unit
def test_login_invalid_credentials(client: TestClient) -> None:
    """Test login with invalid credentials."""
    # First register a user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "login2@example.com",
            "password": "SecurePassword123!",
            "full_name": "Login Test User",
        },
    )

    # Try to login with wrong password
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "login2@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.unit
def test_login_nonexistent_user(client: TestClient) -> None:
    """Test login with nonexistent user."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "nonexistent@example.com",
            "password": "AnyPassword123!",
        },
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()
