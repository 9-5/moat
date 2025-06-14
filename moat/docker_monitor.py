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

    if not labels.get(f"{cfg.moat_label_prefix}.enable"):
        print(f"Docker Monitor: Container {container.name} does not have '{cfg.moat_label_prefix}.enable' label, skipping.")
        return

    hostname = labels.get(f"{cfg.moat_label_prefix}.hostname")
    port = labels.get(f"{cfg.moat_label_prefix}.port")
    
    if not hostname or not port:
        print(f"Docker Monitor: Container {container.name} missing required labels ('hostname' and/or 'port'), skipping.")
        return

    target_url = f"http://{container.name}:{port}" # Use container name for internal Docker network access
    
    if action == "start":
        print(f"Docker Monitor: Registering service '{hostname}' -> '{target_url}' for container {container.name}.")
        await global_registry.register_service(hostname, target_url)
    elif action == "stop":
        print(f"Docker Monitor: Unregistering service '{hostname}' for container {container.name}.")
        await global_registry.unregister_service(hostname)

async def watch_docker_events():
    global _monitor_task_active
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")
    
    cfg = get_settings()
    client = docker.from_env()

    try:
        async for event in client.events(decode=True, filters={"event": ["start", "die", "stop", "destroy"]}):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Stop signal detected, exiting event loop.")
                break
            
            action = event.get("status") or event.get("Action") # 'status' for 'die'/'start', 'Action' for 'destroy'
            if action in ("start", "die", "stop", "destroy"):
                container = None
                try:
                    container = client.containers.get(event["id"])
                except NotFound:
                    pass # Container might be gone already
                except Exception as e:
                    print(f"Docker Monitor: Error getting container {event['id'][:12]}: {e}")

                if container:
                    try:
                        if action == "start":
                            await process_container_labels(container, "start")
                        elif action in ("die", "stop", "destroy"):
                            await process_container_labels(container, "stop") # Always unregister on stop/die/destroy
                            await global_registry.remove_proxy_container_id(event["id"])
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