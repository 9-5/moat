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
    
    if f"{prefix}.enable" not in labels:
        print(f"Docker Monitor: Container {container.name} ({container.short_id}) does not have '{prefix}.enable' label, skipping.")
        await global_registry.unregister_service_by_container_id(container.id)
        return

    if labels.get(f"{prefix}.enable", "false").lower() != "true":
        print(f"Docker Monitor: Container {container.name} ({container.short_id}) has '{prefix}.enable' set to false, unregistering.")
        await global_registry.unregister_service_by_container_id(container.id)
        return
    
    hostname = labels.get(f"{prefix}.hostname")
    port = labels.get(f"{prefix}.port")

    if not hostname or not port:
        print(f"Docker Monitor: Container {container.name} ({container.short_id}) missing required 'hostname' or 'port' labels, skipping registration.")
        await global_registry.unregister_service_by_container_id(container.id)
        return

    try:
        port = int(port)
    except ValueError:
        print(f"Docker Monitor: Container {container.name} ({container.short_id}) has invalid port '{port}', skipping registration.")
        await global_registry.unregister_service_by_container_id(container.id)
        return

    target_url = f"http://{container.name}:{port}" # Inside docker network, use container name

    if action == "start":
        print(f"Docker Monitor: Registering service {hostname} -> {target_url} for container {container.name} ({container.short_id})")
        await global_registry.register_service(hostname, target_url, container.id)
    elif action == "stop":
        print(f"Docker Monitor: Unregistering service for container {container.name} ({container.short_id}) due to stop event.")
        await global_registry.unregister_service_by_container_id(container.id)
    else:
        print(f"Docker Monitor: Unknown action '{action}' for container {container.name} ({container.short_id}), skipping.")

async def watch_docker_events():
    global _monitor_task_should_stop, _monitor_task_active
    if _monitor_task_active:
        print("Docker Monitor: Already running, not starting a new instance.")
        return

    _monitor_task_active = True
    _monitor_task_should_stop.clear()
    
    print("Docker Monitor: Starting event watcher...")
    try:
        client = docker.from_env()
        async for event in client.events(filters={"type": "container", "event": ["start", "stop"]}, decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Exiting event watcher.")
                break

            if event["Type"] == "container":
                action = event["Action"]
                if action in ("start", "stop"):
                    try:
                        container = client.containers.get(event["id"])
                        await process_container_labels(container, action)
                    except NotFound:
                        if action == "stop":
                            # Container stop event might arrive after container is already gone
                            # This is normal, we can just unregister by container id
                            await global_registry.unregister_service_by_container_id(event["id"])
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