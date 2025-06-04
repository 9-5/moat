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
    """Processes labels of a Docker container to register/unregister services."""
    cfg = get_settings()
    label_prefix = cfg.moat_label_prefix
    enable_label = f"{label_prefix}.enable"
    hostname_label = f"{label_prefix}.hostname"
    port_label = f"{label_prefix}.port"

    labels = container.labels

    if enable_label not in labels or hostname_label not in labels or port_label not in labels:
        return  # Missing required labels, skip

    if labels[enable_label].lower() != "true":
        return  # Service not enabled, skip

    hostname = labels[hostname_label]
    try:
        port = int(labels[port_label])
    except ValueError:
        print(f"Docker Monitor: Invalid port value for container {container.name}, skipping.")
        return

    target_url = f"http://{container.name}:{port}"

    if action == "start":
        print(f"Docker Monitor: Registering {hostname} -> {target_url} (Container: {container.name})")
        await global_registry.register_service(hostname, target_url)
    elif action == "stop":
        print(f"Docker Monitor: Unregistering {hostname} (Container: {container.name})")
        await global_registry.unregister_service(hostname)

async def watch_docker_events():
    """Watches Docker events for container start/stop to update service registry."""
    global _monitor_task_should_stop, _monitor_task_active
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")
    
    try:
        client = docker.from_env()
        async for event in client.events(filters={"type": "container", "event": ["start", "stop", "die"]}, decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Stop signal detected, exiting event loop.")
                break
            
            action = event["status"]
            if action in ["start", "stop", "die"]:
                container_id = event["id"]
                try:
                    container = client.containers.get(container_id)
                    await process_container_labels(container, action)
                except NotFound:
                    # Container disappeared before we could inspect it?
                    # Also handle 'die' event when container is already stopped.
                    if action == "start":
                        print(f"Docker Monitor: Container {event['id'][:12]} started, but not found immediately after. Assuming it's gone, skipping.")
                        await global_registry.unregister_by_container_id(event["id"])
                    elif action in ["stop", "die"]:
                        print(f"Docker Monitor: Container {event['id'][:12]} stopped/died. Cleaning up container from registry if needed.")
                        await global_registry.unregister_by_container_id(event["id"])
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