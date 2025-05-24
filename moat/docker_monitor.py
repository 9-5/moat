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
    """Extracts labels from a container and registers/unregisters services."""
    cfg = get_settings()
    labels = container.labels
    prefix = cfg.moat_label_prefix
    enable_label = f"{prefix}.enable"
    hostname_label = f"{prefix}.hostname"
    port_label = f"{prefix}.port"

    if enable_label in labels and labels[enable_label].lower() == "true":
        hostname = labels.get(hostname_label)
        port = labels.get(port_label)

        if not hostname or not port:
            print(f"Docker Monitor: Container {container.name} has enable label but missing hostname or port. Skipping.")
            return

        try:
            port = int(port)
        except ValueError:
            print(f"Docker Monitor: Invalid port value '{port}' for container {container.name}. Skipping.")
            return
        
        target_url = f"http://{container.name}:{port}" # Use container name for internal Docker network

        if action == "start":
            print(f"Docker Monitor: Registering service '{hostname}' -> '{target_url}' (Container: {container.name})")
            await global_registry.register_service(hostname, target_url)
        elif action == "stop":
            print(f"Docker Monitor: Unregistering service '{hostname}' (Container: {container.name})")
            await global_registry.unregister_service(hostname)
    elif action == "stop" and enable_label not in labels:
        # Handle case where container *used* to have the label, but was removed.
        print(f"Docker Monitor: Unregistering service based on 'stop' event for container {container.name}")
        await global_registry.unregister_service_by_container_name(container.name)
    else:
        print(f"Docker Monitor: Container {container.name} does not have '{enable_label}=