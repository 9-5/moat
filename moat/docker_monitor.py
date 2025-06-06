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
        try:
            if container.labels[enable_label].lower() == "true":
                hostname = container.labels.get(hostname_label)
                port = container.labels.get(port_label)

                if not hostname or not port:
                    print(f"Docker Monitor: Container {container.name} missing hostname or port label, skipping.")
                    return
                
                try:
                    port = int(port)
                except ValueError:
                    print(f"Docker Monitor: Container {container.name} has invalid port label, skipping.")
                    return

                target_url = f"http://{container.name}:{port}" #Internal Docker network URL

                if action == "start":
                    print(f"Docker Monitor: Registering service {hostname} -> {target_url} from container {container.name}")
                    await global_registry.register_service(hostname, target_url)
                elif action == "stop":
                    print(f"Docker Monitor: Unregistering service {hostname} from container {container.name}")
                    await global_registry.unregister_service(hostname)
        except Exception as e:
            print(f"Docker Monitor: Error processing labels for container {container.name}: {e}")

async def watch_docker_events():
    global _monitor_task_should_stop, _monitor_task_active
    print("Docker Monitor: Starting event watcher...")
    _monitor_task_active = True
    cfg = get_settings()
    client = docker.from_env()

    try:
        async for event in client.events(decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Event watcher received stop signal.")
                break
            if event["Type"] == "container":
                action = event["Action"]
                try:
                    if action in ("start", "die", "stop", "destroy"): # 'die' seems to come before 'stop' on compose down.
                        container = client.containers.get(event["id"])
                        if container:
                            print(f"Docker Monitor: Event: Container {event['id'][:12]} {action}")
                            await process_container_labels(container, "start" if action == "start" else "stop")
                            if action in ("die", "stop", "destroy"):
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