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


async def process_container_labels(container, action: str = "add"):
    """Processes labels of a Docker container to register/unregister it as a service."""
    cfg = get_settings()
    labels = container.labels
    prefix = cfg.moat_label_prefix
    
    enabled = labels.get(f"{prefix}.enable")
    hostname = labels.get(f"{prefix}.hostname")
    port = labels.get(f"{prefix}.port")

    if enabled and hostname and port:
        try:
            port = int(port)
        except ValueError:
            print(f"Docker Monitor: Invalid port value for container {container.name}, skipping.")
            return
        
        target_url = f"http://{container.name}:{port}"
        
        if action == "add":
            print(f"Docker Monitor: Registering service {hostname} -> {target_url} (Docker)")
            await global_registry.register_service(hostname, target_url)
        elif action == "remove":
            print(f"Docker Monitor: Unregistering service {hostname} (Docker)")
            await global_registry.unregister_service(hostname)
    elif action == "add" and (enabled or hostname or port):
        print(f"Docker Monitor: Incomplete labels for container {container.name}, skipping.")

async def watch_docker_events():
    """Watches Docker events for container start/stop to update service registry."""
    global _monitor_task_should_stop, _monitor_task_active
    
    if _monitor_task_active:
        print("Docker Monitor: Already running, new task will be skipped.")
        return
    
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")
    
    try:
        client = docker.from_env()
        async for event in client.events(filters={"type": "container"}, decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Stop signal detected, exiting event loop.")
                break
            
            status = event.get("status")
            if status in ("start", "die"):
                container_id = event["id"]
                try:
                    container = client.containers.get(container_id)
                    if status == "start":
                        await process_container_labels(container, "add")
                    elif status == "die":
                        await process_container_labels(container, "remove")
                except NotFound:
                    action = "removed" if status == "die" else "created"
                    #TODO - Investigate race conditions.  Sometimes container is created/removed before the event propagates?
                    #       Try fetching the container by ID a few times, with a delay, before giving up.
                    try:
                        global_registry.remove_service_by_container_id(event["id"])
                    except Exception as e:
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