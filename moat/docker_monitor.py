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

    if enable_label in container.labels:
        if container.labels[enable_label].lower() == "true":
            print(f"Docker Monitor: Container {container.name} ({container.short_id}) - Processing labels.")
            hostname = container.labels.get(hostname_label)
            port = container.labels.get(port_label)

            if not hostname:
                print(f"Docker Monitor: Container {container.name} missing {hostname_label} label, skipping.")
                await global_registry.unregister_service(container.id)
                return
            if not port:
                print(f"Docker Monitor: Container {container.name} missing {port_label} label, skipping.")
                await global_registry.unregister_service(container.id)
                return

            target_url = f"http://{container.name}:{port}"
            try:
                await global_registry.register_service(hostname, target_url, container.id)
                print(f"Docker Monitor: Registered {hostname} -> {target_url} for container {container.name}")
            except Exception as e:
                print(f"Docker Monitor: Failed to register service: {e}")
        else:
            print(f"Docker Monitor: Container {container.name} has {enable_label}=false, unregistering.")
            await global_registry.unregister_service(container.id)
    elif action in ["die", "stop"]:
        print(f"Docker Monitor: Container {container.name} stopped. Removing service.")
        await global_registry.unregister_service(container.id)

async def watch_docker_events():
    global _monitor_task_should_stop, _monitor_task_active
    
    if _monitor_task_active:
        print("Docker Monitor: Already running, this call is a no-op.")
        return

    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")
    
    docker_client = docker.from_env()

    try:
        async for event in docker_client.events(decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Stop signal detected, exiting event loop.")
                break
            
            action = event.get("status") or event.get("Action") # Events are inconsistent
            
            # Container health status events can have "health_status" action
            if action in ["start", "die", "stop", "health_status"]:
                container_id = event["id"]
                try:
                    container = docker_client.containers.get(container_id)
                    await process_container_labels(container, action)
                except NotFound:
                    #If container is not found, try to process container labels by container id
                    try:
                        if action in ["start", "die", "stop"]:
                            await global_registry.unregisters_service_by_container_id(event["id"])
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