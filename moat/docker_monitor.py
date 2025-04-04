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
    container_name = container.name
    container_id = container.short_id
    labels = container.labels

    try:
        enable_label = f"{moat_label_prefix}.enable"
        hostname_label = f"{moat_label_prefix}.hostname"
        port_label = f"{moat_label_prefix}.port"

        if enable_label not in labels or hostname_label not in labels or port_label not in labels:
            if action == "start": # Only log on start to reduce spam
                print(f"Docker Monitor: Skipping container '{container_name}' ({container_id}) - missing required labels.")
            return

        if labels[enable_label].lower() != "true":
            print(f"Docker Monitor: Skipping container '{container_name}' ({container_id}) - enable label is not 'true'.")
            return

        hostname = labels[hostname_label]
        port = int(labels[port_label])
        target_url = f"http://{container.name}:{port}"

        if action == "start":
            print(f"Docker Monitor: Adding service: {hostname} -> {target_url} (Container: {container_name}, ID: {container_id})")
            await global_registry.add_service(hostname, target_url)
        elif action == "die" or action == "stop":
            print(f"Docker Monitor: Removing service: {hostname} (Container: {container_name}, ID: {container_id}) due to container {action}.")
            await global_registry.remove_service(hostname)
        else:
            print(f"Docker Monitor: Unknown action '{action}' for container '{container_name}' ({container_id}).")

    except ValueError as e:
        print(f"Docker Monitor: Error processing labels for container '{container_name}' ({container_id}): {e}")
    except Exception as e:
        print(f"Docker Monitor: Unexpected error processing container '{container_name}' ({container_id}): {type(e).__name__} - {e!r}")

async def watch_docker_events():
    global _monitor_task_should_stop, _monitor_task_active
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")
    
    try:
        client = docker.from_env()
        async for event in client.events(decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Stopping event watcher...")
                break

            if event["Type"] == "container":
                action = event["Action"]
                if action in ("start", "die", "stop"):
                    try:
                        container = client.containers.get(event["id"])
                        await process_container_labels(container, action)
                    except NotFound:
                        # Container might be gone already, especially on 'die' events.
                        # Attempt to remove it anyway based on event ID, in case labels existed previously.
                        if action in ("die","stop"):
                            print(f"Docker Monitor: Removing service by container_id after container removal: {event['id'][:12]}")
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