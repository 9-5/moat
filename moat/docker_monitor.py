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
    Processes labels from a Docker container and registers/unregisters services accordingly.
    """
    cfg = get_settings()
    labels = container.labels
    prefix = cfg.moat_label_prefix
    enable_label = f"{prefix}.enable"
    hostname_label = f"{prefix}.hostname"
    port_label = f"{prefix}.port"

    if enable_label not in labels or hostname_label not in labels or port_label not in labels:
        print(f"Docker Monitor: Skipping container {container.name} ({container.short_id}) - missing required labels.")
        return

    if labels[enable_label].lower() == "true":
        hostname = labels[hostname_label]
        try:
            port = int(labels[port_label])
        except ValueError:
            print(f"Docker Monitor: Invalid port value '{labels[port_label]}' for container {container.name} ({container.short_id}), skipping.")
            return
        
        target_url = f"http://{container.name}:{port}"  # Use container name for internal Docker network access
        print(f"Docker Monitor: Registering service '{hostname}' -> '{target_url}' from container {container.name} ({container.short_id}).")
        await global_registry.register_service(hostname, target_url, container.short_id)
    else:
        print(f"Docker Monitor: Unregistering service(s) for container {container.name} ({container.short_id}) due to '{enable_label}=false'.")
        await global_registry.unregister_service_by_container_id(container.short_id)

async def watch_docker_events():
    """
    Watches Docker events for container start/stop events and updates the service registry.
    """
    global _monitor_task_should_stop, _monitor_task_active
    _monitor_task_active = True
    
    try:
        client = docker.from_env()
        print("Docker Monitor: Starting event watcher.")
        async for event in client.events(filters={"type": "container", "event": ["start", "stop", "die", "destroy", "update"]}, decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Stop signal received, exiting event loop.")
                break
            action = event.get("status")
            if action in ("start", "die", "destroy", "update"): # "die" is sent when a container stops
                container_id = event["id"]
                print(f"Docker Monitor: Received container event: {action} for {container_id[:12]}")
                try:
                    container = client.containers.get(container_id)
                    await process_container_labels(container, action)
                except NotFound:
                    # Container might be gone already; happens with very short-lived containers.
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