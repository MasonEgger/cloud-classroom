"""DigitalOcean API client using REST API with aiohttp."""

import asyncio
import json
from typing import Dict, List, Optional, Any

import aiohttp
from aiohttp import ClientSession, ClientTimeout


class DropletInfo:
    """Information about a DigitalOcean droplet."""
    
    def __init__(
        self,
        id: str,
        name: str,
        ip_address: Optional[str],
        status: str,
        size: str,
        image: str,
        region: str,
    ) -> None:
        """Initialize droplet info."""
        self.id = id
        self.name = name
        self.ip_address = ip_address
        self.status = status
        self.size = size
        self.image = image
        self.region = region


class DigitalOceanClient:
    """Async client for DigitalOcean API v2."""
    
    BASE_URL = "https://api.digitalocean.com/v2"
    
    def __init__(self, token: str) -> None:
        """Initialize the DigitalOcean client."""
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self.timeout = ClientTimeout(total=30)
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an async HTTP request to the DigitalOcean API."""
        url = f"{self.BASE_URL}{endpoint}"
        
        async with ClientSession(timeout=self.timeout) as session:
            kwargs: Dict[str, Any] = {
                "headers": self.headers,
            }
            
            if data is not None:
                kwargs["data"] = json.dumps(data)
            
            async with session.request(method, url, **kwargs) as response:
                if response.status >= 400:
                    try:
                        error_data = await response.json()
                        error_message = error_data.get("message", f"HTTP {response.status}")
                    except Exception:
                        error_message = f"HTTP {response.status}"
                    raise Exception(f"DigitalOcean API error: {error_message}")
                
                # Handle responses with no content (like 204)
                if response.status == 204 or response.content_length == 0:
                    return {}
                
                response_data: Dict[str, Any] = await response.json()
                return response_data
    
    async def create_droplet(
        self,
        name: str,
        template: Any,  # ResourceTemplate object
        ssh_keys: List[str],
    ) -> DropletInfo:
        """Create a new droplet using the specified template."""
        # Prepare the request data
        droplet_data = {
            "name": name,
            "region": template.region,
            "size": template.droplet_size,
            "image": template.droplet_image,
            "ssh_keys": ssh_keys,
            "backups": False,
            "ipv6": False,
            "monitoring": True,
            "user_data": template.user_data,
        }
        
        # Remove None values
        droplet_data = {k: v for k, v in droplet_data.items() if v is not None}
        
        response = await self._make_request("POST", "/droplets", {"type": "regular", **droplet_data})
        
        droplet = response["droplet"]
        
        # Get IP address from networks
        ip_address = None
        if droplet.get("networks", {}).get("v4"):
            for network in droplet["networks"]["v4"]:
                if network["type"] == "public":
                    ip_address = network["ip_address"]
                    break
        
        return DropletInfo(
            id=str(droplet["id"]),
            name=droplet["name"],
            ip_address=ip_address,
            status=droplet["status"],
            size=droplet["size"]["slug"],
            image=droplet["image"]["slug"],
            region=droplet["region"]["slug"],
        )
    
    async def get_droplet(self, droplet_id: str) -> Optional[DropletInfo]:
        """Get information about a specific droplet."""
        try:
            response = await self._make_request("GET", f"/droplets/{droplet_id}")
            droplet = response["droplet"]
            
            # Get IP address from networks
            ip_address = None
            if droplet.get("networks", {}).get("v4"):
                for network in droplet["networks"]["v4"]:
                    if network["type"] == "public":
                        ip_address = network["ip_address"]
                        break
            
            return DropletInfo(
                id=str(droplet["id"]),
                name=droplet["name"],
                ip_address=ip_address,
                status=droplet["status"],
                size=droplet["size"]["slug"],
                image=droplet["image"]["slug"],
                region=droplet["region"]["slug"],
            )
        except Exception:
            # Droplet not found or other error
            return None
    
    async def start_droplet(self, droplet_id: str) -> bool:
        """Start a stopped droplet."""
        try:
            await self._make_request(
                "POST", 
                f"/droplets/{droplet_id}/actions",
                {"type": "power_on"}
            )
            return True
        except Exception:
            return False
    
    async def stop_droplet(self, droplet_id: str) -> bool:
        """Stop a running droplet."""
        try:
            await self._make_request(
                "POST",
                f"/droplets/{droplet_id}/actions", 
                {"type": "shutdown"}
            )
            return True
        except Exception:
            return False
    
    async def destroy_droplet(self, droplet_id: str) -> bool:
        """Destroy a droplet permanently."""
        try:
            await self._make_request("DELETE", f"/droplets/{droplet_id}")
            return True
        except Exception:
            return False
    
    async def list_droplets(self) -> List[DropletInfo]:
        """List all droplets in the account."""
        try:
            response = await self._make_request("GET", "/droplets")
            droplets = response["droplets"]
            
            result = []
            for droplet in droplets:
                # Get IP address from networks
                ip_address = None
                if droplet.get("networks", {}).get("v4"):
                    for network in droplet["networks"]["v4"]:
                        if network["type"] == "public":
                            ip_address = network["ip_address"]
                            break
                
                result.append(DropletInfo(
                    id=str(droplet["id"]),
                    name=droplet["name"],
                    ip_address=ip_address,
                    status=droplet["status"],
                    size=droplet["size"]["slug"],
                    image=droplet["image"]["slug"],
                    region=droplet["region"]["slug"],
                ))
            
            return result
        except Exception:
            return []
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information for cost tracking."""
        try:
            response = await self._make_request("GET", "/account")
            account = response["account"]
            
            return {
                "droplet_limit": account.get("droplet_limit", 0),
                "floating_ip_limit": account.get("floating_ip_limit", 0),
                "volume_limit": account.get("volume_limit", 0),
                "email": account.get("email", ""),
                "status": account.get("status", ""),
            }
        except Exception:
            return {
                "droplet_limit": 0,
                "floating_ip_limit": 0,
                "volume_limit": 0,
                "email": "",
                "status": "unknown",
            }


# Sync wrapper functions for use in non-async contexts
def run_async(coro: Any) -> Any:
    """Run an async coroutine in a sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


class SyncDigitalOceanClient:
    """Synchronous wrapper around the async DigitalOcean client."""
    
    def __init__(self, token: str) -> None:
        """Initialize the sync wrapper."""
        self.async_client = DigitalOceanClient(token)
    
    def create_droplet(
        self,
        name: str,
        template: Any,
        ssh_keys: List[str],
    ) -> DropletInfo:
        """Create a new droplet (sync wrapper)."""
        result: DropletInfo = run_async(self.async_client.create_droplet(name, template, ssh_keys))
        return result
    
    def get_droplet(self, droplet_id: str) -> Optional[DropletInfo]:
        """Get droplet information (sync wrapper)."""
        result: Optional[DropletInfo] = run_async(self.async_client.get_droplet(droplet_id))
        return result
    
    def start_droplet(self, droplet_id: str) -> bool:
        """Start a droplet (sync wrapper)."""
        result: bool = run_async(self.async_client.start_droplet(droplet_id))
        return result
    
    def stop_droplet(self, droplet_id: str) -> bool:
        """Stop a droplet (sync wrapper)."""
        result: bool = run_async(self.async_client.stop_droplet(droplet_id))
        return result
    
    def destroy_droplet(self, droplet_id: str) -> bool:
        """Destroy a droplet (sync wrapper)."""
        result: bool = run_async(self.async_client.destroy_droplet(droplet_id))
        return result
    
    def list_droplets(self) -> List[DropletInfo]:
        """List all droplets (sync wrapper)."""
        result: List[DropletInfo] = run_async(self.async_client.list_droplets())
        return result
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information (sync wrapper)."""
        result: Dict[str, Any] = run_async(self.async_client.get_account_info())
        return result