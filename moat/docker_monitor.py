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
        print(f"Docker Monitor: Skipping container {container.name} ({container.short_id}) due to missing required labels.")
        return

    if labels[enable_label].lower() != "true":
        print(f"Docker Monitor: Skipping container {container.name} ({container.short_id}) as it is disabled.")
        return

    hostname = labels[hostname_label]
    try:
        port = int(labels[port_label])
    except ValueError:
        print(f"Docker Monitor: Invalid port value for container {container.name} ({container.short_id}). Skipping.")
        return
    
    target_url = f"http://{container.name}:{port}"  # Construct target URL from container name
    
    if action == "start":
        print(f"Docker Monitor: Registering service {hostname} -> {target_url} from container {container.name} ({container.short_id})")
        await global_registry.register_service(hostname, target_url)
    elif action == "die":
        print(f"Docker Monitor: Deregistering service {hostname} from container {container.name} ({container.short_id})")
        await global_registry.deregister_service(hostname)

async def watch_docker_events():
    """Monitors Docker events for container start/stop events to update the service registry."""
    global _monitor_task_should_stop, _monitor_task_active
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")
    
    try:
        client = docker.from_env() # this can raise docker.errors.DockerException
        async for event in client.events(filters={"type": "container", "event": ["start", "die"]}, decode=True): # type: ignore
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Stop signal detected, exiting event loop.")
                break
            
            action = event.get("Action")
            if action in ("start", "die"):
                container_id = event["id"]
                try:
                    container = client.containers.get(container_id)
                    await process_container_labels(container, action)
                except NotFound:
                    # Container might be gone before we process the event
                    print(f"Docker Monitor: Container {event['id'][:12]} not found, skipping.")
                except Exception as e:
                    print(f"Docker Monitor: Error processing event for {event['id'][:12]}: {e}")
            else:
                print(f"Docker Monitor: Unknown event action: {action}")

    except docker.errors.DockerException as e:
        print(f"Docker Monitor: DockerException in event stream: {e}. Is Docker running and accessible? Stopping monitor.")
    except Exception as e:
        print(f"Docker Monitor: Error in event stream: {e}. Stopping monitor.")
    finally:
        print("Docker Monitor: Event watcher stopped.")
        _monitor_task_active = False
        _monitor_task_should_stop.clear()