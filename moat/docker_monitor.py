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
    Processes a container's labels to register or unregister a service.
    """
    cfg = get_settings()
    moat_label_prefix = cfg.moat_label_prefix
    enable_label = f"{moat_label_prefix}.enable"
    hostname_label = f"{moat_label_prefix}.hostname"
    port_label = f"{moat_label_prefix}.port"
    target_label = f"{moat_label_prefix}.target"

    enable = container.labels.get(enable_label, "").lower() == "true"
    hostname = container.labels.get(hostname_label)
    port = container.labels.get(port_label)
    target = container.labels.get(target_label)

    if enable and hostname and port:
        target_url = f"http://{container.name}:{port}"
        if target:
             target_url = target

        if action == "start":
            print(f"Docker Monitor: Registering {hostname} -> {target_url} from container {container.name} ({container.short_id})")
            await global_registry.register_service(hostname, target_url)
        elif action == "die":
            print(f"Docker Monitor: Unregistering {hostname} from container {container.name} ({container.short_id})")
            await global_registry.unregister_service(hostname)

async def watch_docker_events():
    """
    Watches for Docker container events (start, die) and updates the service registry accordingly.
    """
    global _monitor_task_active
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")
    
    cfg = get_settings()
    client = docker.from_env()

    try:
        async for event in client.events(filters={"type": "container", "event": ["start", "die"]}, decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Received stop signal, exiting event loop.")
                break

            action = event.get("status")
            if action in ["start", "die"]:
                container_id = event["id"]
                try:
                    container = client.containers.get(container_id)
                    await process_container_labels(container, action)
                except NotFound:
                    # Container might be gone already, especially on 'die' events
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