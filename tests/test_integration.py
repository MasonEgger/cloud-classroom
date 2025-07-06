"""Integration tests for Cloud Classroom API.

These tests run against a real HTTP server to verify the complete request/response cycle.
"""

import pytest
import requests


@pytest.mark.integration
def test_root_endpoint(test_server: str) -> None:
    """Test root endpoint returns welcome message."""
    response = requests.get(f"{test_server}/", timeout=5)

    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Cloud Classroom"}


@pytest.mark.integration
def test_health_endpoint(test_server: str) -> None:
    """Test health endpoint returns healthy status."""
    response = requests.get(f"{test_server}/health", timeout=5)

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.integration
def test_api_documentation_available(test_server: str) -> None:
    """Test that API documentation is available."""
    response = requests.get(f"{test_server}/docs", timeout=5)

    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()


@pytest.mark.integration
def test_openapi_schema_available(test_server: str) -> None:
    """Test that OpenAPI schema is available."""
    response = requests.get(f"{test_server}/openapi.json", timeout=5)

    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "paths" in schema
    assert "/api/v1/auth/register" in schema["paths"]
    assert "/api/v1/auth/login" in schema["paths"]


@pytest.mark.integration
def test_user_registration_success(test_server: str) -> None:
    """Test successful user registration."""
    user_data = {
        "email": "integration-test@example.com",
        "password": "SecurePassword123",
        "full_name": "Integration Test User"
    }

    response = requests.post(
        f"{test_server}/api/v1/auth/register",
        json=user_data,
        timeout=5
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["full_name"] == user_data["full_name"]
    assert data["role"] == "student"
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.integration
def test_user_registration_duplicate_email(test_server: str) -> None:
    """Test registration with duplicate email."""
    user_data = {
        "email": "duplicate-test@example.com",
        "password": "SecurePassword123",
        "full_name": "First User"
    }

    # First registration
    response1 = requests.post(
        f"{test_server}/api/v1/auth/register",
        json=user_data,
        timeout=5
    )
    assert response1.status_code == 201

    # Attempt duplicate registration
    user_data["full_name"] = "Second User"
    response2 = requests.post(
        f"{test_server}/api/v1/auth/register",
        json=user_data,
        timeout=5
    )

    assert response2.status_code == 400
    assert "already registered" in response2.json()["detail"].lower()


@pytest.mark.integration
def test_user_registration_invalid_email(test_server: str) -> None:
    """Test registration with invalid email."""
    user_data = {
        "email": "not-an-email",
        "password": "SecurePassword123",
        "full_name": "Test User"
    }

    response = requests.post(
        f"{test_server}/api/v1/auth/register",
        json=user_data,
        timeout=5
    )

    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.integration
def test_user_registration_weak_password(test_server: str) -> None:
    """Test registration with weak password."""
    user_data = {
        "email": "weak-password@example.com",
        "password": "weak",
        "full_name": "Test User"
    }

    response = requests.post(
        f"{test_server}/api/v1/auth/register",
        json=user_data,
        timeout=5
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("password" in str(error).lower() for error in errors)


@pytest.mark.integration
def test_user_login_success(test_server: str) -> None:
    """Test successful user login."""
    # First register a user
    user_data = {
        "email": "login-test@example.com",
        "password": "SecurePassword123",
        "full_name": "Login Test User"
    }

    register_response = requests.post(
        f"{test_server}/api/v1/auth/register",
        json=user_data,
        timeout=5
    )
    assert register_response.status_code == 201

    # Now login
    login_data = {
        "username": user_data["email"],  # OAuth2 spec uses 'username'
        "password": user_data["password"]
    }

    response = requests.post(
        f"{test_server}/api/v1/auth/login",
        data=login_data,  # OAuth2 uses form data, not JSON
        timeout=5
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 50  # JWT tokens are long


@pytest.mark.integration
def test_user_login_invalid_credentials(test_server: str) -> None:
    """Test login with invalid credentials."""
    # First register a user
    user_data = {
        "email": "invalid-creds@example.com",
        "password": "SecurePassword123",
        "full_name": "Invalid Creds User"
    }

    register_response = requests.post(
        f"{test_server}/api/v1/auth/register",
        json=user_data,
        timeout=5
    )
    assert register_response.status_code == 201

    # Try to login with wrong password
    login_data = {
        "username": user_data["email"],
        "password": "WrongPassword123"
    }

    response = requests.post(
        f"{test_server}/api/v1/auth/login",
        data=login_data,
        timeout=5
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.integration
def test_user_login_nonexistent_user(test_server: str) -> None:
    """Test login with nonexistent user."""
    login_data = {
        "username": "nonexistent@example.com",
        "password": "AnyPassword123"
    }

    response = requests.post(
        f"{test_server}/api/v1/auth/login",
        data=login_data,
        timeout=5
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.integration
def test_invalid_endpoint_returns_404(test_server: str) -> None:
    """Test that invalid endpoints return 404."""
    response = requests.get(f"{test_server}/invalid/endpoint", timeout=5)

    assert response.status_code == 404
