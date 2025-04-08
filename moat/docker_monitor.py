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
    moat_label_prefix = cfg.moat_label_prefix

    enable_label = f"{moat_label_prefix}.enable"
    hostname_label = f"{moat_label_prefix}.hostname"
    port_label = f"{moat_label_prefix}.port"

    if enable_label in container.labels and container.labels[enable_label].lower() == "true":
        hostname = container.labels.get(hostname_label)
        port = container.labels.get(port_label)

        if not hostname or not port:
            print(f"Docker Monitor: Container '{container.name}' has '{enable_label}=true' but is missing '{hostname_label}' or '{port_label}' labels. Skipping.")
            return

        try:
            port = int(port)
        except ValueError:
            print(f"Docker Monitor: Invalid port value '{port}' in label '{port_label}' for container '{container.name}'. Skipping.")
            return
        
        target_url = f"http://{container.name}:{port}" # Internal Docker network hostname

        if action == "start":
            print(f"Docker Monitor: Registering service '{hostname}' -> '{target_url}' (from container '{container.name}')")
            await global_registry.register_service(hostname, target_url)
        elif action == "die":
            print(f"Docker Monitor: Unregistering service '{hostname}' (container '{container.name}' stopped)")
            await global_registry.unregister_service(hostname)

async def watch_docker_events():
    global _monitor_task_should_stop, _monitor_task_active

    docker_client = docker.from_env()
    print("Docker Monitor: Starting event watcher...")
    _monitor_task_active = True

    try:
        async for event in docker_client.events(decode=True, filters={"type": "container", "event": ["start", "die", "stop", "health_status"]}):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Event watcher received stop signal.")
                break

            action = event.get("status")
            if action in ["start", "die", "stop", "health_status"]:
                container_id = event["id"]
                try:
                    container = docker_client.containers.get(container_id)
                    await process_container_labels(container, action)
                except NotFound:
                    #If container is not found, try to process container labels by container id
                    try:
                        if action in ["start", "die", "stop"]:
                            await global_registry.unregisters_service_b... (FILE CONTENT TRUNCATED) ...
    finally:
        print("Docker Monitor: Event watcher stopped.")
        _monitor_task_active = False
        _monitor_task_should_stop.clear()