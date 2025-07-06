"""Tests for the main FastAPI application."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_root_endpoint(client: TestClient) -> None:
    """Test root endpoint returns welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Cloud Classroom"}


@pytest.mark.unit
def test_health_endpoint(client: TestClient) -> None:
    """Test health endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
