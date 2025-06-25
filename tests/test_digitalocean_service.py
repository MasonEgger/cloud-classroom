"""
Tests for the async DigitalOcean API client.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp

from services.digitalocean import (
    DigitalOceanClient,
    DOError,
    DODroplet,
    DORegion,
    DOSize,
    DOImage,
    DOSSHKey,
)


class TestDigitalOceanClient:
    """Test suite for DigitalOceanClient."""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization with token."""
        client = DigitalOceanClient("test_token")
        assert client.token == "test_token"
        assert client.base_url == "https://api.digitalocean.com/v2"
        assert client.session is None

    @pytest.mark.asyncio
    async def test_client_initialization_no_token(self):
        """Test client initialization without token raises error."""
        with patch("services.digitalocean.settings") as mock_settings:
            mock_settings.DO_TOKEN = None
            with pytest.raises(DOError, match="DigitalOcean API token is required"):
                DigitalOceanClient()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        with patch("services.digitalocean.settings") as mock_settings:
            mock_settings.DO_TOKEN = "test_token"
            
            async with DigitalOceanClient() as client:
                assert client.session is not None
                assert not client.session.closed
            
            # Session should be closed after exiting context
            assert client.session.closed

    @pytest.mark.asyncio
    async def test_request_success(self):
        """Test successful API request."""
        mock_response_data = {"droplets": [{"id": 123, "name": "test"}]}
        
        with patch("aiohttp.ClientSession.request") as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            mock_request.return_value.__aenter__.return_value = mock_response
            
            client = DigitalOceanClient("test_token")
            result = await client._request("GET", "/droplets")
            
            assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_request_api_error(self):
        """Test API error handling."""
        error_response = {"id": "Unauthorized", "message": "Unable to authenticate you"}
        
        with patch("aiohttp.ClientSession.request") as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_response.json.return_value = error_response
            mock_request.return_value.__aenter__.return_value = mock_response
            
            client = DigitalOceanClient("test_token")
            
            with pytest.raises(DOError) as exc_info:
                await client._request("GET", "/droplets")
            
            assert exc_info.value.status_code == 401
            assert "Unable to authenticate you" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_request_client_error(self):
        """Test aiohttp client error handling."""
        with patch("aiohttp.ClientSession.request") as mock_request:
            mock_request.side_effect = aiohttp.ClientError("Connection failed")
            
            client = DigitalOceanClient("test_token")
            
            with pytest.raises(DOError, match="HTTP client error"):
                await client._request("GET", "/droplets")

    @pytest.mark.asyncio
    async def test_list_droplets(self):
        """Test listing droplets."""
        mock_response = {
            "droplets": [
                {
                    "id": 123,
                    "name": "test-droplet",
                    "memory": 1024,
                    "vcpus": 1,
                    "disk": 25,
                    "locked": False,
                    "status": "active",
                    "created_at": "2024-01-01T00:00:00Z",
                    "features": [],
                    "backup_ids": [],
                    "snapshot_ids": [],
                    "image": {"slug": "ubuntu-22-04-x64"},
                    "size": {"slug": "s-1vcpu-1gb"},
                    "size_slug": "s-1vcpu-1gb",
                    "networks": {
                        "v4": [{"type": "public", "ip_address": "192.168.1.1"}]
                    },
                    "region": {"slug": "nyc1"},
                    "tags": [],
                    "volume_ids": [],
                }
            ]
        }
        
        client = DigitalOceanClient("test_token")
        with patch.object(client, "_request", return_value=mock_response):
            droplets = await client.list_droplets()
            
            assert len(droplets) == 1
            assert isinstance(droplets[0], DODroplet)
            assert droplets[0].id == 123
            assert droplets[0].name == "test-droplet"
            assert droplets[0].ip_address == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_get_droplet(self):
        """Test getting a specific droplet."""
        mock_response = {
            "droplet": {
                "id": 123,
                "name": "test-droplet",
                "memory": 1024,
                "vcpus": 1,
                "disk": 25,
                "locked": False,
                "status": "active",
                "created_at": "2024-01-01T00:00:00Z",
                "features": [],
                "backup_ids": [],
                "snapshot_ids": [],
                "image": {"slug": "ubuntu-22-04-x64"},
                "size": {"slug": "s-1vcpu-1gb"},
                "size_slug": "s-1vcpu-1gb",
                "networks": {
                    "v4": [{"type": "public", "ip_address": "192.168.1.1"}]
                },
                "region": {"slug": "nyc1"},
                "tags": [],
                "volume_ids": [],
            }
        }
        
        client = DigitalOceanClient("test_token")
        with patch.object(client, "_request", return_value=mock_response):
            droplet = await client.get_droplet(123)
            
            assert isinstance(droplet, DODroplet)
            assert droplet.id == 123
            assert droplet.ip_address == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_get_droplet_not_found(self):
        """Test getting a non-existent droplet."""
        mock_response = {"droplet": None}
        
        client = DigitalOceanClient("test_token")
        with patch.object(client, "_request", return_value=mock_response):
            with pytest.raises(DOError, match="Droplet 123 not found"):
                await client.get_droplet(123)

    @pytest.mark.asyncio
    async def test_create_droplet(self):
        """Test creating a droplet."""
        mock_response = {
            "droplet": {
                "id": 123,
                "name": "new-droplet",
                "memory": 1024,
                "vcpus": 1,
                "disk": 25,
                "locked": False,
                "status": "new",
                "created_at": "2024-01-01T00:00:00Z",
                "features": [],
                "backup_ids": [],
                "snapshot_ids": [],
                "image": {"slug": "ubuntu-22-04-x64"},
                "size": {"slug": "s-1vcpu-1gb"},
                "size_slug": "s-1vcpu-1gb",
                "networks": {"v4": []},
                "region": {"slug": "nyc1"},
                "tags": ["test"],
                "volume_ids": [],
            }
        }
        
        client = DigitalOceanClient("test_token")
        with patch.object(client, "_request", return_value=mock_response) as mock_req:
            droplet = await client.create_droplet(
                name="new-droplet",
                region="nyc1",
                size="s-1vcpu-1gb",
                image="ubuntu-22-04-x64",
                tags=["test"],
            )
            
            assert isinstance(droplet, DODroplet)
            assert droplet.id == 123
            assert droplet.name == "new-droplet"
            
            # Verify the request was made with correct data
            mock_req.assert_called_once()
            args, kwargs = mock_req.call_args
            assert args == ("POST", "/droplets")
            assert kwargs["data"]["name"] == "new-droplet"
            assert kwargs["data"]["region"] == "nyc1"
            assert kwargs["data"]["tags"] == ["test"]

    @pytest.mark.asyncio
    async def test_delete_droplet(self):
        """Test deleting a droplet."""
        client = DigitalOceanClient("test_token")
        with patch.object(client, "_request") as mock_req:
            await client.delete_droplet(123)
            mock_req.assert_called_once_with("DELETE", "/droplets/123")

    @pytest.mark.asyncio
    async def test_list_regions(self):
        """Test listing regions."""
        mock_response = {
            "regions": [
                {
                    "name": "New York 1",
                    "slug": "nyc1",
                    "features": ["virtio", "metadata"],
                    "available": True,
                    "sizes": ["s-1vcpu-1gb"],
                }
            ]
        }
        
        client = DigitalOceanClient("test_token")
        with patch.object(client, "_request", return_value=mock_response):
            regions = await client.list_regions()
            
            assert len(regions) == 1
            assert isinstance(regions[0], DORegion)
            assert regions[0].slug == "nyc1"
            assert regions[0].name == "New York 1"

    @pytest.mark.asyncio
    async def test_wait_for_droplet_active(self):
        """Test waiting for droplet to become active."""
        # Mock progression from "new" to "active"
        mock_droplets = [
            MagicMock(status="new"),
            MagicMock(status="active"),
        ]
        
        client = DigitalOceanClient("test_token")
        with patch.object(client, "get_droplet", side_effect=mock_droplets):
            with patch("asyncio.sleep"):  # Speed up the test
                result = await client.wait_for_droplet_active(123, max_wait=10, check_interval=1)
                assert result.status == "active"

    @pytest.mark.asyncio
    async def test_wait_for_droplet_timeout(self):
        """Test timeout when waiting for droplet."""
        mock_droplet = MagicMock(status="new")
        
        client = DigitalOceanClient("test_token")
        with patch.object(client, "get_droplet", return_value=mock_droplet):
            with patch("asyncio.sleep"):  # Speed up the test
                with pytest.raises(DOError, match="did not become active within"):
                    await client.wait_for_droplet_active(123, max_wait=1, check_interval=1)

    @pytest.mark.asyncio
    async def test_wait_for_droplet_error(self):
        """Test error state when waiting for droplet."""
        mock_droplet = MagicMock(status="errored")
        
        client = DigitalOceanClient("test_token")
        with patch.object(client, "get_droplet", return_value=mock_droplet):
            with pytest.raises(DOError, match="failed to start"):
                await client.wait_for_droplet_active(123)


class TestDOModels:
    """Test suite for DigitalOcean pydantic models."""

    def test_do_droplet_ip_address_property(self):
        """Test DODroplet ip_address property."""
        droplet_data = {
            "id": 123,
            "name": "test",
            "memory": 1024,
            "vcpus": 1,
            "disk": 25,
            "locked": False,
            "status": "active",
            "created_at": "2024-01-01T00:00:00Z",
            "image": {"slug": "ubuntu-22-04-x64"},
            "size": {"slug": "s-1vcpu-1gb"},
            "size_slug": "s-1vcpu-1gb",
            "networks": {
                "v4": [
                    {"type": "public", "ip_address": "192.168.1.1"},
                    {"type": "private", "ip_address": "10.0.0.1"},
                ]
            },
            "region": {"slug": "nyc1"},
        }
        
        droplet = DODroplet(**droplet_data)
        assert droplet.ip_address == "192.168.1.1"
        assert droplet.private_ip_address == "10.0.0.1"

    def test_do_droplet_no_ip_address(self):
        """Test DODroplet with no IP addresses."""
        droplet_data = {
            "id": 123,
            "name": "test",
            "memory": 1024,
            "vcpus": 1,
            "disk": 25,
            "locked": False,
            "status": "new",
            "created_at": "2024-01-01T00:00:00Z",
            "image": {"slug": "ubuntu-22-04-x64"},
            "size": {"slug": "s-1vcpu-1gb"},
            "size_slug": "s-1vcpu-1gb",
            "networks": {"v4": []},
            "region": {"slug": "nyc1"},
        }
        
        droplet = DODroplet(**droplet_data)
        assert droplet.ip_address is None
        assert droplet.private_ip_address is None