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
    """Processes labels of a Docker container to register or unregister services."""
    cfg = get_settings()
    moat_label_prefix = cfg.moat_label_prefix
    enable_label = f"{moat_label_prefix}.enable"
    hostname_label = f"{moat_label_prefix}.hostname"
    port_label = f"{moat_label_prefix}.port"

    if enable_label not in container.labels or hostname_label not in container.labels or port_label not in container.labels:
        print(f"Docker Monitor: Skipping container {container.name} (ID: {container.short_id}) due to missing required labels.")
        return

    if container.labels[enable_label].lower() != "true":
        print(f"Docker Monitor: Container {container.name} (ID: {container.short_id}) has '{enable_label}' set to false, unregistering if present.")
        await global_registry.unregister_service_by_container_id(container.id)
        return

    hostname = container.labels[hostname_label]
    port = container.labels[port_label]

    try:
        port = int(port)
    except ValueError:
        print(f"Docker Monitor: Invalid port value '{port}' for container {container.name} (ID: {container.short_id}), skipping.")
        return

    target_url = f"http://{container.name}:{port}" # Assumes internal network
    
    if action == "start":
        print(f"Docker Monitor: Registering {hostname} -> {target_url} for container {container.name} (ID: {container.short_id})")
        await global_registry.register_service(hostname, target_url, container.id)
    elif action == "die":
        print(f"Docker Monitor: Unregistering service for container {container.name} (ID: {container.short_id})")
        await global_registry.unregister_service_by_container_id(container.id)

async def watch_docker_events():
    """Watches Docker events for container start/stop events to update service registry."""
    global _monitor_task_should_stop, _monitor_task_active
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")
    
    try:
        client = docker.from_env()
        async for event in client.events(filters={"type": "container", "event": ["start", "die"]}, decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Stop signal detected, exiting event loop.")
                break
            action = event["Action"]
            if action in ["start", "die"]:
                container_id = event["id"]
                try:
                    container = client.containers.get(container_id)
                    await process_container_labels(container, action)
                except NotFound:
                    # Attempt to retrieve by_id to handle "die" events more reliably, but retry by name on start
                    try:
                        container = client.containers.get(event["id"])
                        await process_container_labels(container, action)
                    except NotFound:
                        if action == "start":
                            # Retry by Name as the container might only be resolvable by name after start
                            try:
                                container = client.containers.get(event["id"])
                                await process_container_labels(container, action)
                            except NotFound:
                                print(f"Docker Monitor: Container {event['id'][:12]} not found for event {action}, skipping.")
                        elif action == "die":
                            await global_registry.unregister_service_b