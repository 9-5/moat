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
    """Extract relevant labels and register or unregister services in the global registry."""
    cfg = get_settings()
    moat_label_prefix = cfg.moat_label_prefix
    enable_label = f"{moat_label_prefix}.enable"
    hostname_label = f"{moat_label_prefix}.hostname"
    port_label = f"{moat_label_prefix}.port"

    labels = container.labels
    if enable_label not in labels or hostname_label not in labels or port_label not in labels:
        print(f"Docker Monitor: Required labels missing on container {container.name} ({container.id[:12]}), skipping.")
        return

    if labels.get(enable_label).lower() != "true":
        print(f"Docker Monitor: {enable_label} is not 'true' on container {container.name} ({container.id[:12]}), skipping.")
        return

    hostname = labels[hostname_label]
    try:
        port = int(labels[port_label])
    except ValueError:
        print(f"Docker Monitor: Invalid port value '{labels[port_label]}' on container {container.name} ({container.id[:12]}), skipping.")
        return

    target_url = f"http://{container.name}:{port}"  # or container.attrs['NetworkSettings']['Networks']['bridge']['IPAddress']
    print(f"Docker Monitor: Found service: {hostname} -> {target_url}")
    if action == "start":
        await global_registry.register_service(hostname, target_url, container_id=container.id)
    elif action == "stop":
        await global_registry.unregister_service(hostname)

async def watch_docker_events():
    """Watches Docker events and updates the service registry accordingly."""
    global _monitor_task_should_stop, _monitor_task_active
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")

    try:
        client = docker.from_env()
        # Load existing containers at startup, mimicking "start" events
        print("Docker Monitor: Initial service discovery...")
        for container in client.containers.list(all=True):
            if container.status == 'running': # Only process running containers on startup
                await process_container_labels(container, "start")

        async for event in client.events(decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Event watcher received stop signal.")
                break
            if event["Type"] == "container":
                action = event["Action"]
                try:
                    if action in ("start", "die", "stop", "destroy"): # 'die' seems to come before 'stop' on compose down.
                        container = client.containers.get(event["id"])
                        if container:
                            print(f"Docker Monitor: Event: Container {event['id'][:12]} {action}")
                            await process_container_labels(container, "start" if action == "start" else "stop")
                            if action in ("die", "stop", "destroy"):
                                await global_registry.unre