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
    """
    Processes a container's labels to register or unregister it as a service.
    """
    cfg = get_settings()
    moat_label_prefix = cfg.moat_label_prefix
    container_name = container.name
    container_id = container.short_id

    labels = container.labels
    enabled = labels.get(f"{moat_label_prefix}.enable") == "true"
    hostname = labels.get(f"{moat_label_prefix}.hostname")
    port = labels.get(f"{moat_label_prefix}.port")

    if action == "start":
        if enabled and hostname and port:
            target_url = f"http://{container.name}:{port}"
            print(f"Docker Monitor: Registering service {hostname} -> {target_url} (Container: {container_name}, ID: {container_id})")
            await global_registry.register_service(hostname, target_url)
        else:
            if enabled:
                print(f"Docker Monitor: Container {container_name} has 'moat.enable=true' but missing 'hostname' or 'port' labels.")
            else:
                print(f"Docker Monitor: Container {container_name} started, but 'moat.enable' label is not 'true'.")
    elif action == "stop":
        if hostname:
            print(f"Docker Monitor: Unregistering service {hostname} (Container: {container_name}, ID: {container_id})")
            await global_registry.unregister_service(hostname)
        else:
            print(f"Docker Monitor: Container {container_name} stopped, but no 'hostname' label found.")

async def watch_docker_events():
    """
    Monitors Docker events for container start and stop events and updates the service registry accordingly.
    """
    global _monitor_task_should_stop, _monitor_task_active
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")

    try:
        client = docker.from_env()
        async for event in client.events(filters={"type": "container", "event": ["start", "die", "stop", "destroy"]}, decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Exiting event stream.")
                break

            action = event.get("status")
            if action in ["start", "stop", "die", "destroy"]:
                container_id = event["id"]
                print(f"Docker Monitor: Received event '{action}' for container {container_id[:12]}")
                try:
                    container = client.containers.get(container_id)
                    await process_container_labels(container, action)
                except