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

    if enable_label not in container.labels or hostname_label not in container.labels or port_label not in container.labels:
        print(f"Docker Monitor: Skipping container {container.name} ({container.short_id}) because it's missing required labels.")
        return
    
    try:
        enable = container.labels[enable_label].lower() == 'true'
        hostname = container.labels[hostname_label]
        port = int(container.labels[port_label])
    except ValueError as e:
        print(f"Docker Monitor: Invalid label value on container {container.name} ({container.short_id}): {e}")
        return

    if enable:
        target_url = f"http://{container.name}:{port}"
        if action == "start":
            print(f"Docker Monitor: Adding service {hostname} -> {target_url} from container {container.name} ({container.short_id})")
            await global_registry.add_service(hostname, target_url)
        elif action == "die":
            print(f"Docker Monitor: Removing service {hostname} from container {container.name} ({container.short_id})")
            await global_registry.remove_service(hostname)
    else:
        print(f"Docker Monitor: Container {container.name} ({container.short_id}) has Moat disabled.")

async def watch_docker_events():
    global _monitor_task_should_stop, _monitor_task_active
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")
    
    try:
        client = docker.from_env()
        async for event in client.events(filters={"type": "container", "event": ["start", "die"]}, decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Stop signal detected, exiting event loop.")
                break
            action = event.get("status")
            if action in ["start", "die"]:
                container_id = event["id"]
                try:
                    container = client.containers.get(container_id)
                    await process_container_labels(container, action)
                except NotFound:
                    # Container disappeared between event and processing
                    if action == "die":
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