"""Tests for DigitalOcean REST API client."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiohttp import web

from cloud_classroom.models import ResourceTemplate
from cloud_classroom.services.digitalocean_client import DigitalOceanClient, DropletInfo, SyncDigitalOceanClient


@pytest.mark.unit  
def test_digitalocean_client_initialization() -> None:
    """Test DigitalOcean client initialization."""
    client = SyncDigitalOceanClient(token="test-token")
    assert client.async_client.token == "test-token"


@pytest.mark.unit
async def test_create_droplet_success(aiohttp_client: any) -> None:
    """Test successful droplet creation via REST API."""
    # Mock the HTTP response from DigitalOcean API
    mock_response_data = {
        "droplet": {
            "id": 12345,
            "name": "test-droplet",
            "status": "new",
            "size": {"slug": "s-1vcpu-1gb"},
            "image": {"slug": "ubuntu-22-04-x64"},
            "region": {"slug": "nyc3"},
            "networks": {
                "v4": [
                    {
                        "type": "public",
                        "ip_address": "192.168.1.100",
                        "netmask": "255.255.255.0",
                        "gateway": "192.168.1.1"
                    }
                ]
            }
        }
    }
    
    async def create_droplet_handler(request: web.Request) -> web.Response:
        """Mock handler for droplet creation."""
        return web.json_response(mock_response_data)
    
    # Create a mock web app
    app = web.Application()
    app.router.add_post('/v2/droplets', create_droplet_handler)
    
    # Create test client
    client_app = await aiohttp_client(app)
    
    # Patch the BASE_URL to use our test server
    with patch.object(DigitalOceanClient, 'BASE_URL', str(client_app.host).replace('http://', 'http://') + ':' + str(client_app.port)):
        client = DigitalOceanClient(token="test-token")
        
        # Override the base URL properly
        client.BASE_URL = f"http://{client_app.host}:{client_app.port}/v2"
        
        # Create a resource template
        template = ResourceTemplate(
            id=1,
            name="Test Server",
            droplet_size="s-1vcpu-1gb",
            droplet_image="ubuntu-22-04-x64",
            region="nyc3",
            user_data="#!/bin/bash\necho 'Hello World'",
            workshop_id=1,
        )
        
        result = await client.create_droplet(
            name="test-droplet",
            template=template,
            ssh_keys=[]
        )
        
        # Verify the result
        assert isinstance(result, DropletInfo)
        assert result.id == "12345"
        assert result.name == "test-droplet"
        assert result.ip_address == "192.168.1.100"
        assert result.status == "new"
        assert result.size == "s-1vcpu-1gb"
        assert result.image == "ubuntu-22-04-x64"
        assert result.region == "nyc3"


@pytest.mark.unit
async def test_get_droplet_success(aiohttp_client: any) -> None:
    """Test successful droplet retrieval via REST API."""
    mock_response_data = {
        "droplet": {
            "id": 12345,
            "name": "test-droplet",
            "status": "active",
            "size": {"slug": "s-1vcpu-1gb"},
            "image": {"slug": "ubuntu-22-04-x64"},
            "region": {"slug": "nyc3"},
            "networks": {
                "v4": [
                    {
                        "type": "public",
                        "ip_address": "192.168.1.100",
                        "netmask": "255.255.255.0",
                        "gateway": "192.168.1.1"
                    }
                ]
            }
        }
    }
    
    async def get_droplet_handler(request: web.Request) -> web.Response:
        """Mock handler for droplet retrieval."""
        return web.json_response(mock_response_data)
    
    # Create a mock web app
    app = web.Application()
    app.router.add_get('/v2/droplets/{droplet_id}', get_droplet_handler)
    
    # Create test client
    client_app = await aiohttp_client(app)
    
    client = DigitalOceanClient(token="test-token")
    client.BASE_URL = f"http://{client_app.host}:{client_app.port}/v2"
    
    result = await client.get_droplet("12345")
    
    assert isinstance(result, DropletInfo)
    assert result.id == "12345"
    assert result.status == "active"


@pytest.mark.unit
async def test_get_droplet_not_found(aiohttp_client: any) -> None:
    """Test droplet retrieval when droplet doesn't exist."""
    async def get_droplet_not_found_handler(request: web.Request) -> web.Response:
        """Mock handler for droplet not found."""
        return web.json_response({"message": "Not found"}, status=404)
    
    # Create a mock web app
    app = web.Application()
    app.router.add_get('/v2/droplets/{droplet_id}', get_droplet_not_found_handler)
    
    # Create test client
    client_app = await aiohttp_client(app)
    
    client = DigitalOceanClient(token="test-token")
    client.BASE_URL = f"http://{client_app.host}:{client_app.port}/v2"
    
    result = await client.get_droplet("99999")
    
    assert result is None


@pytest.mark.unit
async def test_start_droplet(aiohttp_client: any) -> None:
    """Test starting a droplet via REST API."""
    mock_response_data = {
        "action": {
            "id": 36804636,
            "status": "in-progress",
            "type": "power_on",
            "started_at": "2015-06-21T08:56:27Z",
            "completed_at": None,
            "resource_id": 12345,
            "resource_type": "droplet",
            "region": {"slug": "nyc3"},
            "region_slug": "nyc3"
        }
    }
    
    async def start_droplet_handler(request: web.Request) -> web.Response:
        """Mock handler for starting droplet."""
        return web.json_response(mock_response_data)
    
    # Create a mock web app
    app = web.Application()
    app.router.add_post('/v2/droplets/{droplet_id}/actions', start_droplet_handler)
    
    # Create test client
    client_app = await aiohttp_client(app)
    
    client = DigitalOceanClient(token="test-token")
    client.BASE_URL = f"http://{client_app.host}:{client_app.port}/v2"
    
    result = await client.start_droplet("12345")
    
    assert result is True


@pytest.mark.unit
async def test_stop_droplet(aiohttp_client: any) -> None:
    """Test stopping a droplet via REST API."""
    mock_response_data = {
        "action": {
            "id": 36804637,
            "status": "in-progress",
            "type": "shutdown",
            "started_at": "2015-06-21T08:56:27Z",
            "completed_at": None,
            "resource_id": 12345,
            "resource_type": "droplet"
        }
    }
    
    async def stop_droplet_handler(request: web.Request) -> web.Response:
        """Mock handler for stopping droplet."""
        return web.json_response(mock_response_data)
    
    # Create a mock web app
    app = web.Application()
    app.router.add_post('/v2/droplets/{droplet_id}/actions', stop_droplet_handler)
    
    # Create test client
    client_app = await aiohttp_client(app)
    
    client = DigitalOceanClient(token="test-token")
    client.BASE_URL = f"http://{client_app.host}:{client_app.port}/v2"
    
    result = await client.stop_droplet("12345")
    
    assert result is True


@pytest.mark.unit
async def test_destroy_droplet(aiohttp_client: any) -> None:
    """Test destroying a droplet via REST API."""
    async def destroy_droplet_handler(request: web.Request) -> web.Response:
        """Mock handler for destroying droplet."""
        return web.Response(status=204)  # No content response
    
    # Create a mock web app  
    app = web.Application()
    app.router.add_delete('/v2/droplets/{droplet_id}', destroy_droplet_handler)
    
    # Create test client
    client_app = await aiohttp_client(app)
    
    client = DigitalOceanClient(token="test-token")
    client.BASE_URL = f"http://{client_app.host}:{client_app.port}/v2"
    
    result = await client.destroy_droplet("12345")
    
    assert result is True


@pytest.mark.unit
async def test_list_droplets(aiohttp_client: any) -> None:
    """Test listing droplets via REST API."""
    mock_response_data = {
        "droplets": [
            {
                "id": 12345,
                "name": "droplet-1",
                "status": "active",
                "size": {"slug": "s-1vcpu-1gb"},
                "image": {"slug": "ubuntu-22-04-x64"},
                "region": {"slug": "nyc3"},
                "networks": {
                    "v4": [{"type": "public", "ip_address": "192.168.1.100"}]
                }
            },
            {
                "id": 67890,
                "name": "droplet-2",
                "status": "off",
                "size": {"slug": "s-2vcpu-2gb"},
                "image": {"slug": "ubuntu-22-04-x64"},
                "region": {"slug": "sfo3"},
                "networks": {
                    "v4": [{"type": "public", "ip_address": "192.168.1.101"}]
                }
            }
        ]
    }
    
    async def list_droplets_handler(request: web.Request) -> web.Response:
        """Mock handler for listing droplets."""
        return web.json_response(mock_response_data)
    
    # Create a mock web app
    app = web.Application()
    app.router.add_get('/v2/droplets', list_droplets_handler)
    
    # Create test client
    client_app = await aiohttp_client(app)
    
    client = DigitalOceanClient(token="test-token")
    client.BASE_URL = f"http://{client_app.host}:{client_app.port}/v2"
    
    result = await client.list_droplets()
    
    assert len(result) == 2
    assert result[0].id == "12345"
    assert result[0].name == "droplet-1"
    assert result[1].id == "67890"
    assert result[1].name == "droplet-2"


@pytest.mark.unit
async def test_get_account_info(aiohttp_client: any) -> None:
    """Test getting account information via REST API."""
    mock_response_data = {
        "account": {
            "droplet_limit": 25,
            "floating_ip_limit": 5,
            "volume_limit": 10,
            "email": "test@example.com",
            "status": "active"
        }
    }
    
    async def get_account_handler(request: web.Request) -> web.Response:
        """Mock handler for account information."""
        return web.json_response(mock_response_data)
    
    # Create a mock web app
    app = web.Application()
    app.router.add_get('/v2/account', get_account_handler)
    
    # Create test client
    client_app = await aiohttp_client(app)
    
    client = DigitalOceanClient(token="test-token")
    client.BASE_URL = f"http://{client_app.host}:{client_app.port}/v2"
    
    result = await client.get_account_info()
    
    assert result["droplet_limit"] == 25
    assert result["email"] == "test@example.com"
    assert result["status"] == "active"


@pytest.mark.unit
def test_sync_wrapper() -> None:
    """Test the synchronous wrapper around async client."""
    with patch("cloud_classroom.services.digitalocean_client.run_async") as mock_run_async:
        mock_droplet = DropletInfo("123", "test", "1.2.3.4", "active", "s-1vcpu-1gb", "ubuntu-22-04-x64", "nyc3")
        mock_run_async.return_value = mock_droplet
        
        client = SyncDigitalOceanClient(token="test-token")
        result = client.get_droplet("123")
        
        assert result == mock_droplet
        mock_run_async.assert_called_once()