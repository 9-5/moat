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
    """Extracts labels from a container and updates the service registry."""
    cfg = get_settings()
    labels = container.labels
    prefix = cfg.moat_label_prefix

    if f"{prefix}.enable" not in labels or labels[f"{prefix}.enable"].lower() != "true":
        print(f"Docker Monitor: Container {container.name} ({container.short_id}) does not have {prefix}.enable=true, skipping.")
        await global_registry.remove_service_by_container_id(container.id)
        return

    hostname = labels.get(f"{prefix}.hostname")
    port = labels.get(f"{prefix}.port")

    if not hostname or not port:
        print(f"Docker Monitor: Container {container.name} missing {prefix}.hostname or {prefix}.port labels.")
        await global_registry.remove_service_by_container_id(container.id)
        return

    try:
        port = int(port)
    except ValueError:
        print(f"Docker Monitor: Invalid port number for {container.name}: {port}")
        await global_registry.remove_service_by_container_id(container.id)
        return

    target_url = f"http://{container.name}:{port}"  # Docker's internal network
    
    if action == "start":
        print(f"Docker Monitor: Adding/Updating service: {hostname} -> {target_url} (Container: {container.name})")
        await global_registry.add_service(hostname=hostname, target_url=target_url, container_id=container.id)
    elif action == "die":
        print(f"Docker Monitor: Removing service for container {container.name} due to 'die' event.")
        await global_registry.remove_service_by_container_id(container.id)
    else:
        print(f"Docker Monitor: Unknown action: {action} for container {container.name}")

async def watch_docker_events():
    """Watches Docker events for container starts and stops, and updates the service registry."""
    global _monitor_task_should_stop, _monitor_task_active
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")

    try:
        client = docker.from_env()
        async for event in client.events(filters={"type": "container", "event": ["start", "die"]}, decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Stop signal detected, exiting event loop.")
                break
            action = event.get("status")
            if action in ("start", "die"):
                try:
                    container = client.containers.get(event["id"])
                    await process_container_labels(container, action)
                except NotFound:
                    # Container might be gone already; happens with very short-lived containers.
                    print(f"Docker Monitor: Container {event['id'][:12]} not found for event {action}, skipping.")
                except Exception as e:
                    print(f"Docker Monitor: Error processing event for {event['id'][:1