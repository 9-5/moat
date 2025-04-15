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
    """Processes the labels of a Docker container to register or unregister it as a service."""
    cfg = get_settings()
    
    if not cfg.docker_monitor_enabled:
        print(f"Docker Monitor: Processing labels for {container.name} ({container.short_id}) skipped because monitoring is disabled.")
        return

    if not container.labels:
        print(f"Docker Monitor: Container {container.name} ({container.short_id}) has no labels, skipping.")
        return

    enable_label = f"{cfg.moat_label_prefix}.enable"
    hostname_label = f"{cfg.moat_label_prefix}.hostname"
    port_label = f"{cfg.moat_label_prefix}.port"

    if enable_label not in container.labels:
        print(f"Docker Monitor: Container {container.name} ({container.short_id}) missing '{enable_label}' label, skipping.")
        return

    if container.labels[enable_label].lower() != "true":
        print(f"Docker Monitor: Container {container.name} ({container.short_id}) '{enable_label}' is not 'true', skipping.")
        return

    if hostname_label not in container.labels:
        print(f"Docker Monitor: Container {container.name} ({container.short_id}) missing '{hostname_label}' label, skipping.")
        return

    if port_label not in container.labels:
        print(f"Docker Monitor: Container {container.name} ({container.short_id}) missing '{port_label}' label, skipping.")
        return

    hostname = container.labels[hostname_label]
    try:
        port = int(container.labels[port_label])
    except ValueError:
        print(f"Docker Monitor: Container {container.name} ({container.short_id}) has invalid port '{container.labels[port_label]}', skipping.")
        return
    
    container_ip = None
    try:
        container_ip = container.attrs['NetworkSettings']['Networks']['bridge']['IPAddress']
    except KeyError:
        print(f"Docker Monitor: Could not determine container IP for {container.name} ({container.short_id}), skipping.")
        return

    target_url = f"http://{container_ip}:{port}"

    if action == "start":
        print(f"Docker Monitor: Registering service '{hostname}' -> '{target_url}' for container {container.name} ({container.short_id}).")
        await global_registry.register_service(hostname, target_url, container.id)
    elif action == "stop":
        print(f"Docker Monitor: Unregistering service '{hostname}' for container {container.name} ({container.short_id}).")
        await global_registry.unregister_service_by_container_id(container.id)
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

        async for event in client.events(decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Event watcher stopping...")
                break
            
            if event['Type'] == 'container':
                action = event['Action']
                if action in ("start", "stop", "die"):
                    try:
                        container = client.containers.get(event["id"])
                        if container:
                            await process_container_labels(container, action)
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