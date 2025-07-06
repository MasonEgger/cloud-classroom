"""Shared test fixtures."""

import socket
import time
from collections.abc import Generator
from multiprocessing import Process

import pytest
import requests
import uvicorn
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from cloud_classroom.database import Base, get_db
from cloud_classroom.main import create_app

# Create test database
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    """Override database dependency for tests."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Create a fresh database for each test."""
    # Create tables
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    yield db

    db.close()
    # Drop all tables after test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db: Session) -> TestClient:
    """Create test client with database override.

    The db fixture ensures database is created before client initialization.
    """
    # Ensure db fixture is evaluated (creates tables)
    assert db is not None

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    return TestClient(app)


def find_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="function")
def server_port() -> int:
    """Get a free port for the test server."""
    return find_free_port()


@pytest.fixture(scope="function")
def test_server(server_port: int) -> Generator[str, None, None]:
    """Start a test server and return its base URL."""

    def run_server() -> None:
        # Create tables in test database
        Base.metadata.create_all(bind=engine)

        app = create_app()
        # Override database dependency for integration tests
        app.dependency_overrides[get_db] = override_get_db
        uvicorn.run(app, host="127.0.0.1", port=server_port, log_level="error")

    # Start server in separate process
    server_process = Process(target=run_server)
    server_process.start()

    base_url = f"http://127.0.0.1:{server_port}"

    # Wait for server to start
    max_attempts = 20
    for _ in range(max_attempts):
        try:
            response = requests.get(f"{base_url}/health", timeout=1)
            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            time.sleep(0.1)
    else:
        server_process.terminate()
        server_process.join(timeout=5)
        pytest.fail("Server failed to start within timeout")

    try:
        yield base_url
    finally:
        # Clean up server
        server_process.terminate()
        server_process.join(timeout=5)
        if server_process.is_alive():
            server_process.kill()
            server_process.join()

        # Clean up test database
        Base.metadata.drop_all(bind=engine)
