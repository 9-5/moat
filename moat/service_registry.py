import asyncio
from typing import Dict, Optional, Tuple

class ServiceRegistry:
    def __init__(self):
        # Stores hostname -> (target_url, source_type, optional_id)
        # source_type can be 'static' or 'docker'
        # optional_id can be container_id for docker services
        self._services: Dict[str, Tuple[str, str, Optional[str]]] = {}
        self._lock = asyncio.Lock()

    async def add_service(self, hostname: str, target_url: str, source_type: str = "static", container_id: Optional[str] = None):
        async with self._lock:
            self._services[hostname] = (target_url, source_type, container_id)
            print(f"Service Registry: Added/Updated {hostname} -> {target_url} (source: {source_type})")

    async def remove_service(self, hostname: str):
        async with self._lock:
            if hostname in self._services:
                del self._services[hostname]
                print(f"Service Registry: Removed {hostname}")

    async def remove_services_by_container_id(self, container_id: str):
        async with self._lock:
            to_remove = [hostname for hostname, (_, source, cid) in self._services.items() if source == "docker" and cid == container_id]
            for hostname in to_remove:
                del self._services[hostname]
                print(f"Service Registry: Removed {hostname} (container_id: {container_id})")

    async def get_target_url(self, hostname: str) -> Optional[str]:
        async with self._lock:
            service_info = self._services.get(hostname)
            return service_info[0] if service_info else None

    async def get_all_services(self) -> Dict[str, Tuple[str, str, Optional[str]]]:
        async with self._lock:
            return self._services.copy()

# Global instance
registry = ServiceRegistry()