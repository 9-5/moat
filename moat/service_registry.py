import asyncio
from typing import Dict, Tuple, List, Optional
from urllib.parse import urlparse

class ServiceRegistry:
    def __init__(self):
        self._services: Dict[str, str] = {}  # hostname -> target_url
        self._lock = asyncio.Lock()

    async def register_service(self, hostname: str, target_url: str):
        async with self._lock:
            self._services[hostname] = target_url
            print(f"ServiceRegistry: Registered {hostname} -> {target_url}")

    async def unregister_service(self, hostname: str):
        async with self._lock:
            if hostname in self._services:
                del self._services[hostname]
                print(f"ServiceRegistry: Unregistered {hostname}")
            else:
                print(f"ServiceRegistry: Cannot unregister {hostname}, not found.")

    async def get_target_url(self, hostname: str, request_headers: dict) -> Optional[str]:
        async with self._lock:
            target_url = self._services.get(hostname)
            if target_url:
                # Apply X-Forwarded-* headers
                x_forwarded_proto = request_headers.get("x-forwarded-proto")
                x_forwarded_host = request_headers.get("x-forwarded-host")
                
                if x_forwarded_proto or x_forwarded_host:
                    parsed_target = urlparse(target_url)
                    
                    scheme = x_forwarded_proto if x_forwarded_proto else parsed_target.scheme
                    netloc = x_forwarded_host if x_forwarded_host else parsed_target.netloc
                    path = parsed_target.path
                    query = parsed_target.query
                    fragment = parsed_target.fragment

                    # Reconstruct the URL
                    target_url = f"{scheme}://{netloc}{path}"
                    if query:
                        target_url += f"?{query}"
                    if fragment:
                        target_url += f"#{fragment}"
                
                print(f"ServiceRegistry: Resolved {hostname} to {target_url}")
                return target_url
            else:
                print(f"ServiceRegistry: No target URL found for {hostname}")
                return None

    async def get_all_services(self) -> List[Tuple[str, str]]:
        async with self._lock:
            return list(self._services.items())  # Returns a list of (hostname, target_url) tuples

    async def clear(self):
        async with self._lock:
            self._services.clear()
            print("ServiceRegistry: Cleared all services.")

registry = ServiceRegistry()