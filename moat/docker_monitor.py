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
    cfg = get_settings()
    labels = container.labels
    prefix = cfg.moat_label_prefix
    enable_label = f"{prefix}.enable"
    hostname_label = f"{prefix}.hostname"
    port_label = f"{prefix}.port"

    if enable_label not in labels or hostname_label not in labels or port_label not in labels:
        print(f"Docker Monitor: Skipping container {container.name} ({container.short_id}) - missing required labels.")
        return

    if labels[enable_label].lower() != "true":
        print(f"Docker Monitor: Skipping container {container.name} ({container.short_id}) - enable label is not 'true'.")
        return

    hostname = labels[hostname_label]
    try:
        port = int(labels[port_label])
    except ValueError:
        print(f"Docker Monitor: Invalid port value '{labels[port_label]}' for container {container.name} ({container.short_id}).")
        return
    
    target_url = f"http://{container.name}:{port}"  # Internal Docker network URL

    if action == "start":
        print(f"Docker Monitor: Adding service {hostname} -> {target_url} (Container: {container.name})")
        await global_registry.register_service(hostname, target_url)
    elif action == "stop":
        print(f"Docker Monitor: Removing service {hostname} (Container: {container.name})")
        await global_registry.unregister_service(hostname)

async def watch_docker_events():
    global _monitor_task_should_stop, _monitor_task_active
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")

    try:
        client = docker.from_env()
        async for event in client.events(decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Exiting event watcher.")
                break

            if event["Type"] == "container":
                action = event["Action"]
                if action in ("start", "stop"):
                    try:
                        container = client.containers.get(event["id"])
                        await process_container_labels(container, action)
                    except NotFound:
                        if action == "stop":
                            # Container stop event might arrive after container is already gone
                            # This is normal, we can just unregister by container id
                            await global_registry.unregisterservice_b