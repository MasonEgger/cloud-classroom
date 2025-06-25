"""
Modern async DigitalOcean API client using aiohttp and pydantic.

This replaces the legacy python-digitalocean library with a modern async implementation
that provides better performance, type safety, and error handling.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import aiohttp
import structlog
from django.conf import settings
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class DOError(Exception):
    """Base exception for DigitalOcean API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class DODroplet(BaseModel):
    """DigitalOcean Droplet model."""

    id: int
    name: str
    memory: int
    vcpus: int
    disk: int
    locked: bool
    status: str
    kernel: dict[str, Any] | None = None
    created_at: datetime
    features: list[str] = Field(default_factory=list)
    backup_ids: list[int] = Field(default_factory=list)
    snapshot_ids: list[int] = Field(default_factory=list)
    image: dict[str, Any]
    size: dict[str, Any]
    size_slug: str
    networks: dict[str, Any]
    region: dict[str, Any]
    tags: list[str] = Field(default_factory=list)
    volume_ids: list[str] = Field(default_factory=list)
    vpc_uuid: str | None = None

    @property
    def ip_address(self) -> str | None:
        """Get the public IPv4 address."""
        v4_networks = self.networks.get("v4", [])
        for network in v4_networks:
            if network.get("type") == "public":
                return network.get("ip_address")
        return None

    @property
    def private_ip_address(self) -> str | None:
        """Get the private IPv4 address."""
        v4_networks = self.networks.get("v4", [])
        for network in v4_networks:
            if network.get("type") == "private":
                return network.get("ip_address")
        return None


class DORegion(BaseModel):
    """DigitalOcean Region model."""

    name: str
    slug: str
    features: list[str] = Field(default_factory=list)
    available: bool
    sizes: list[str] = Field(default_factory=list)


class DOSize(BaseModel):
    """DigitalOcean Size model."""

    slug: str
    memory: int
    vcpus: int
    disk: int
    transfer: float
    price_monthly: float
    price_hourly: float
    regions: list[str] = Field(default_factory=list)
    available: bool
    description: str


class DOImage(BaseModel):
    """DigitalOcean Image model."""

    id: int | str
    name: str
    distribution: str
    slug: str | None = None
    public: bool
    regions: list[str] = Field(default_factory=list)
    min_disk_size: int
    size_gigabytes: float | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    status: str = "available"
    type: str = "snapshot"


class DOSSHKey(BaseModel):
    """DigitalOcean SSH Key model."""

    id: int
    fingerprint: str
    public_key: str
    name: str


class DigitalOceanClient:
    """
    Async DigitalOcean API client.
    
    Provides modern async interface to DigitalOcean API v2 with proper
    error handling, type safety, and logging.
    """

    def __init__(self, token: str | None = None) -> None:
        self.token = token or settings.DO_TOKEN
        self.base_url = "https://api.digitalocean.com/v2"
        self.session: aiohttp.ClientSession | None = None

        if not self.token:
            msg = "DigitalOcean API token is required"
            raise DOError(msg)

    async def __aenter__(self) -> DigitalOceanClient:
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self) -> None:
        """Ensure aiohttp session is created."""
        if self.session is None or self.session.closed:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "cloud-classroom/2.0",
            }
            connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
            timeout = aiohttp.ClientTimeout(total=30, connect=10)

            self.session = aiohttp.ClientSession(
                headers=headers,
                connector=connector,
                timeout=timeout,
                raise_for_status=False,
            )

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an async HTTP request to the DigitalOcean API."""
        await self._ensure_session()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        logger.info(
            "DO API request",
            method=method,
            url=url,
            data=data,
            params=params,
        )

        try:
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
            ) as response:
                response_data = await response.json()

                if response.status >= 400:
                    error_msg = response_data.get("message", "Unknown API error")
                    logger.error(
                        "DO API error",
                        status=response.status,
                        error=error_msg,
                        response_data=response_data,
                    )
                    raise DOError(error_msg, response.status)

                logger.info(
                    "DO API success",
                    status=response.status,
                    endpoint=endpoint,
                )

                return response_data

        except aiohttp.ClientError as e:
            logger.error("HTTP client error", error=str(e))
            raise DOError(f"HTTP client error: {e}") from e
        except TimeoutError as e:
            logger.error("Request timeout", endpoint=endpoint)
            raise DOError("Request timeout") from e

    # Droplet operations
    async def list_droplets(
        self,
        tag_name: str | None = None,
        name: str | None = None,
        per_page: int = 200,
    ) -> list[DODroplet]:
        """List all droplets, optionally filtered by tag or name."""
        params = {"per_page": per_page}
        if tag_name:
            params["tag_name"] = tag_name
        if name:
            params["name"] = name

        response = await self._request("GET", "/droplets", params=params)
        droplets_data = response.get("droplets", [])

        return [DODroplet(**droplet) for droplet in droplets_data]

    async def get_droplet(self, droplet_id: int) -> DODroplet:
        """Get a specific droplet by ID."""
        response = await self._request("GET", f"/droplets/{droplet_id}")
        droplet_data = response.get("droplet")

        if not droplet_data:
            raise DOError(f"Droplet {droplet_id} not found", 404)

        return DODroplet(**droplet_data)

    async def create_droplet(
        self,
        name: str,
        region: str,
        size: str,
        image: str | int,
        ssh_keys: list[str] | None = None,
        backups: bool = False,
        ipv6: bool = False,
        private_networking: bool = False,
        user_data: str | None = None,
        monitoring: bool = False,
        volumes: list[str] | None = None,
        tags: list[str] | None = None,
        vpc_uuid: str | None = None,
    ) -> DODroplet:
        """Create a new droplet."""
        data = {
            "name": name,
            "region": region,
            "size": size,
            "image": image,
            "ssh_keys": ssh_keys or [],
            "backups": backups,
            "ipv6": ipv6,
            "private_networking": private_networking,
            "monitoring": monitoring,
            "volumes": volumes or [],
            "tags": tags or [],
        }

        if user_data:
            data["user_data"] = user_data
        if vpc_uuid:
            data["vpc_uuid"] = vpc_uuid

        response = await self._request("POST", "/droplets", data=data)
        droplet_data = response.get("droplet")

        if not droplet_data:
            raise DOError("Failed to create droplet")

        return DODroplet(**droplet_data)

    async def delete_droplet(self, droplet_id: int) -> None:
        """Delete a droplet."""
        await self._request("DELETE", f"/droplets/{droplet_id}")
        logger.info("Droplet deleted", droplet_id=droplet_id)

    async def power_on_droplet(self, droplet_id: int) -> dict[str, Any]:
        """Power on a droplet."""
        data = {"type": "power_on"}
        response = await self._request(
            "POST",
            f"/droplets/{droplet_id}/actions",
            data=data
        )
        return response.get("action", {})

    async def power_off_droplet(self, droplet_id: int) -> dict[str, Any]:
        """Power off a droplet."""
        data = {"type": "power_off"}
        response = await self._request(
            "POST",
            f"/droplets/{droplet_id}/actions",
            data=data
        )
        return response.get("action", {})

    async def shutdown_droplet(self, droplet_id: int) -> dict[str, Any]:
        """Gracefully shutdown a droplet."""
        data = {"type": "shutdown"}
        response = await self._request(
            "POST",
            f"/droplets/{droplet_id}/actions",
            data=data
        )
        return response.get("action", {})

    async def reboot_droplet(self, droplet_id: int) -> dict[str, Any]:
        """Reboot a droplet."""
        data = {"type": "reboot"}
        response = await self._request(
            "POST",
            f"/droplets/{droplet_id}/actions",
            data=data
        )
        return response.get("action", {})

    # Resource information operations
    async def list_regions(self) -> list[DORegion]:
        """List all available regions."""
        response = await self._request("GET", "/regions")
        regions_data = response.get("regions", [])

        return [DORegion(**region) for region in regions_data]

    async def list_sizes(self) -> list[DOSize]:
        """List all available droplet sizes."""
        response = await self._request("GET", "/sizes")
        sizes_data = response.get("sizes", [])

        return [DOSize(**size) for size in sizes_data]

    async def list_images(
        self,
        image_type: str = "distribution",
        per_page: int = 200,
    ) -> list[DOImage]:
        """List available images."""
        params = {"type": image_type, "per_page": per_page}
        response = await self._request("GET", "/images", params=params)
        images_data = response.get("images", [])

        return [DOImage(**image) for image in images_data]

    async def list_ssh_keys(self) -> list[DOSSHKey]:
        """List SSH keys."""
        response = await self._request("GET", "/account/keys")
        keys_data = response.get("ssh_keys", [])

        return [DOSSHKey(**key) for key in keys_data]

    async def create_ssh_key(self, name: str, public_key: str) -> DOSSHKey:
        """Create a new SSH key."""
        data = {"name": name, "public_key": public_key}
        response = await self._request("POST", "/account/keys", data=data)
        key_data = response.get("ssh_key")

        if not key_data:
            raise DOError("Failed to create SSH key")

        return DOSSHKey(**key_data)

    async def delete_ssh_key(self, key_id: int | str) -> None:
        """Delete an SSH key."""
        await self._request("DELETE", f"/account/keys/{key_id}")
        logger.info("SSH key deleted", key_id=key_id)

    # Utility methods
    async def wait_for_droplet_active(
        self,
        droplet_id: int,
        max_wait: int = 300,
        check_interval: int = 5,
    ) -> DODroplet:
        """
        Wait for a droplet to become active.
        
        Args:
            droplet_id: The droplet ID to check
            max_wait: Maximum time to wait in seconds
            check_interval: How often to check status in seconds
            
        Returns:
            The active droplet
            
        Raises:
            DOError: If droplet doesn't become active within max_wait
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            droplet = await self.get_droplet(droplet_id)

            if droplet.status == "active":
                logger.info(
                    "Droplet became active",
                    droplet_id=droplet_id,
                    elapsed_time=asyncio.get_event_loop().time() - start_time,
                )
                return droplet

            if droplet.status == "errored":
                raise DOError(f"Droplet {droplet_id} failed to start")

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= max_wait:
                raise DOError(
                    f"Droplet {droplet_id} did not become active within {max_wait}s"
                )

            await asyncio.sleep(check_interval)

    async def get_available_regions_for_size(self, size_slug: str) -> list[str]:
        """Get regions where a specific size is available."""
        sizes = await self.list_sizes()
        for size in sizes:
            if size.slug == size_slug and size.available:
                return size.regions
        return []


# Convenience function for getting a client
async def get_do_client(token: str | None = None) -> DigitalOceanClient:
    """Get a configured DigitalOcean client."""
    client = DigitalOceanClient(token)
    await client._ensure_session()
    return client
