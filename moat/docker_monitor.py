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
        print(f"Docker Monitor: Required labels missing on container {container.name} ({container.short_id}), skipping {action}.")
        return

    if labels[enable_label].lower() != "true":
        print(f"Docker Monitor: {enable_label} is not 'true' on container {container.name} ({container.short_id}), skipping {action}.")
        return

    hostname = labels[hostname_label]
    port = labels[port_label]

    try:
        port = int(port)
    except ValueError:
        print(f"Docker Monitor: Invalid port value '{port}' on container {container.name} ({container.short_id}), skipping {action}.")
        return

    target_url = f"http://{container.name}:{port}" # Use container name for internal Docker network access.

    if action == "start":
        print(f"Docker Monitor: Registering {hostname} -> {target_url} from container {container.name} ({container.short_id})")
        await global_registry.register_service(hostname, target_url, container.id)
    elif action == "stop":
        print(f"Docker Monitor: Deregistering {hostname} from container {container.name} ({container.short_id})")
        await global_registry.remove_service_by_container_id(container.id)

async def watch_docker_events():
    global _monitor_task_should_stop, _monitor_task_active
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")
    
    try:
        client = docker.from_env()
        async for event in client.events(decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Received stop signal, exiting event watcher.")
                break
            
            if event["Type"] == "container":
                action = event["Action"]
                if action in ("start", "die"):
                    try:
                        container = client.containers.get(event["id"])
                        await process_container_labels(container, action)
                    except NotFound:
                        if action == "die": #It's possible that the container is already removed.
                            await global_registry.remove_service_by_container_id(event["id"])
                        else:
                            print(f"Docker Monitor: Container {event['id'][:12]} not found for event {action}, skipping.")
                    except Exception as e:
                        print(f"Docker Monitor: Error processing event for {event['id'][:12]}: {e}")
    except docker.errors.DockerException as e:
        print(f"Docker Monitor: DockerException in event stream: {e}. Is Docker running and accessible? Stopping monitor.")
    except Exception as e:
        print(f"Docker Monitor: Error in event stream: {e}. Stopping monitor.")
    finally:
        print("Docker Monitor: Event watcher stopped.")
        _monitor_task_active = False
        _monitor_task_should_stop.clear()