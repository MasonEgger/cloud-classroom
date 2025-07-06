"""Tests for DigitalOcean client error handling and edge cases."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiohttp import ClientError, ClientResponseError, web

from cloud_classroom.services.digitalocean_client import DigitalOceanClient, SyncDigitalOceanClient


@pytest.mark.unit
async def test_digitalocean_client_request_timeout(aiohttp_client: any) -> None:
    """Test DigitalOcean client handling of request timeouts."""
    # Create a slow handler that will timeout
    async def slow_handler(request: web.Request) -> web.Response:
        import asyncio
        await asyncio.sleep(2)  # Simulate slow response
        return web.json_response({"message": "success"})
    
    app = web.Application()
    app.router.add_get('/v2/account', slow_handler)
    client_app = await aiohttp_client(app)
    
    # Create client with very short timeout
    client = DigitalOceanClient(
        api_token="test_token",
        base_url=str(client_app.make_url("/")),
        timeout=0.1  # 100ms timeout
    )
    
    # Request should timeout
    with pytest.raises(Exception):  # Will be a timeout or client error
        await client.get_account_info()


@pytest.mark.unit
async def test_digitalocean_client_network_error(aiohttp_client: any) -> None:
    """Test DigitalOcean client handling of network errors."""
    # Create client pointing to non-existent host
    client = DigitalOceanClient(
        api_token="test_token",
        base_url="http://non-existent-host.invalid/",
        timeout=1.0
    )
    
    # Request should fail with network error
    with pytest.raises(Exception):  # Will be a connection error
        await client.get_account_info()


@pytest.mark.unit
async def test_digitalocean_client_invalid_json_response(aiohttp_client: any) -> None:
    """Test DigitalOcean client handling of invalid JSON responses."""
    async def invalid_json_handler(request: web.Request) -> web.Response:
        return web.Response(text="invalid json {", content_type="application/json")
    
    app = web.Application()
    app.router.add_get('/v2/account', invalid_json_handler)
    client_app = await aiohttp_client(app)
    
    client = DigitalOceanClient(
        api_token="test_token",
        base_url=str(client_app.make_url("/"))
    )
    
    # Should handle invalid JSON gracefully
    with pytest.raises(Exception):  # JSON decode error
        await client.get_account_info()


@pytest.mark.unit
async def test_digitalocean_client_http_error_responses(aiohttp_client: any) -> None:
    """Test DigitalOcean client handling of HTTP error status codes."""
    async def error_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {"id": "unauthorized", "message": "Unable to authenticate you."},
            status=401
        )
    
    app = web.Application()
    app.router.add_get('/v2/account', error_handler)
    client_app = await aiohttp_client(app)
    
    client = DigitalOceanClient(
        api_token="test_token",
        base_url=str(client_app.make_url("/"))
    )
    
    # Should raise exception for HTTP error
    with pytest.raises(ClientResponseError):
        await client.get_account_info()


@pytest.mark.unit
async def test_digitalocean_client_empty_response_handling(aiohttp_client: any) -> None:
    """Test DigitalOcean client handling of empty responses."""
    async def empty_handler(request: web.Request) -> web.Response:
        return web.Response(status=204)  # No content
    
    app = web.Application()
    app.router.add_delete('/v2/droplets/12345', empty_handler)
    client_app = await aiohttp_client(app)
    
    client = DigitalOceanClient(
        api_token="test_token",
        base_url=str(client_app.make_url("/"))
    )
    
    # Should handle empty response correctly
    result = await client.destroy_droplet("12345")
    assert result is True


@pytest.mark.unit
async def test_digitalocean_client_malformed_droplet_data(aiohttp_client: any) -> None:
    """Test DigitalOcean client handling of malformed droplet data."""
    async def malformed_handler(request: web.Request) -> web.Response:
        return web.json_response({
            "droplet": {
                "id": "not_an_integer",  # Invalid ID type
                "name": "test-droplet",
                "networks": {
                    "v4": [{"ip_address": "192.168.1.100", "type": "public"}]
                },
                "status": "active",
                "size": {},  # Missing size slug
                "image": {},  # Missing image slug
                "region": {}  # Missing region slug
            }
        })
    
    app = web.Application()
    app.router.add_get('/v2/droplets/12345', malformed_handler)
    client_app = await aiohttp_client(app)
    
    client = DigitalOceanClient(
        api_token="test_token",
        base_url=str(client_app.make_url("/"))
    )
    
    # Should handle malformed data gracefully
    result = await client.get_droplet("12345")
    assert result is not None
    assert result.name == "test-droplet"
    assert result.ip_address == "192.168.1.100"


@pytest.mark.unit
async def test_digitalocean_client_missing_droplet_fields(aiohttp_client: any) -> None:
    """Test DigitalOcean client handling of missing required droplet fields."""
    async def missing_fields_handler(request: web.Request) -> web.Response:
        return web.json_response({
            "droplet": {
                "id": 12345,
                # Missing name, networks, status, size, image, region
            }
        })
    
    app = web.Application()
    app.router.add_get('/v2/droplets/12345', missing_fields_handler)
    client_app = await aiohttp_client(app)
    
    client = DigitalOceanClient(
        api_token="test_token",
        base_url=str(client_app.make_url("/"))
    )
    
    # Should handle missing fields gracefully
    result = await client.get_droplet("12345")
    assert result is not None
    assert result.id == "12345"
    assert result.name == "Unknown"
    assert result.ip_address is None


@pytest.mark.unit
def test_sync_digitalocean_client_initialization() -> None:
    """Test SyncDigitalOceanClient initialization."""
    client = SyncDigitalOceanClient(api_token="test_token")
    assert client.api_token == "test_token"
    assert client.timeout == 30.0  # Default timeout


@pytest.mark.unit
def test_sync_digitalocean_client_create_droplet_error() -> None:
    """Test SyncDigitalOceanClient create_droplet with async client error."""
    client = SyncDigitalOceanClient(api_token="test_token")
    
    # Mock the async client to raise an exception
    mock_async_client = AsyncMock()
    mock_async_client.create_droplet.side_effect = Exception("API Error")
    
    with patch.object(client, '_get_async_client', return_value=mock_async_client):
        with pytest.raises(Exception, match="API Error"):
            client.create_droplet(
                name="test-droplet",
                size="s-1vcpu-1gb",
                image="ubuntu-22-04-x64",
                region="nyc3"
            )


@pytest.mark.unit
def test_sync_digitalocean_client_get_droplet_error() -> None:
    """Test SyncDigitalOceanClient get_droplet with async client error."""
    client = SyncDigitalOceanClient(api_token="test_token")
    
    # Mock the async client to raise an exception
    mock_async_client = AsyncMock()
    mock_async_client.get_droplet.side_effect = Exception("API Error")
    
    with patch.object(client, '_get_async_client', return_value=mock_async_client):
        with pytest.raises(Exception, match="API Error"):
            client.get_droplet("12345")


@pytest.mark.unit
def test_sync_digitalocean_client_start_droplet_error() -> None:
    """Test SyncDigitalOceanClient start_droplet with async client error."""
    client = SyncDigitalOceanClient(api_token="test_token")
    
    # Mock the async client to raise an exception
    mock_async_client = AsyncMock()
    mock_async_client.start_droplet.side_effect = Exception("API Error")
    
    with patch.object(client, '_get_async_client', return_value=mock_async_client):
        result = client.start_droplet("12345")
        # Error should be caught and return False
        assert result is False


@pytest.mark.unit
def test_sync_digitalocean_client_stop_droplet_error() -> None:
    """Test SyncDigitalOceanClient stop_droplet with async client error."""
    client = SyncDigitalOceanClient(api_token="test_token")
    
    # Mock the async client to raise an exception
    mock_async_client = AsyncMock()
    mock_async_client.stop_droplet.side_effect = Exception("API Error")
    
    with patch.object(client, '_get_async_client', return_value=mock_async_client):
        result = client.stop_droplet("12345")
        # Error should be caught and return False
        assert result is False


@pytest.mark.unit
def test_sync_digitalocean_client_destroy_droplet_error() -> None:
    """Test SyncDigitalOceanClient destroy_droplet with async client error."""
    client = SyncDigitalOceanClient(api_token="test_token")
    
    # Mock the async client to raise an exception
    mock_async_client = AsyncMock()
    mock_async_client.destroy_droplet.side_effect = Exception("API Error")
    
    with patch.object(client, '_get_async_client', return_value=mock_async_client):
        result = client.destroy_droplet("12345")
        # Error should be caught and return False
        assert result is False


@pytest.mark.unit
async def test_digitalocean_client_list_droplets_pagination_error(aiohttp_client: any) -> None:
    """Test DigitalOcean client handling of pagination errors."""
    async def pagination_error_handler(request: web.Request) -> web.Response:
        return web.json_response({
            "droplets": [],
            "links": {
                "pages": {
                    "next": "invalid_url_format"  # Invalid URL
                }
            }
        })
    
    app = web.Application()
    app.router.add_get('/v2/droplets', pagination_error_handler)
    client_app = await aiohttp_client(app)
    
    client = DigitalOceanClient(
        api_token="test_token",
        base_url=str(client_app.make_url("/"))
    )
    
    # Should handle pagination gracefully and return what was retrieved
    result = await client.list_droplets()
    assert result == []


@pytest.mark.unit
async def test_digitalocean_client_account_info_missing_fields(aiohttp_client: any) -> None:
    """Test DigitalOcean client handling of account info with missing fields."""
    async def missing_account_fields_handler(request: web.Request) -> web.Response:
        return web.json_response({
            "account": {
                # Missing email, droplet_limit, floating_ip_limit, status
                "uuid": "test-uuid"
            }
        })
    
    app = web.Application()
    app.router.add_get('/v2/account', missing_account_fields_handler)
    client_app = await aiohttp_client(app)
    
    client = DigitalOceanClient(
        api_token="test_token",
        base_url=str(client_app.make_url("/"))
    )
    
    # Should handle missing fields gracefully
    result = await client.get_account_info()
    assert result is not None
    assert "uuid" in result
    assert result["uuid"] == "test-uuid"