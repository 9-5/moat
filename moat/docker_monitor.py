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
    prefix = cfg.moat_label_prefix + "."
    enable_label = prefix + "enable"
    hostname_label = prefix + "hostname"
    port_label = prefix + "port"

    if enable_label not in labels or hostname_label not in labels or port_label not in labels:
        print(f"Docker Monitor: Skipping container {container.name} ({container.short_id}), missing required labels.")
        return

    if labels[enable_label].lower() != "true":
        print(f"Docker Monitor: Skipping container {container.name} ({container.short_id}), enable label is not 'true'.")
        return

    hostname = labels[hostname_label]
    port = labels[port_label]

    try:
        port = int(port)
    except ValueError:
        print(f"Docker Monitor: Invalid port value '{port}' for container {container.name} ({container.short_id}), skipping.")
        return
    
    target_url = f"http://{container.name}:{port}" #Assumes container name is resolvable.  Containers MUST be on the same network.

    print(f"Docker Monitor: {action.title()} service {hostname} -> {target_url} (Container: {container.name}, ID: {container.short_id})")
    
    if action == "start":
        await global_registry.register_service(hostname, target_url, container.id)
    elif action == "stop" or action == "die":
        await global_registry.deregister_service_by_container_id(container.id)
    else:
        print(f"Docker Monitor: Unknown action '{action}' for container {container.name} ({container.short_id}).")

async def watch_docker_events():
    global _monitor_task_should_stop, _monitor_task_active
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")
    
    cfg = get_settings()
    try:
        client = docker.from_env()
        # First, process all existing containers
        print("Docker Monitor: Processing existing containers...")
        for container in client.containers.list():
            await process_container_labels(container, "start")

        # Then, watch for events
        print("Docker Monitor: Watching for container events...")