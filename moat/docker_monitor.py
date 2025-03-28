import asyncio
import docker # type: ignore
from docker.errors import NotFound # type: ignore

from .service_registry import registry as global_registry
from .config import get_settings

_monitor_task_should_stop = asyncio.Event()
_monitor_task_active = False

async def stop_docker_monitor_task():
    global _monitor_task_should_stop, _monitor_task_active
    if _monitor_task_active:
        print("Docker Monitor: Stop signal received.")
        _monitor_task_should_stop.set()
    else:
        print("Docker Monitor: Stop signal received, but monitor was not marked active.")

async def is_docker_monitor_running() -> bool:
    global _monitor_task_active
    return _monitor_task_active


async def process_container_labels(container, action: str):
    """Extracts relevant labels from a container and registers/unregisters it as a service."""
    cfg = get_settings()
    label_prefix = cfg.moat_label_prefix
    
    enable_label = f"{label_prefix}.enable"
    hostname_label = f"{label_prefix}.hostname"
    port_label = f"{label_prefix}.port"

    if enable_label in container.labels:
        try:
            enabled = str(container.labels.get(enable_label)).lower() == "true"
            hostname = container.labels.get(hostname_label)
            port = container.labels.get(port_label)
            
            if not (enabled and hostname and port):
                print(f"Docker Monitor: Skipping container {container.name} ({container.short_id}) due to missing labels. Enable: {enabled}, Hostname: {hostname}, Port: {port}")
                return # Skip if missing required labels or not enabled.
            
            target_url = f"http://{container.name}:{port}"  # Use container name for internal Docker network
            
            if enabled:
                print(f"Docker Monitor: Registering service {hostname} -> {target_url} (Container: {container.name} - {container.short_id})")
                await global_registry.register_service(hostname, target_url)
            else:
                print(f"Docker Monitor: Unregistering service {hostname} (Container: {container.name} - {container.short_id})")
                await global_registry.unregister_service(hostname)

        except Exception as e:
            print(f"Docker Monitor: Error processing labels for container {container.name} ({container.short_id}): {e}")

async def watch_docker_events():
    """Monitors Docker events for container starts, stops, and dies to update the service registry."""
    global _monitor_task_should_stop, _monitor_task_active
    
    if _monitor_task_active:
        print("Docker Monitor: Already running, this call is a no-op.")
        return
    
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")

    try:
        client = docker.from_env()
        
        # Get existing containers to sync on startup
        print("Docker Monitor: Initial sync of existing containers...")
        for container in client.containers.list():